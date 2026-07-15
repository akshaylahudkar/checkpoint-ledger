# Connect 4 + Postgres — Design Session Notes

Status snapshot: DB set up, schema built and (mostly) validated, `db.py` pool working,
one working transaction (create game + first player), repository-pattern design reasoned
through but **not yet implemented in code**.

---

## 1. Postgres driver fundamentals

- **`psycopg` vs `psycopg2`**: `psycopg` (no "2"/"3" in the package name) *is* psycopg3 —
  actively developed, native async, better type adaptation. `psycopg2` is the older,
  maintenance-mode driver. Don't confuse the package name with the "psycopg3" nickname.
- **`psycopg_pool` is a separate package** (`pip install "psycopg[binary,pool]"`) by
  deliberate design — core driver handles single-connection correctness; pooling is a
  separate, independently-evolving concern (background threads, health checks, sizing).
  Not every psycopg user needs pooling (e.g. one-off scripts).
- **`binary` extra**: installs a precompiled C extension (`psycopg_binary`) bundling its
  own `libpq`, avoiding the need for a local compiler/`libpq` dev headers.
- **Row factories** (`tuple_row` default, `dict_row`, `namedtuple_row`, `class_row`):
  decide what Python object each fetched row becomes. Chose `dict_row` for legibility;
  `class_row(SomeClass)` is the natural next step once real domain classes exist.

## 2. Singleton pattern in Python

- In Python, **a module is already a singleton** (cached in `sys.modules`) — often the
  simplest correct answer, no `__new__` tricks needed.
- Class-based singleton (`__new__` + double-checked locking) is worth it when you need
  lazy init, multiple configs, or a `reset()` escape hatch for tests.
- Key gotchas: `__init__` runs every time `Database()` is called even if `__new__`
  returns an existing instance — needs an `_initialized` guard. The thing that should be
  singular is the **pool**, not a single raw connection (a single shared connection isn't
  safe under concurrency).

## 3. `.env` / configuration

- `.env` file, loaded via `python-dotenv`'s `load_dotenv()` **before** reading
  `os.environ`. Never commit `.env`; commit `.env.example` instead.
- DSN format: `postgresql://user:password@host:port/dbname` — the `@` before the host is
  load-bearing; a stray `:` there gets parsed as "password" or breaks host resolution
  entirely (hit this bug twice — `apple:localhost:5432` parsed `localhost` as a password,
  not a host).

## 4. Schema design — decision log

Reasoned through iteratively; final structural decisions, in the order they were locked in:

| Decision | Resolution |
|---|---|
| `Board` — own table or derived? | **Derived** — reconstructed by replaying `moves` in order. No `boards` table. |
| `GamePlayer` scope | Per-**game**, not per-user (`gameId` + `userId` both on the row) — supports one user playing multiple games, including local hot-seat (same user as both players). |
| `Game` status tracking | Single `status` enum (`IN_PROGRESS`/`DRAW`/`COMPLETED`) instead of separate `is_draw` boolean + status string that could contradict each other. |
| `Game.winnerId` target | References **`GamePlayer.id`**, not `User.id` — gives you "which colour won" for free. |
| `Move.gameId` | Initially removed as redundant (derivable via `gameplayerId → GamePlayer.gameId`), then **deliberately re-added** — needed so the DB itself can enforce `UNIQUE(gameId, row, column)`, a constraint that can't reference columns outside the table. |
| `moveNumber` race condition | Considered: row locking (`SELECT ... FOR UPDATE`), per-game `SEQUENCE` objects, retry-on-conflict. **Chose retry-on-conflict** via `UNIQUE(gameId, moveNumber)` — justified because turn-based play has natural mutual exclusion, so real collisions are rare; matches effort to actual risk rather than theoretical risk. |
| Colour | Started as free `TEXT`, then a `CHECK`, then realized `CHECK` can't see across rows (can't stop two players sharing a colour) — needed a **`UNIQUE(gameId, colour)`** constraint instead. Colour itself became a Postgres `ENUM` type (`player_colour`) to reject invalid/typo'd values at the type level. Expanded beyond the traditional 2 (red/yellow) to 4 (`RED`,`YELLOW`,`GREEN`,`BLUE`) to leave room for >2 players later. |
| Naming convention | Standardized on **lowercase snake_case, no quoted identifiers** — Postgres folds unquoted names to lowercase by default; quoting locks you into exact-case matching everywhere forever. Fixed earlier inconsistency (mixed `"User"` quoted-capitalized vs `winner_id` snake_case). |
| Circular FK (`games` ↔ `gameplayers`) | `games.winner_id` references `gameplayers.id`, but `gameplayers.game_id` references `games.id`. Resolved by creating `games` first with `winner_id` as a plain nullable `INTEGER` (no constraint), creating `gameplayers` next, then `ALTER TABLE games ADD CONSTRAINT ... FOREIGN KEY` afterward. |

