"""
main.py
-------
Middleman FastAPI backend — runs on Vultr (Debian 12, port 8000).
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD

Memory strategy:
  - Arduino stats computed entirely in SQL (COUNT/SUM/AVG/MAX/MIN — zero Python load)
  - Face-cam stats stream one row at a time via cursor iteration (no fetchall)
  - Batch inserts use generator expressions (no intermediate list in RAM)
  - Raw logs deleted immediately after stats are safely saved (same transaction)
  - WAL checkpoint forced after disposal to keep SSD usage predictable
  - Uvicorn locked to 1 worker, backlog capped, keep-alive trimmed

Arduino / bridge flow:
  1. serial_bridge.py (local PC) monitors Serial output live
  2. On CTRL+C, POSTs each pickup individually to POST /arduino/log
  3. Each POST carries: session_id (per-pickup counter), user_id (optional),
     picked_up_at (PC timestamp), duration_sec
  4. Stats calculated on demand → POST /stats/calculate/{session_id}
  5. Raw logs disposed after stats are written

user_id:
  Present in all ingest endpoints and stored in all log tables.
  Optional everywhere — NULL if not provided.
  Carried through to session_stats for future personalization.
  GET /stats/user/{user_id} returns all cached stats for that user.
  GET /stats/user/{user_id}/session/{session_id} returns one session for that user.

Run with:
  uv run main.py
  — or —
  uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
"""

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from database import init_db, get_conn
from schemas import (
    ArduinoEntry,
    StudyEvent, StudyBatch,
    PhoneCamEvent, PhoneCamBatch,
    SessionStats,
)


# ── App Startup ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Middleman Backend",
    description="Receives Arduino/webcam logs, calculates stats, disposes raw logs.",
    version="0.5.0",
    lifespan=lifespan,
    # Uncomment both lines below when fully deployed to reduce overhead:
    # docs_url=None,
    # redoc_url=None,
)


# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok"}


# ═════════════════════════════════════════════════════════════════════════════
# INGEST ROUTES — receive data from hardware / webcams
# ═════════════════════════════════════════════════════════════════════════════

# ── Arduino ──────────────────────────────────────────────────────────────────

@app.post("/arduino/log")
def log_arduino(entry: ArduinoEntry):
    """
    Receive a single pickup event from serial_bridge.py.
    user_id is optional — pass it once user accounts are implemented.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO arduino_log (session_id, user_id, picked_up_at, duration_sec) VALUES (?,?,?,?)",
            (entry.session_id, entry.user_id, entry.picked_up_at, entry.duration_sec),
        )
    return {"status": "ok"}


# ── Study Tracker (Face Webcam) ───────────────────────────────────────────────

@app.post("/study/log")
def log_study_event(event: StudyEvent):
    """Receive a single face-cam event."""
    event.validate_event()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO study_log (session_id, user_id, event_time, event_type) VALUES (?,?,?,?)",
            (event.session_id, event.user_id, event.event_time, event.event_type),
        )
    return {"status": "ok"}


@app.post("/study/batch")
def log_study_batch(batch: StudyBatch):
    """
    Batch insert for a full study-session CSV dump.
    Validates all events first, then inserts via generator (no list in RAM).
    """
    for e in batch.events:
        e.validate_event()
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO study_log (session_id, user_id, event_time, event_type) VALUES (?,?,?,?)",
            ((e.session_id, e.user_id, e.event_time, e.event_type) for e in batch.events),
        )
    return {"status": "ok", "logged": len(batch.events)}


# ── Phone Webcam (placeholder) ────────────────────────────────────────────────

@app.post("/phone-cam/log")
def log_phone_cam_event(event: PhoneCamEvent):
    """
    Placeholder — tracks when the phone lights up.
    Update PhoneCamEvent in schemas.py once event codes are defined.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO phone_cam_log (session_id, user_id, event_time, event_type, extra_data) VALUES (?,?,?,?,?)",
            (event.session_id, event.user_id, event.event_time, event.event_type, event.extra_data),
        )
    return {"status": "ok"}


