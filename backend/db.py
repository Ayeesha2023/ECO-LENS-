from typing import Any, Optional

from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

from config import Config


_pool = MySQLConnectionPool(
    pool_name="ecolens_pool",
    pool_size=5,
    pool_reset_session=True,
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    database=Config.DB_NAME,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
)


def fetch_one(
    query: str,
    params: Optional[tuple[Any, ...]] = None,
) -> Optional[dict[str, Any]]:
    """Run a SELECT query and return one row."""

    connection = None
    cursor = None

    try:
        connection = _pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, params or ())
        return cursor.fetchone()

    except Error as exc:
        raise RuntimeError(f"Database query failed: {exc}") from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


def fetch_all(
    query: str,
    params: Optional[tuple[Any, ...]] = None,
) -> list[dict[str, Any]]:
    """Run a SELECT query and return all rows."""

    connection = None
    cursor = None

    try:
        connection = _pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, params or ())
        return cursor.fetchall()

    except Error as exc:
        raise RuntimeError(f"Database query failed: {exc}") from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


def execute(
    query: str,
    params: Optional[tuple[Any, ...]] = None,
) -> int:
    """Run an INSERT, UPDATE or DELETE query."""

    connection = None
    cursor = None

    try:
        connection = _pool.get_connection()
        cursor = connection.cursor()

        cursor.execute(query, params or ())
        connection.commit()

        return cursor.lastrowid

    except Error as exc:
        if connection is not None:
            connection.rollback()

        raise RuntimeError(f"Database operation failed: {exc}") from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()