**Known open items on the schema (flagged, not yet decided):**
- No cap on number of `gameplayers` per game — currently unlimited up to available colours (4). Is that intentional?
- No "lobby / waiting for players" state in `game_status` — does colour-picking-at-start imply a pre-`IN_PROGRESS` phase that's currently missing?
- `email NOT NULL` — decided as a default, worth confirming it's a real product requirement.

Final schema file: `schema.sql` (users, game_status enum, player_colour enum, games,
gameplayers, moves — with the ALTER TABLE fix for the circular FK).

## 5. Running the schema / transactions in practice

- `schema.py` reads `schema.sql` and runs it as **one `cur.execute()` call** — works
  because passing no params falls back to Postgres's simple query protocol, which allows
  multiple `;`-separated statements in one string. This only works for **unparameterized**
  SQL — never mix this pattern with parameterized queries.
- `schema.sql` is currently **not safely re-runnable** (no `IF NOT EXISTS` anywhere) —
  practical workaround for now is drop-and-recreate the dev DB when iterating.
- **`with` blocks don't create variable scope in Python** — only the underlying
  *resource* (cursor, connection) becomes unsafe to use after the block exits; plain
  values extracted inside (e.g. `game_id = row["id"]`) remain valid after the block ends.
- **Every operation on a psycopg3 connection happens inside a transaction** by default
  (non-autocommit) — even a single `SELECT`. The transaction boundary is "everything
  between commits," not "everything you intended to group" — easy to accidentally couple
  unrelated statements if you're not deliberate about where `commit()` is called.
- Rule of thumb going forward: **one `with pool.connection()` block = one logical unit of
  work = one commit** (or a rollback via exception) — not one block per DB call.
- Type-checker friction hit twice, both false positives worth understanding rather than
  blindly suppressing:
  - `.execute()` overload complaint on a non-literal string (file contents) — psycopg's
    stubs push toward literal strings as an anti-SQL-injection nudge; safe to
    `# type: ignore` for a trusted, self-authored `schema.sql`.
  - `fetchone()` returning `Optional[Row]` — the type checker can't know an
    `INSERT ... RETURNING` guarantees exactly one row; fixed by explicit
    `if row is None: raise ...` rather than suppressing, since it also improves the
    failure mode (clear error vs. a confusing `NoneType` crash).

## 6. Production Postgres at scale (conceptual, not yet implemented)

- **PgBouncer**-style external pooling: app-side pools (many, one per process) → a small
  number of real Postgres connections, since each Postgres connection is a full OS
  process server-side and `max_connections` is limited.
- **Read replicas** for read-heavy, staleness-tolerant queries; primary stays
  authoritative for writes and anything needing up-to-the-moment correctness.
- **Sharding by `game_id`** as the natural partition key if a single primary's write
  throughput is ever actually exceeded — the schema already carries `game_id` on every
  child table, which is what makes this viable without a redesign.
- **Redis** as an external, shared, cross-process cache for the derived board — necessary
  once there's more than one API server, since an in-process Python cache doesn't survive
  a request landing on a different server instance.
