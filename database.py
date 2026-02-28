"""
database.py
-----------
SQLite setup for the Middleman backend on Vultr.
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD / Debian 12

Tuning applied to every connection:
  - WAL journal mode    → non-blocking reads during writes
  - cache_size = -1000  → cap SQLite page cache at ~1MB
  - synchronous = NORMAL → safe but faster than FULL
  - temp_store = MEMORY  → small temp ops stay in RAM, not disk
  - Indexes on session_id → fast lookups AND fast DELETEs at disposal time

Arduino / bridge note:
  The new serial_bridge.py monitors Serial live and POSTs each pickup
  individually to /arduino/log when the session ends (CTRL+C).

  Each POST carries:
    session_id   — increments per pickup in the bridge (1 for pickup 1,
                   2 for pickup 2, etc.). It acts as a pickup identifier,
                   not a study-session identifier. Stats for Arduino data
                   are therefore aggregated across ALL rows, not filtered
                   by session_id. See _calc_arduino_stats in main.py.
    picked_up_at — datetime.now() on the PC at send time (ISO format)
    duration_sec — integer seconds the phone was held
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "middleman.db"

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
    check_same_thread=False is safe — single synchronous worker (1 vCPU).
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
    Indexes on session_id used by both SELECT (calc) and DELETE (disposal).
    """
    with get_conn() as conn:
        conn.executescript("""
            -- ── Arduino Log ────────────────────────────────────────────────
            -- One row per pickup, POSTed individually by serial_bridge.py.
            --
            -- session_id   : bridge increments this per pickup (1, 2, 3…)
            --                — acts as pickup ID, not study-session ID
            -- picked_up_at : ISO timestamp from the PC at send time
            -- duration_sec : integer seconds the phone was held
            CREATE TABLE IF NOT EXISTS arduino_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                picked_up_at TEXT    NOT NULL,
                duration_sec REAL    NOT NULL,
                received_at  DATETIME DEFAULT CURRENT_TIMESTAMP
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
            -- Final home for computed values. Raw logs deleted after write.
            -- Arduino stats are aggregated across ALL arduino_log rows
            -- (not per session_id) due to bridge incrementing session_id
            -- per pickup rather than per study session.
            CREATE TABLE IF NOT EXISTS session_stats (
                session_id           INTEGER PRIMARY KEY,
                -- Arduino-derived (aggregated across all arduino_log rows)
                phone_pickups        INTEGER,
                total_held_sec       REAL,
                avg_held_sec         REAL,
                -- Face-cam-derived
                session_duration_sec REAL,
                total_look_away_sec  REAL,
                total_face_lost_sec  REAL,
                look_away_count      INTEGER,
                face_lost_count      INTEGER,
                focus_pct            REAL,
                -- Phone-cam-derived (placeholder)
                phone_cam_stat_1     REAL,
                phone_cam_stat_2     REAL,
                -- Meta
                last_updated         DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)