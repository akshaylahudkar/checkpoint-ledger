from db import pool
from pathlib import Path

def run_schema():
    schema_sql = Path(__file__).parent.joinpath("schema.sql").read_text()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql) # type: ignore[arg-type]
        conn.commit()

if __name__ == "__main__":
    run_schema()
