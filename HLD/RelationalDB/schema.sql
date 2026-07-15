-- ============================================================
-- users
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

-- ============================================================
-- game_status enum
-- ============================================================
CREATE TYPE game_status AS ENUM ('IN_PROGRESS', 'DRAW', 'COMPLETED');

-- ============================================================
-- games
-- created WITHOUT the winner_id foreign key constraint, since
-- gameplayers (which winner_id references) doesn't exist yet.
-- The constraint is added back further down via ALTER TABLE,
-- once gameplayers exists. This breaks the circular dependency.
-- ============================================================
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    status game_status NOT NULL DEFAULT 'IN_PROGRESS',
    winner_id INTEGER  -- FK added later; nullable since an in-progress game has no winner
);

-- ============================================================
-- gameplayers
-- ============================================================
CREATE TABLE gameplayers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    colour TEXT NOT NULL,

    CONSTRAINT fk_gameplayers_user
        FOREIGN KEY (user_id) REFERENCES users(id),

    CONSTRAINT fk_gameplayers_game
        FOREIGN KEY (game_id) REFERENCES games(id),

    -- no two players in the same game can have the same colour
    CONSTRAINT uq_gameplayers_game_colour
        UNIQUE (game_id, colour)
);

-- ============================================================
-- now that gameplayers exists, add the winner_id FK on games
-- ============================================================
ALTER TABLE games
    ADD CONSTRAINT fk_games_winner
        FOREIGN KEY (winner_id) REFERENCES gameplayers(id);

-- ============================================================
-- moves
-- ============================================================
CREATE TABLE moves (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL,
    gameplayer_id INTEGER NOT NULL,
    row INTEGER NOT NULL,
    column_number INTEGER NOT NULL,
    move_number INTEGER NOT NULL,

    CONSTRAINT fk_moves_game
        FOREIGN KEY (game_id) REFERENCES games(id),

    CONSTRAINT fk_moves_gameplayer
        FOREIGN KEY (gameplayer_id) REFERENCES gameplayers(id),

    -- no two discs can occupy the same cell in the same game
    CONSTRAINT uq_moves_game_row_col
        UNIQUE (game_id, row, column_number),

    -- move ordering within a game must be unique
    -- (retry-on-conflict strategy: app catches the violation and retries)
    CONSTRAINT uq_moves_game_movenumber
        UNIQUE (game_id, move_number)
);