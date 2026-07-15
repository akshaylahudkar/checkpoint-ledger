from db import pool

def create_game_with_first_player(user_id: int, colour: str):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            # Insert into games, capture the generated id
            cur.execute(
                "INSERT INTO games (status) VALUES (%s) RETURNING id",
                ("IN_PROGRESS",)
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT ... RETURNING id returned no row")
            game_id = row["id"]

            cur.execute(
                """
                INSERT INTO gameplayers (user_id, game_id, colour)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (user_id, game_id, colour)
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT ... RETURNING id returned no row")
            gameplayer_id = row["id"]

        conn.commit()

    return game_id, gameplayer_id

def create_user(name: str, email: int):
    


create_game_with_first_player(user_id=99999, colour="RED")  # user 99999 doesn't exist