import os

from app.auth.jwt_handler import get_password_hash
from app.core.database import session_scope


def ensure_default_admin() -> None:
    email = os.getenv("DEFAULT_ADMIN_EMAIL")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    if not email or not password:
        return

    full_name = os.getenv("DEFAULT_ADMIN_FULL_NAME", "Default Admin")

    with session_scope() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if existing:
            conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
            return

        hashed = get_password_hash(password)
        conn.execute(
            "INSERT INTO users (email, full_name, hashed_password, role) VALUES (?, ?, ?, 'admin')",
            (email, full_name, hashed),
        )