- Concrete arithmetic check done: ~1M concurrent games at ~1 move/15s ≈ 66k writes/sec —
  plausibly within reach of a well-tuned single primary + pooling; sharding/caching become
  necessary only past that or under burstier load (e.g. bot-speed games). **Lesson:
  estimate real throughput before reaching for distributed-system complexity.**

## 7. Repository pattern — design reasoned through (not yet coded)

- Chose **Repository pattern** (option 2 of 3 considered: manual `class_row` mapping,
  repository, full ORM) — keeps domain classes (`Game`, `Move`, etc.) free of SQL
  knowledge; `GameRepository` owns persistence.
- **Fetching `Game` + `GamePlayer`s + `Move`s**: JOIN initially considered, then rejected
  in favor of **separate queries per table** — a 3-table JOIN fans out badly (each `move`
  row repeats both the `games` and the relevant `gameplayers` row), making Python-side
  de-duplication more complex than three small independent queries. JOINs remain the right
  tool for one-to-one/many-to-one relationships, filtering through a related table, or
  aggregates — just not for hydrating a nested one-to-many collection.
- **`Board.from_moves(moves)`** established as a `@classmethod` (alternative constructor)
  — used specifically because there's no `Board` instance yet when reconstructing from
  move history. Confirmed this becomes the **cold-path fallback** once Redis caching is
  in place, not the everyday path.
- **Cached board mechanics** (still being finalized):
  - Data shape: 2D array, current lean is storing **colour** per cell directly (cheap to
    render) — open question vs. storing `gameplayer_id` (needs a lookup for colour, but
    ties directly to the player).
  - Cache miss triggers: cold cache, or (at scale, multi-server) a request landing on a
    server/process without the relevant in-memory state — resolved by using **Redis**
    (external, shared) rather than in-process memory, once more than one API server exists.
  - Applying a new move to a cached board = one array-index assignment, **not** a full
    replay — full reconstruction (`Board.from_moves`) is only for cache-miss cases.
  - `checkResult` should check only the four lines through the **last placed move's**
    (row, column) — not rescan the whole board (callback to the very first LLD review).
  - **Write ordering resolved**: validate legality → persist move to DB (source of truth)
    → update cache/board → checkResult → if win/draw, persist status + winnerId to DB →
    return result. DB-first, cache-after ensures the cache never reflects a move that
    wasn't actually durably saved.

**Still open / next steps when resuming:**
1. **Turn order** — not yet resolved precisely. Needs either (a) an explicit "player
   order" column on `gameplayers` (created-at ordering may already serve this — check
   whether `gameplayers.id` insertion order is reliable enough, or whether an explicit
   `turn_order` column is needed), or (b) deriving strictly from move history, which
   requires knowing who moved first (may be self-describing from the first `Move` row
   itself, without needing a new column — worth confirming).
2. Clear up **what "partial move" failure actually referred to** — legality check happens
   *before* any DB insert, so there's no partial-move-to-fix at that stage. The real open
   question is what happens if the DB insert of a move succeeds but the *cache update*
   afterward fails — does that need reconciliation logic, or does the cache just
   self-heal on next read via the cold-path fallback?
3. Confirm **where the legality check reads board state from** — Redis primarily, with
   `Board.from_moves()` as fallback on a cache miss — and make that explicit in the flow.
4. Write actual `GameRepository` method signatures (`get_by_id`, `save`, `create`, etc.)
   once turn order and the partial-move question are settled.
5. Schema open items from section 4 (player-count cap, lobby status) — decide when
   relevant, not blocking repository work.

---

*Logged for checkpoint-ledger: today's assignment (implement DB, exercise transactions)
was completed — schema, pool, one working atomic transaction with tested
commit/rollback. Everything from section 7 onward was unplanned scope (repository
pattern, N+1, production scaling) — good learning, but worth noting as a deviation from
plan when updating the ledger.*
