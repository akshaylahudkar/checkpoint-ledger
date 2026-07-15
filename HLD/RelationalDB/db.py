import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

pool = ConnectionPool(
    conninfo=os.environ["DATABASE_URL"],
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=True
)