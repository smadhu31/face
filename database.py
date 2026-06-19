"""
database.py
Handles SQLite connection, schema creation and seeding the default admin.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

from config import Config


def get_db_connection():
    """Return a new SQLite connection with row factory set to dict-like rows."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
-- ============================================================
-- users: login credentials for both employees and admins
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'employee')),
    employee_id TEXT,                 -- links to employees.employee_id (NULL for admin)
    email TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ============================================================
-- employees: employee master data + face encoding
-- ============================================================
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department TEXT,
    designation TEXT,
    phone TEXT,
    email TEXT UNIQUE,
    photo_path TEXT,
    face_encoding BLOB,               -- pickled numpy array (128-d encoding)
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- attendance: daily check-in / check-out records
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    date TEXT NOT NULL,               -- YYYY-MM-DD
    check_in_time TEXT,               -- HH:MM:SS
    check_out_time TEXT,              -- HH:MM:SS
    working_hours REAL DEFAULT 0,
    status TEXT DEFAULT 'Present',    -- Present / Half Day / Absent
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    UNIQUE(employee_id, date)
);

CREATE INDEX IF NOT EXISTS idx_attendance_emp_date ON attendance(employee_id, date);
CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(is_active);
"""


def init_db():
    """Create tables if they do not exist and seed a default admin user."""
    conn = get_db_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        _seed_default_admin(conn)
    finally:
        conn.close()


def _seed_default_admin(conn):
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin'")
    count = cur.fetchone()["cnt"]
    if count == 0:
        conn.execute(
            """INSERT INTO users (username, password_hash, role, email, is_active, created_at)
               VALUES (?, ?, 'admin', ?, 1, ?)""",
            (
                Config.DEFAULT_ADMIN_USERNAME,
                generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD),
                Config.DEFAULT_ADMIN_EMAIL,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        print(
            f"[INFO] Default admin created -> username: '{Config.DEFAULT_ADMIN_USERNAME}', "
            f"password: '{Config.DEFAULT_ADMIN_PASSWORD}' (please change after first login)"
        )