@app.post("/phone-cam/batch")
def log_phone_cam_batch(batch: PhoneCamBatch):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO phone_cam_log (session_id, user_id, event_time, event_type, extra_data) VALUES (?,?,?,?,?)",
            ((e.session_id, e.user_id, e.event_time, e.event_type, e.extra_data) for e in batch.events),
        )
    return {"status": "ok", "logged": len(batch.events)}


# ═════════════════════════════════════════════════════════════════════════════
# CALCULATION FUNCTIONS
# All receive an open connection and session_id.
# None of them load bulk data into Python — SQL or cursor streaming only.
# ═════════════════════════════════════════════════════════════════════════════

def _calc_arduino_stats(conn, session_id: int) -> dict:
    """
    Aggregate ALL arduino_log rows entirely in SQL.
    No Python-side data load — COUNT/SUM/AVG/MAX/MIN run on the DB side.

    Aggregates ALL rows (not filtered by session_id) because the bridge
    increments session_id per pickup, making each row its own session_id.

    Stats:
      phone_pickups  — how many times the phone was picked up
      total_held_sec — total seconds the phone was held this session
      avg_held_sec   — average hold duration per pickup
      max_held_sec   — longest single pickup
      min_held_sec   — shortest single pickup
    """
    row = conn.execute(
        """
        SELECT
            COUNT(*)           AS phone_pickups,
            SUM(duration_sec)  AS total_held_sec,
            AVG(duration_sec)  AS avg_held_sec,
            MAX(duration_sec)  AS max_held_sec,
            MIN(duration_sec)  AS min_held_sec
        FROM arduino_log
        """
    ).fetchone()

    if not row or row["phone_pickups"] == 0:
        return {}

    return {
        "phone_pickups":  row["phone_pickups"],
        "total_held_sec": row["total_held_sec"],
        "avg_held_sec":   row["avg_held_sec"],
        "max_held_sec":   row["max_held_sec"],
        "min_held_sec":   row["min_held_sec"],
    }


def _time_to_sec(t: str):
    """
    Convert HH:MM:SS to total seconds.
    Returns None on malformed input — caller skips the row instead of
    crashing the session and stranding raw logs undisposed.
    """
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def _calc_study_stats(conn, session_id: int) -> dict:
    """
    Stream face-cam events one row at a time — no fetchall, no bulk RAM load.
    Rows are processed and discarded as the cursor iterates.

    Event pairs:
      SS → SE  : session wall time (session_duration_sec)
      LA → LB  : look-away intervals → total, avg, longest, first
      FL → FF  : face-lost intervals → total, count

    Derived:
      focus_time_sec = session_duration_sec - total_look_away_sec - total_face_lost_sec
      focus_pct      = (focus_time_sec / session_duration_sec) * 100
    """
    cursor = conn.execute(
        """
        SELECT event_time, event_type
        FROM   study_log
        WHERE  session_id = ?
        ORDER  BY event_time ASC
        """,
        (session_id,),
    )

    session_start   = session_end = None
    look_away_sec   = 0.0
    look_away_count = 0
    first_look_away_sec   = None
    longest_look_away_sec = 0.0
    face_lost_sec   = 0.0
    face_lost_count = 0
    _la_start = _fl_start = None
    has_rows  = False

    for row in cursor:                          # ← one row at a time
        has_rows = True
        ts = _time_to_sec(row["event_time"])
        if ts is None:
            continue                            # skip malformed timestamp

        e = row["event_type"]

        if   e == "SS":
            session_start = ts

        elif e == "SE":
            session_end = ts

        elif e == "LA":
            _la_start = ts
            look_away_count += 1

        elif e == "LB" and _la_start is not None:
            duration = ts - _la_start
            look_away_sec += duration
            if first_look_away_sec is None:     # capture the very first one
                first_look_away_sec = duration
            if duration > longest_look_away_sec:
                longest_look_away_sec = duration
            _la_start = None

        elif e == "FL":
            _fl_start = ts
            face_lost_count += 1

        elif e == "FF" and _fl_start is not None:
            face_lost_sec += ts - _fl_start
            _fl_start = None

    if not has_rows:
        return {}

    session_duration_sec = (
        session_end - session_start
        if session_start is not None and session_end is not None
        else None
    )

    avg_look_away_sec = (
        look_away_sec / look_away_count
        if look_away_count > 0
        else None
    )

    # focus_time: clamp to 0 in case of overlapping events or clock drift
    focus_time_sec = focus_pct = None
    if session_duration_sec is not None and session_duration_sec > 0:
        focus_time_sec = max(0.0, session_duration_sec - look_away_sec - face_lost_sec)
        focus_pct      = round((focus_time_sec / session_duration_sec) * 100, 2)

    return {
        "session_duration_sec":  session_duration_sec,
        "total_look_away_sec":   look_away_sec,
        "look_away_count":       look_away_count,
        "avg_look_away_sec":     avg_look_away_sec,
        "longest_look_away_sec": longest_look_away_sec if look_away_count > 0 else None,
        "first_look_away_sec":   first_look_away_sec,
        "total_face_lost_sec":   face_lost_sec,
        "face_lost_count":       face_lost_count,
        "focus_time_sec":        focus_time_sec,
        "focus_pct":             focus_pct,
    }


