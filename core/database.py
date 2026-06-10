"""
Module 2: Database Generation
- Takes a DataFrame and writes it into a SQLite database
- No manual SQL required from the user
- Each session gets its own .db file
- Exposes execute_query() for running SQL safely
"""

import os
import sqlite3
import pandas as pd
from typing import Tuple, Optional
import uuid


DB_DIR = os.path.join(os.path.dirname(__file__), "..", "database", "sessions")


def get_session_db_path(session_id: str) -> str:
    """Return the SQLite file path for a given session ID."""
    os.makedirs(DB_DIR, exist_ok=True)
    return os.path.join(DB_DIR, f"{session_id}.db")


def create_database(
    df: pd.DataFrame,
    table_name: str,
    session_id: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Write a DataFrame into a SQLite database table.

    Returns:
        (db_path, session_id)  — so the caller can store these in session state.
    """
    if session_id is None:
        session_id = uuid.uuid4().hex[:12]

    db_path = get_session_db_path(session_id)

    conn = sqlite3.connect(db_path)
    try:
        # Write the whole DataFrame as a SQL table (replace if exists)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()
    finally:
        conn.close()

    return db_path, session_id


def execute_query(db_path: str, sql: str) -> pd.DataFrame:
    """
    Run a SELECT query against the SQLite database.
    Returns results as a DataFrame.
    Raises RuntimeError on failure.
    """
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(sql, conn)
    except Exception as e:
        raise RuntimeError(f"Query execution failed: {e}") from e
    finally:
        conn.close()
    return df


def list_tables(db_path: str) -> list:
    """Return a list of all table names in the database."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
    return tables


def get_table_preview(db_path: str, table_name: str, n: int = 5) -> pd.DataFrame:
    """Return the first n rows of a table."""
    return execute_query(db_path, f"SELECT * FROM {table_name} LIMIT {n};")
