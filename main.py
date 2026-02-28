"""
main.py
-------
Middleman FastAPI backend — runs on Vultr (Debian 12, port 8000).
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD

Memory strategy:
  - Arduino stats are computed entirely in SQL (no Python-side data load)
  - Study/phone-cam stats stream rows one at a time via cursor iteration
  - Batch inserts use generator expressions (no intermediate list in RAM)
  - Raw logs are deleted from SQLite immediately after stats are saved
  - Uvicorn is locked to 1 worker with a backlog cap

Run with:
  uv run main.py
  — or —
  uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
"""

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from database import init_db, get_conn
from schemas import (
    ArduinoEntry, ArduinoBatch,
    StudyEvent,   StudyBatch,
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
    version="0.2.0",
    lifespan=lifespan,
    # Disable interactive docs in production to reduce overhead.
    # Set both to None when fully deployed; keep enabled during dev.
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
    """Receive a single phone-pickup event from the Arduino."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO arduino_log (session_id, picked_up_at, duration_sec) VALUES (?,?,?)",
            (entry.session_id, entry.picked_up_at, entry.duration_sec),
        )
    return {"status": "ok"}


@app.post("/arduino/batch")
def log_arduino_batch(batch: ArduinoBatch):
    """
    Batch insert for Arduino entries.
    Generator expression — the full list is never held in memory at once.
    """
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO arduino_log (session_id, picked_up_at, duration_sec) VALUES (?,?,?)",
            ((e.session_id, e.picked_up_at, e.duration_sec) for e in batch.entries),
        )
    return {"status": "ok", "logged": len(batch.entries)}


# ── Study Tracker (Face Webcam) ───────────────────────────────────────────────

@app.post("/study/log")
def log_study_event(event: StudyEvent):
    event.validate_event()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO study_log (session_id, event_time, event_type) VALUES (?,?,?)",
            (event.session_id, event.event_time, event.event_type),
        )
    return {"status": "ok"}


@app.post("/study/batch")
def log_study_batch(batch: StudyBatch):
    """
    Batch insert for a full study-session CSV dump.
    Validates all events first, then inserts via generator.
    """
    for e in batch.events:
        e.validate_event()
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO study_log (session_id, event_time, event_type) VALUES (?,?,?)",
            ((e.session_id, e.event_time, e.event_type) for e in batch.events),
        )
    return {"status": "ok", "logged": len(batch.events)}


# ── Phone Webcam (placeholder) ────────────────────────────────────────────────

@app.post("/phone-cam/log")
def log_phone_cam_event(event: PhoneCamEvent):
    """Placeholder — update PhoneCamEvent in schemas.py once the log format is defined."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO phone_cam_log (session_id, event_time, event_type, extra_data) VALUES (?,?,?,?)",
            (event.session_id, event.event_time, event.event_type, event.extra_data),
        )
    return {"status": "ok"}


@app.post("/phone-cam/batch")
def log_phone_cam_batch(batch: PhoneCamBatch):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO phone_cam_log (session_id, event_time, event_type, extra_data) VALUES (?,?,?,?)",
            ((e.session_id, e.event_time, e.event_type, e.extra_data) for e in batch.events),
        )
    return {"status": "ok", "logged": len(batch.events)}


# ═════════════════════════════════════════════════════════════════════════════
# CALCULATION FUNCTIONS
# Each function receives an open connection and a session_id.
# ═════════════════════════════════════════════════════════════════════════════