def _calc_phone_cam_stats(conn, session_id: int) -> dict:
    """
    Placeholder — implement once the phone-cam log format is defined.
    The phone cam tracks when the phone screen lights up; a separate AI
    processes image content.

    Pattern to follow when implementing:
        cursor = conn.execute(
            "SELECT event_time, event_type FROM phone_cam_log "
            "WHERE session_id = ? ORDER BY event_time ASC",
            (session_id,)
        )
        for row in cursor:   # ← stream, don't fetchall
            ...
    ── Rename stat keys and fill formulas when ready ──
    """
    return {
        "phone_cam_stat_1": None,  # ← FILL IN
        "phone_cam_stat_2": None,  # ← FILL IN
    }


def _get_user_id_for_session(conn, session_id: int):
    """
    Look up user_id for a session from study_log.
    Returns None if no study events exist or user_id was not provided.
    """
    row = conn.execute(
        "SELECT user_id FROM study_log WHERE session_id = ? LIMIT 1",
        (session_id,),
    ).fetchone()
    return row["user_id"] if row else None


def _save_stats(conn, session_id: int, user_id, stats: dict):
    """Upsert calculated stats into the session_stats cache table."""
    conn.execute(
        """
        INSERT INTO session_stats (
            session_id, user_id,
            phone_pickups, total_held_sec, avg_held_sec, max_held_sec, min_held_sec,
            session_duration_sec, total_look_away_sec, look_away_count,
            avg_look_away_sec, longest_look_away_sec, first_look_away_sec,
            total_face_lost_sec, face_lost_count,
            focus_time_sec, focus_pct,
            phone_cam_stat_1, phone_cam_stat_2,
            last_updated
        ) VALUES (
            :session_id, :user_id,
            :phone_pickups, :total_held_sec, :avg_held_sec, :max_held_sec, :min_held_sec,
            :session_duration_sec, :total_look_away_sec, :look_away_count,
            :avg_look_away_sec, :longest_look_away_sec, :first_look_away_sec,
            :total_face_lost_sec, :face_lost_count,
            :focus_time_sec, :focus_pct,
            :phone_cam_stat_1, :phone_cam_stat_2,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(session_id) DO UPDATE SET
            user_id               = excluded.user_id,
            phone_pickups         = excluded.phone_pickups,
            total_held_sec        = excluded.total_held_sec,
            avg_held_sec          = excluded.avg_held_sec,
            max_held_sec          = excluded.max_held_sec,
            min_held_sec          = excluded.min_held_sec,
            session_duration_sec  = excluded.session_duration_sec,
            total_look_away_sec   = excluded.total_look_away_sec,
            look_away_count       = excluded.look_away_count,
            avg_look_away_sec     = excluded.avg_look_away_sec,
            longest_look_away_sec = excluded.longest_look_away_sec,
            first_look_away_sec   = excluded.first_look_away_sec,
            total_face_lost_sec   = excluded.total_face_lost_sec,
            face_lost_count       = excluded.face_lost_count,
            focus_time_sec        = excluded.focus_time_sec,
            focus_pct             = excluded.focus_pct,
            phone_cam_stat_1      = excluded.phone_cam_stat_1,
            phone_cam_stat_2      = excluded.phone_cam_stat_2,
            last_updated          = CURRENT_TIMESTAMP
        """,
        {"session_id": session_id, "user_id": user_id, **stats},
    )


