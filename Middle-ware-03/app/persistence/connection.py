import os

import psycopg
from psycopg import Connection


DB_HOST = os.getenv("CLINICAL_DB_HOST", "localhost")
DB_PORT = int(os.getenv("CLINICAL_DB_PORT", "5432"))
DB_NAME = os.getenv("CLINICAL_DB_NAME", "clinical")
DB_USER = os.getenv("CLINICAL_DB_USER", "clinical")
DB_PASSWORD = os.getenv("CLINICAL_DB_PASSWORD", "clinical123")


def get_connection() -> Connection:
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )