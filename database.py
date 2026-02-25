import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path("habits.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        reminder_time TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        chat_id TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER,
        date TEXT,
        FOREIGN KEY (habit_id) REFERENCES habits (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminder_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        sent_at TEXT NOT NULL
    )
    """)

    cursor.execute("PRAGMA table_info(habits)")
    habit_columns = {row["name"] for row in cursor.fetchall()}
    if "user_id" not in habit_columns:
        cursor.execute("ALTER TABLE habits ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


def create_habit(name: str, reminder_time: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO habits (name, reminder_time) VALUES (?, ?)",
        (name, reminder_time)
    )

    conn.commit()
    conn.close()


def get_habits():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM habits WHERE is_active = 1")
    habits = cursor.fetchall()

    conn.close()
    return habits


def mark_done_today(habit_id: int):
    today = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM completions WHERE habit_id = ? AND date = ? LIMIT 1",
        (habit_id, today)
    )
    already_done = cursor.fetchone()

    if not already_done:
        cursor.execute(
            "INSERT INTO completions (habit_id, date) VALUES (?, ?)",
            (habit_id, today)
        )
        conn.commit()

    conn.close()


def get_done_habit_ids_for_today() -> set[int]:
    today = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT habit_id FROM completions WHERE date = ?",
        (today,)
    )
    rows = cursor.fetchall()

    conn.close()
    return {row["habit_id"] for row in rows}


def was_reminder_sent(habit_id: int, sent_at: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM reminder_log WHERE habit_id = ? AND sent_at = ? LIMIT 1",
        (habit_id, sent_at),
    )
    row = cursor.fetchone()

    conn.close()
    return row is not None


def log_reminder_sent(habit_id: int, sent_at: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO reminder_log (habit_id, sent_at) VALUES (?, ?)",
        (habit_id, sent_at),
    )

    conn.commit()
    conn.close()


def upsert_user(name: str, chat_id: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE chat_id = ? LIMIT 1", (chat_id,))
    existing = cursor.fetchone()

    if existing:
        user_id = existing["id"]
        cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    else:
        cursor.execute(
            "INSERT INTO users (name, chat_id) VALUES (?, ?)",
            (name, chat_id),
        )
        user_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return user_id


def get_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users ORDER BY id")
    users = cursor.fetchall()

    conn.close()
    return users


def get_habits_for_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM habits WHERE is_active = 1 AND user_id = ?",
        (user_id,),
    )
    habits = cursor.fetchall()

    conn.close()
    return habits


def create_habit_for_user(user_id: int, name: str, reminder_time: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO habits (name, reminder_time, user_id) VALUES (?, ?, ?)",
        (name, reminder_time, user_id),
    )

    conn.commit()
    conn.close()


def get_chat_id_for_habit(habit_id: int) -> str | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT users.chat_id
        FROM habits
        JOIN users ON users.id = habits.user_id
        WHERE habits.id = ?
        LIMIT 1
        """,
        (habit_id,),
    )
    row = cursor.fetchone()

    conn.close()
    if row is None:
        return None
    return row["chat_id"]