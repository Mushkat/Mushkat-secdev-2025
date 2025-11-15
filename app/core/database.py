import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Generator, Iterator

from app.core.settings import ensure_settings_loaded

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./parking.db")


def _resolve_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        path = database_url.replace("sqlite:///", "", 1)
    elif database_url.startswith("sqlite://"):
        path = database_url.replace("sqlite://", "", 1)
    else:
        raise ValueError("Unsupported database URL; only sqlite:/// is supported")

    if path == ":memory:":
        return ":memory:"

    db_path = Path(path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


sqlite3.register_adapter(date, lambda value: value.isoformat())
sqlite3.register_converter("DATE", lambda value: date.fromisoformat(value.decode()))

DB_PATH = _resolve_path(DATABASE_URL)

_INITIALIZED = False


def _raw_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_initialized() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    init_db()
    _INITIALIZED = True


def connect() -> sqlite3.Connection:
    ensure_settings_loaded()
    _ensure_initialized()
    conn = _raw_connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    ensure_settings_loaded()
    with _raw_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                description TEXT,
                owner_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                booking_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(slot_id) REFERENCES slots(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                expires_at TIMESTAMP NOT NULL
            );
            """
        )
        _ensure_role_column(conn)


@contextmanager
def session_scope() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _ensure_role_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "role" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.commit()
