"""
main.py
-------
Middleman FastAPI backend — runs on Vultr (Debian 12, port 8000).
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD

Memory strategy:
  - Arduino stats computed entirely in SQL (no Python-side data load)
  - Study/phone-cam stats stream rows one at a time via cursor iteration
  - Batch inserts use generator expressions (no intermediate list in RAM)
  - Raw logs deleted immediately after stats are safely saved
  - Uvicorn locked to 1 worker with backlog and keep-alive caps

Arduino / bridge flow:
  1. serial_bridge.py runs on the PC connected to the Arduino
  2. It monitors Serial output live, collecting pickups in memory
  3. On CTRL+C, it POSTs each pickup individually to POST /arduino/log
  4. Each POST has: session_id (pickup counter), picked_up_at, duration_sec
  5. Stats are calculated on demand via POST /stats/calculate/{session_id}
  6. Raw logs are disposed after stats are written

  Note on session_id from Arduino:
  The bridge increments session_id per pickup (1 for pickup 1, 2 for pickup 2…).
  This means Arduino session_id acts as a pickup ID, not a study-session ID.
  _calc_arduino_stats therefore aggregates ALL rows in arduino_log, not just
  those matching the requested session_id. Dispose clears all arduino_log rows.

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
    version="0.4.0",
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
    Called once per pickup after the user presses CTRL+C on the bridge.

    Payload: { session_id, picked_up_at, duration_sec }
    session_id increments per pickup in the bridge — see module note above.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO arduino_log (session_id, picked_up_at, duration_sec) VALUES (?,?,?)",
            (entry.session_id, entry.picked_up_at, entry.duration_sec),
        )
    return {"status": "ok"}


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
    """Batch insert for a full study-session CSV dump."""
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
    """Placeholder — update PhoneCamEvent in schemas.py once log format is defined."""
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
# ═════════════════════════════════════════════════════════════════════════════

def _calc_arduino_stats(conn, session_id: int) -> dict:
    """
    Aggregate ALL arduino_log rows in SQL — no Python-side data load.

    Why ALL rows and not filtered by session_id:
      The bridge uses session_id as a per-pickup counter (1, 2, 3…), so each
      pickup has a unique session_id. Filtering by the study session_id would
      only ever return 0 or 1 row. Instead, we aggregate everything currently
      in the table (all pickups from the current Arduino run).

    Stats produced:
      phone_pickups  — COUNT of rows
      total_held_sec — SUM of duration_sec
      avg_held_sec   — AVG of duration_sec  ← adjust formula if needed
    """
    row = conn.execute(
        """
        SELECT
            COUNT(*)           AS phone_pickups,
            SUM(duration_sec)  AS total_held_sec,
            AVG(duration_sec)  AS avg_held_sec    -- ← adjust formula if needed
        FROM arduino_log
        """
    ).fetchone()

    if not row or row["phone_pickups"] == 0:
        return {}

    return {
        "phone_pickups":  row["phone_pickups"],
        "total_held_sec": row["total_held_sec"],
        "avg_held_sec":   row["avg_held_sec"],
    }


def _time_to_sec(t: str):
    """
    Convert HH:MM:SS to total seconds.
    Returns None on malformed input so the caller can skip the row
    instead of crashing the entire calculation and stranding raw logs.
    """
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def _calc_study_stats(conn, session_id: int) -> dict:
    """
    Stream study events one row at a time — no fetchall(), no bulk RAM load.

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
    has_rows = False

    for row in cursor:
        has_rows = True
        t, e = row["event_time"], row["event_type"]
        ts = _time_to_sec(t)

        if ts is None:
            continue   # malformed timestamp — skip row, don't crash the session

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
    # e.g.: focus_pct = 1 - (look_away_sec + face_lost_sec) / session_duration_sec
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
    Placeholder — stream phone-cam events once the log format is defined.

    Pattern to follow:
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
    """Upsert calculated stats into session_stats cache."""
    conn.execute(
        """
        INSERT INTO session_stats (
            session_id,
            phone_pickups, total_held_sec, avg_held_sec,
            session_duration_sec, total_look_away_sec, total_face_lost_sec,
            look_away_count, face_lost_count, focus_pct,
            phone_cam_stat_1, phone_cam_stat_2,
            last_updated
        ) VALUES (
            :session_id,
            :phone_pickups, :total_held_sec, :avg_held_sec,
            :session_duration_sec, :total_look_away_sec, :total_face_lost_sec,
            :look_away_count, :face_lost_count, :focus_pct,
            :phone_cam_stat_1, :phone_cam_stat_2,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(session_id) DO UPDATE SET
            phone_pickups        = excluded.phone_pickups,
            total_held_sec       = excluded.total_held_sec,
            avg_held_sec         = excluded.avg_held_sec,
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
    Delete raw log rows after stats are safely stored.
    Arduino logs: ALL rows cleared (session_id is per-pickup, not per-study-session).
    Study / phone-cam logs: filtered by session_id as normal.

    wal_checkpoint(PASSIVE) runs after deletion to merge the WAL back into
    the main DB file. Without this, the WAL grows silently after every
    disposal and never shrinks until the process restarts — a problem on
    a 10GB SSD.
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
    "session_duration_sec": None, "total_look_away_sec": None,
    "total_face_lost_sec": None, "look_away_count": None,
    "face_lost_count": None, "focus_pct": None,
    "phone_cam_stat_1": None, "phone_cam_stat_2": None,
}


@app.post("/stats/calculate/{session_id}", response_model=SessionStats)
def calculate_stats(session_id: int):
    """
    1. Compute stats from raw logs (streaming, minimal RAM).
    2. Upsert into session_stats.
    3. Delete raw logs — all in one transaction.
       If the save fails, logs are NOT deleted.
    4. Return stats to the caller.
    """
    with get_conn() as conn:
        stats = {
            **_STAT_DEFAULTS,
            **_calc_arduino_stats(conn, session_id),
            **_calc_study_stats(conn, session_id),
            **_calc_phone_cam_stats(conn, session_id),
        }
        _save_stats(conn, session_id, stats)
        _dispose_logs(conn, session_id)

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
        workers=1,
        reload=False,
        backlog=64,
        timeout_keep_alive=5,
        access_log=False,
    )