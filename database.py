"""
database.py
-----------
SQLite setup for the Middleman backend on Vultr.
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD / Debian 12

Tuning applied to every connection via individual execute() calls:
  - WAL journal mode         → non-blocking reads during writes
  - cache_size = -1000       → cap SQLite page cache at ~1MB
  - synchronous = NORMAL     → safe but faster than FULL
  - temp_store = MEMORY      → small temp ops stay in RAM, not disk
  - foreign_keys = ON        → enforce FK constraints
  - wal_autocheckpoint = 100 → merge WAL back to DB at ~400KB (vs default ~4MB)

user_id note:
  user_id is present in all log tables and session_stats but is NOT enforced.
  It is nullable with no foreign key — a placeholder for future personalization.
  Pass it in from ingest endpoints when available; leave NULL otherwise.
  See /stats/user/{user_id} in main.py for the user-scoped GET endpoint.

Arduino / bridge note:
  serial_bridge.py POSTs one pickup per row to /arduino/log on CTRL+C.
  session_id increments per pickup (1, 2, 3…) — acts as a pickup ID,
  not a study-session ID. Stats aggregate ALL arduino_log rows.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "middleman.db"

_PRAGMAS = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous  = NORMAL",
    "PRAGMA cache_size   = -1000",
    "PRAGMA temp_store   = MEMORY",
    "PRAGMA foreign_keys = ON",
    "PRAGMA wal_autocheckpoint = 100",
]


@contextmanager
def get_conn():
    """
    Yield a tuned SQLite connection.
    Auto-commits on success, rolls back on exception, always closes.
    check_same_thread=False is safe — single synchronous worker (1 vCPU).
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for pragma in _PRAGMAS:
        conn.execute(pragma)
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
    Create all tables and indexes on first startup.
    executescript() is acceptable here — DDL-only, runs once at boot.
    Indexes cover both SELECT (calculation) and DELETE (disposal) paths.
    """
    with get_conn() as conn:
        conn.executescript("""
            -- ── Arduino Log ────────────────────────────────────────────────
            -- One row per pickup, POSTed individually by serial_bridge.py.
            -- session_id increments per pickup (acts as pickup ID).
            -- user_id is nullable — populate when available.
            CREATE TABLE IF NOT EXISTS arduino_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                user_id      INTEGER,
                picked_up_at TEXT    NOT NULL,
                duration_sec REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_arduino_session
                ON arduino_log(session_id);
            CREATE INDEX IF NOT EXISTS idx_arduino_user
                ON arduino_log(user_id);

            -- ── Study Tracker Log (Face Webcam) ───────────────────────────
            -- S=session_id, T=time(HH:MM:SS EST), E=event_type
            -- Events: SS=session_start  SE=session_end
            --         LA=look_away      LB=look_back
            --         FL=face_lost      FF=face_found
            -- user_id is nullable — populate when available.
            CREATE TABLE IF NOT EXISTS study_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                user_id     INTEGER,
                event_time  TEXT    NOT NULL,
                event_type  TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_study_session
                ON study_log(session_id);
            CREATE INDEX IF NOT EXISTS idx_study_user
                ON study_log(user_id);

            -- ── Phone Webcam Log (placeholder) ────────────────────────────
            -- Tracks when the phone lights up. A separate AI will process
            -- images. Define event_type codes once the log format is set.
            -- user_id is nullable — populate when available.
            CREATE TABLE IF NOT EXISTS phone_cam_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                user_id     INTEGER,
                event_time  TEXT    NOT NULL,
                event_type  TEXT    NOT NULL,
                extra_data  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_phone_cam_session
                ON phone_cam_log(session_id);
            CREATE INDEX IF NOT EXISTS idx_phone_cam_user
                ON phone_cam_log(user_id);

            -- ── Calculated Stats Cache ─────────────────────────────────────
            -- Final home for all computed values. Raw logs deleted after write.
            --
            -- user_id: nullable — links stats to a person once user system is built.
            --
            -- Arduino-derived (aggregated across ALL arduino_log rows):
            --   phone_pickups, total_held_sec, avg_held_sec,
            --   max_held_sec, min_held_sec
            --
            -- Face-cam-derived (per session_id):
            --   session_duration_sec  — SS to SE wall time
            --   total_look_away_sec   — sum of all LA→LB intervals
            --   look_away_count       — number of LA events
            --   avg_look_away_sec     — total_look_away_sec / look_away_count
            --   longest_look_away_sec — longest single LA→LB interval
            --   first_look_away_sec   — duration of the very first LA→LB pair
            --   total_face_lost_sec   — sum of all FL→FF intervals
            --   face_lost_count       — number of FL events
            --   focus_time_sec        — session_duration - look_away - face_lost
            --   focus_pct             — (focus_time_sec / session_duration_sec) * 100
            --
            -- Phone-cam-derived (placeholder):
            --   phone_cam_stat_1, phone_cam_stat_2
            CREATE TABLE IF NOT EXISTS session_stats (
                session_id            INTEGER PRIMARY KEY,
                user_id               INTEGER,
                -- Arduino-derived
                phone_pickups         INTEGER,
                total_held_sec        REAL,
                avg_held_sec          REAL,
                max_held_sec          REAL,
                min_held_sec          REAL,
                -- Face-cam-derived
                session_duration_sec  REAL,
                total_look_away_sec   REAL,
                look_away_count       INTEGER,
                avg_look_away_sec     REAL,
                longest_look_away_sec REAL,
                first_look_away_sec   REAL,
                total_face_lost_sec   REAL,
                face_lost_count       INTEGER,
                focus_time_sec        REAL,
                focus_pct             REAL,
                -- Phone-cam-derived (placeholder)
                phone_cam_stat_1      REAL,
                phone_cam_stat_2      REAL,
                -- Meta
                last_updated          DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_stats_user
                ON session_stats(user_id);
        """)