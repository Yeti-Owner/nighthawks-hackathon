"""
database.py
-----------
SQLite setup for the Middleman backend on Vultr.
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD / Debian 12

Key decisions:
  - WAL journal mode    → non-blocking reads during writes
  - cache_size = -1000  → cap SQLite page cache at ~1MB
  - synchronous = NORMAL → safe but faster than FULL
  - temp_store = MEMORY  → small temp ops stay in RAM, not disk
  - Indexes on session_id → fast lookups AND fast DELETEs at disposal time
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "middleman.db"

# PRAGMAs applied to every new connection
_PRAGMAS = """
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous  = NORMAL;
    PRAGMA cache_size   = -1000;
    PRAGMA temp_store   = MEMORY;
    PRAGMA foreign_keys = ON;
"""


@contextmanager
def get_conn():
    """
    Yield a tuned SQLite connection.
    Auto-commits on success, rolls back on exception, always closes.
    check_same_thread=False is safe here because FastAPI runs a single
    synchronous worker (1 vCPU) — no concurrent thread conflicts.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_PRAGMAS)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Create all tables and indexes on startup.
    Indexes are on session_id — used by both SELECT (calc) and DELETE (disposal).
    """
    with get_conn() as conn:
        conn.executescript("""
            -- ── Arduino Log ────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS arduino_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                picked_up_at TEXT    NOT NULL,
                duration_sec REAL    NOT NULL,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_arduino_session
                ON arduino_log(session_id);

            -- ── Study Tracker Log (Face Webcam) ───────────────────────────
            -- S=session_id, T=time(HH:MM:SS EST), E=event_type
            -- Events: SS SE FL FF LA LB
            CREATE TABLE IF NOT EXISTS study_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                event_time  TEXT    NOT NULL,
                event_type  TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_study_session
                ON study_log(session_id);

            -- ── Phone Webcam Log (placeholder) ────────────────────────────
            -- Slot reserved; define event codes once phone-cam log is spec'd.
            CREATE TABLE IF NOT EXISTS phone_cam_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                event_time  TEXT    NOT NULL,
                event_type  TEXT    NOT NULL,
                extra_data  TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_phone_cam_session
                ON phone_cam_log(session_id);

            -- ── Calculated Stats Cache ─────────────────────────────────────
            -- Final home for all computed values. Raw logs are deleted after
            -- stats are written here (see _dispose_logs in main.py).
            CREATE TABLE IF NOT EXISTS session_stats (
                session_id           INTEGER PRIMARY KEY,
                phone_pickups        INTEGER,
                total_phone_sec      REAL,
                avg_pickup_duration  REAL,
                session_duration_sec REAL,
                total_look_away_sec  REAL,
                total_face_lost_sec  REAL,
                look_away_count      INTEGER,
                face_lost_count      INTEGER,
                focus_pct            REAL,
                phone_cam_stat_1     REAL,
                phone_cam_stat_2     REAL,
                last_updated         DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)