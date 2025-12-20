import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_MAIN = ROOT / "parking.db"
DB_TEST = ROOT / "parking_test.db"
SCHEMA_SQL = ROOT / "db" / "schema.sql"


def run_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def main():
    if DB_TEST.exists():
        DB_TEST.unlink()

    if DB_MAIN.exists():
        shutil.copy(DB_MAIN, DB_TEST)
    conn = sqlite3.connect(DB_TEST)
    conn.row_factory = sqlite3.Row

    try:
        run_schema(conn)

        with conn:
            conn.execute(
                "INSERT INTO users(email, full_name, hashed_password, role) VALUES (?, ?, ?, ?)",
                ("owner@test.com", "Owner", "hash1", "user"),
            )
            conn.execute(
                "INSERT INTO users(email, full_name, hashed_password, role) VALUES (?, ?, ?, ?)",
                ("user@test.com", "User", "hash2", "user"),
            )

            owner_id = conn.execute(
                "SELECT id FROM users WHERE email=?", ("owner@test.com",)
            ).fetchone()["id"]
            user_id = conn.execute(
                "SELECT id FROM users WHERE email=?", ("user@test.com",)
            ).fetchone()["id"]

            conn.execute(
                "INSERT INTO slots(code, description, owner_id) VALUES (?, ?, ?)",
                ("A-101", "Test slot", owner_id),
            )
            slot_id = conn.execute("SELECT id FROM slots WHERE code=?", ("A-101",)).fetchone()["id"]

        booking_date = "2025-12-20"

        def create_booking_atomic(slot_id: int, user_id: int, booking_date: str):
            conn.execute("BEGIN IMMEDIATE;")
            try:
                exists = conn.execute(
                    "SELECT 1 FROM bookings WHERE slot_id=? AND booking_date=? LIMIT 1",
                    (slot_id, booking_date),
                ).fetchone()
                if exists:
                    conn.execute("ROLLBACK;")
                    return False

                conn.execute(
                    "INSERT INTO bookings(slot_id, user_id, booking_date, status) VALUES (?, ?, ?, 'pending')",
                    (slot_id, user_id, booking_date),
                )
                conn.execute("COMMIT;")
                return True
            except Exception:
                conn.execute("ROLLBACK;")
                raise

        ok = create_booking_atomic(slot_id, user_id, booking_date)
        print("Create booking #1:", ok)

        try:
            ok2 = create_booking_atomic(slot_id, user_id, booking_date)
            print("Create booking #2 (should be False):", ok2)
        except sqlite3.IntegrityError as e:
            print("Expected UNIQUE error:", e)

        with conn:
            before = conn.execute("SELECT COUNT(*) AS c FROM bookings").fetchone()["c"]
            conn.execute("DELETE FROM slots WHERE id=?", (slot_id,))
            after = conn.execute("SELECT COUNT(*) AS c FROM bookings").fetchone()["c"]
        print("Bookings before delete slot:", before)
        print("Bookings after delete slot (should be 1):", after)

        with conn:
            conn.execute(
                "INSERT INTO revoked_tokens(jti, expires_at) VALUES (?, ?)",
                ("test-jti-1", "2099-01-01 00:00:00"),
            )
            is_revoked = conn.execute(
                "SELECT 1 FROM revoked_tokens WHERE jti=? AND expires_at > CURRENT_TIMESTAMP LIMIT 1",
                ("test-jti-1",),
            ).fetchone()
        print("Token revoked check (should be True):", bool(is_revoked))

        print("\nOK: проверки прошли, смотри parking_test.db")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