def _dispose_logs(conn, session_id: int):
    """
    Delete raw log rows after stats are safely stored.
    All three deletes + checkpoint run inside the same transaction as _save_stats.
    If the save fails, the transaction rolls back and logs are NOT deleted.

    Arduino: ALL rows cleared (session_id is per-pickup, not per-study-session).
    Study / phone-cam: filtered by session_id.

    wal_checkpoint(PASSIVE): merges WAL back to main DB file after deletion.
    Without this, WAL grows silently and never shrinks until process restart.
    """
    conn.execute("DELETE FROM arduino_log")
    conn.execute("DELETE FROM study_log     WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM phone_cam_log WHERE session_id = ?", (session_id,))
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")


# ═════════════════════════════════════════════════════════════════════════════
# STATS ROUTES
# ═════════════════════════════════════════════════════════════════════════════

_STAT_DEFAULTS = {
    "phone_pickups": None, "total_held_sec": None, "avg_held_sec": None,
    "max_held_sec": None, "min_held_sec": None,
    "session_duration_sec": None, "total_look_away_sec": None,
    "look_away_count": None, "avg_look_away_sec": None,
    "longest_look_away_sec": None, "first_look_away_sec": None,
    "total_face_lost_sec": None, "face_lost_count": None,
    "focus_time_sec": None, "focus_pct": None,
    "phone_cam_stat_1": None, "phone_cam_stat_2": None,
}


@app.post("/stats/calculate/{session_id}", response_model=SessionStats)
def calculate_stats(session_id: int):
    """
    1. Fetch user_id for this session from study_log.
    2. Compute all stats (SQL aggregation + cursor streaming).
    3. Upsert into session_stats.
    4. Dispose raw logs + WAL checkpoint.
       Steps 3 and 4 are in one transaction — if save fails, logs survive.
    5. Return stats.
    """
    with get_conn() as conn:
        user_id = _get_user_id_for_session(conn, session_id)
        stats = {
            **_STAT_DEFAULTS,
            **_calc_arduino_stats(conn, session_id),
            **_calc_study_stats(conn, session_id),
            **_calc_phone_cam_stats(conn, session_id),
        }
        _save_stats(conn, session_id, user_id, stats)
        _dispose_logs(conn, session_id)

    return SessionStats(session_id=session_id, user_id=user_id, **stats)


@app.get("/stats/{session_id}", response_model=SessionStats)
def get_stats(session_id: int):
    """Return cached stats for a session. No recomputation."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM session_stats WHERE session_id = ?", (session_id,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No stats for session {session_id}. "
                f"Call POST /stats/calculate/{session_id} first."
            ),
        )
    return SessionStats(**dict(row))


@app.get("/stats/summary/all")
def get_all_stats():
    """Return all cached sessions. Used by the frontend dashboard."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM session_stats ORDER BY session_id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── User-scoped endpoints ─────────────────────────────────────────────────────

@app.get("/stats/user/{user_id}")
def get_stats_by_user(user_id: int):
    """
    Return all cached sessions belonging to a specific user.
    Requires user_id to have been passed during ingest or calculation.
    Returns an empty list if no sessions exist for this user yet.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM session_stats WHERE user_id = ? ORDER BY session_id DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/stats/user/{user_id}/session/{session_id}", response_model=SessionStats)
def get_user_session(user_id: int, session_id: int):
    """
    Return a specific session's stats, scoped to a user.
    Returns 404 if the session doesn't exist or belongs to a different user.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM session_stats WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No stats for user {user_id}, session {session_id}.",
        )
    return SessionStats(**dict(row))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,              # single vCPU — never more than 1
        reload=False,           # reload=True doubles memory usage
        backlog=64,             # cap queued connections (default 2048 is too high)
        timeout_keep_alive=5,   # drop idle connections quickly to free sockets
        access_log=False,       # skip per-request logging to reduce SSD I/O
    )