def _calc_arduino_stats(conn, session_id: int) -> dict:
    """
    Aggregate phone-pickup stats entirely inside SQLite.
    No rows are loaded into Python memory — COUNT/SUM/AVG run on the DB side.
    ── Adjust the formula comment below when finalizing ──
    """
    row = conn.execute(
        """
        SELECT
            COUNT(*)           AS phone_pickups,
            SUM(duration_sec)  AS total_phone_sec,
            AVG(duration_sec)  AS avg_pickup_duration   -- ← adjust formula if needed
        FROM arduino_log
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()

    if not row or row["phone_pickups"] == 0:
        return {}

    return {
        "phone_pickups":       row["phone_pickups"],
        "total_phone_sec":     row["total_phone_sec"],
        "avg_pickup_duration": row["avg_pickup_duration"],
    }


def _time_to_sec(t: str) -> float:
    """Convert HH:MM:SS to total seconds. No imports needed."""
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def _calc_study_stats(conn, session_id: int) -> dict:
    """
    Stream study events one row at a time via cursor iteration.
    No fetchall() — rows are processed and discarded immediately.

    Event pairs tracked:
      SS → SE  : total session duration
      LA → LB  : look-away duration
      FL → FF  : face-lost duration
    ── Add/adjust formulas below when ready ──
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

    session_start = session_end = None
    look_away_sec   = 0.0
    face_lost_sec   = 0.0
    look_away_count = 0
    face_lost_count = 0
    _la_start = _fl_start = None
    has_rows  = False

    for row in cursor:          # ← one row at a time, no list in RAM
        has_rows = True
        t, e = row["event_time"], row["event_type"]
        ts = _time_to_sec(t)

        if   e == "SS": session_start = ts
        elif e == "SE": session_end   = ts
        elif e == "LA": _la_start = ts; look_away_count += 1
        elif e == "LB" and _la_start is not None:
            look_away_sec += ts - _la_start; _la_start = None
        elif e == "FL": _fl_start = ts; face_lost_count += 1
        elif e == "FF" and _fl_start is not None:
            face_lost_sec += ts - _fl_start; _fl_start = None

    if not has_rows:
        return {}

    session_duration_sec = (
        session_end - session_start
        if session_start is not None and session_end is not None
        else None
    )

    # ── focus_pct formula placeholder ─────────────────────────────────────
    # Fill in the formula once defined, e.g.:
    # if session_duration_sec:
    #     focus_pct = 1 - (look_away_sec + face_lost_sec) / session_duration_sec
    focus_pct = None  # ← FILL IN FORMULA

    return {
        "session_duration_sec": session_duration_sec,
        "total_look_away_sec":  look_away_sec,
        "total_face_lost_sec":  face_lost_sec,
        "look_away_count":      look_away_count,
        "face_lost_count":      face_lost_count,
        "focus_pct":            focus_pct,
    }


def _calc_phone_cam_stats(conn, session_id: int) -> dict:
    """
    Placeholder — stream phone-cam events and compute stats once the
    log format and event codes are defined.

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


def _save_stats(conn, session_id: int, stats: dict):
    """Upsert calculated stats into the session_stats cache table."""
    conn.execute(
        """
        INSERT INTO session_stats (
            session_id,
            phone_pickups, total_phone_sec, avg_pickup_duration,
            session_duration_sec, total_look_away_sec, total_face_lost_sec,
            look_away_count, face_lost_count, focus_pct,
            phone_cam_stat_1, phone_cam_stat_2,
            last_updated
        ) VALUES (
            :session_id,
            :phone_pickups, :total_phone_sec, :avg_pickup_duration,
            :session_duration_sec, :total_look_away_sec, :total_face_lost_sec,
            :look_away_count, :face_lost_count, :focus_pct,
            :phone_cam_stat_1, :phone_cam_stat_2,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(session_id) DO UPDATE SET
            phone_pickups        = excluded.phone_pickups,
            total_phone_sec      = excluded.total_phone_sec,
            avg_pickup_duration  = excluded.avg_pickup_duration,
            session_duration_sec = excluded.session_duration_sec,
            total_look_away_sec  = excluded.total_look_away_sec,
            total_face_lost_sec  = excluded.total_face_lost_sec,
            look_away_count      = excluded.look_away_count,
            face_lost_count      = excluded.face_lost_count,
            focus_pct            = excluded.focus_pct,
            phone_cam_stat_1     = excluded.phone_cam_stat_1,
            phone_cam_stat_2     = excluded.phone_cam_stat_2,
            last_updated         = CURRENT_TIMESTAMP
        """,
        {"session_id": session_id, **stats},
    )


def _dispose_logs(conn, session_id: int):
    """
    Delete all raw log rows for this session once stats are safely stored.
    Indexes on session_id make these DELETEs fast with minimal I/O.
    This keeps the DB lean and prevents raw log tables from growing unbounded.
    """
    conn.execute("DELETE FROM arduino_log   WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM study_log     WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM phone_cam_log WHERE session_id = ?", (session_id,))


# ═════════════════════════════════════════════════════════════════════════════
# STATS ROUTES — calculate, cache, dispose, return to frontend
# ═════════════════════════════════════════════════════════════════════════════

_STAT_DEFAULTS = {
    "phone_pickups": None, "total_phone_sec": None, "avg_pickup_duration": None,
    "session_duration_sec": None, "total_look_away_sec": None,
    "total_face_lost_sec": None, "look_away_count": None,
    "face_lost_count": None, "focus_pct": None,
    "phone_cam_stat_1": None, "phone_cam_stat_2": None,
}


@app.post("/stats/calculate/{session_id}", response_model=SessionStats)
def calculate_stats(session_id: int):
    """
    1. Compute stats from raw logs (streaming, no bulk RAM load).
    2. Upsert results into session_stats.
    3. Delete raw log rows — they are no longer needed.
    4. Return the stats to the caller.

    All three steps run inside a single transaction:
    if saving fails, logs are NOT deleted.
    """
    with get_conn() as conn:
        stats = {
            **_STAT_DEFAULTS,
            **_calc_arduino_stats(conn, session_id),
            **_calc_study_stats(conn, session_id),
            **_calc_phone_cam_stats(conn, session_id),
        }
        _save_stats(conn, session_id, stats)
        _dispose_logs(conn, session_id)   # ← only runs if save succeeds

    return SessionStats(session_id=session_id, **stats)


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
                f"No stats found for session {session_id}. "
                f"Call POST /stats/calculate/{session_id} first."
            ),
        )
    return SessionStats(**dict(row))


@app.get("/stats/summary/all")
def get_all_stats():
    """Return all cached sessions for the frontend dashboard."""
    with get_conn() as conn:
        # Stream rows into list — session_stats stays small since raw logs
        # are disposed after each calculation, so this table won't balloon.
        rows = conn.execute(
            "SELECT * FROM session_stats ORDER BY session_id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,              # single vCPU — never spin up more than 1
        reload=False,           # reload=True doubles memory usage
        backlog=64,             # cap queued connections; default 2048 is too high
        timeout_keep_alive=5,   # drop idle connections quickly to free sockets
        access_log=False,       # skip per-request logging to save I/O on small SSD
    )