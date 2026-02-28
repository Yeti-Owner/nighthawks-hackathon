"""
main.py
-------
Middleman FastAPI backend — runs on Vultr (Debian 12, port 8000).
Optimized for: 1 vCPU / 512MB RAM / 10GB SSD

Calculation flow (automatic — no external trigger needed):
  Arduino pickups:
    Each POST to /arduino/log stores the row then immediately runs the
    SQL aggregation (COUNT/SUM/AVG/MAX/MIN) and upserts session_stats.
    This is a single SQL query — negligible cost on the server.
    session_stats is always current after every pickup received.
    Arduino logs are NOT disposed here — they stay until a study session
    ends so that the final combined stats include all pickups.

  Study events (single):
    Each POST to /study/log stores the event. When the event type is SE
    (session_end), a full calculation runs automatically: study stats are
    computed, merged with the current arduino stats, saved to session_stats,
    and all raw logs for that session are disposed.

  Study events (batch):
    POST to /study/batch stores all events then immediately runs the full
    calculation and disposal — same result as receiving SE individually.

  Phone-cam events:
    Stored only for now. Full auto-calculation will be wired in once the
    phone-cam event codes and formulas are defined.

  Manual override:
    POST /stats/calculate/{session_id} still exists to force a full
    recalculation at any time (e.g. re-running stats, debugging).

Arduino session_id note:
  The bridge increments session_id per pickup (1, 2, 3…) — it is a
  pickup counter, not a study-session ID. Arduino stats aggregate ALL
  rows in arduino_log and are merged into the study session's slot
  in session_stats when a study session ends (SE event or batch submit).

user_id:
  Optional on all ingest endpoints. Stored in all log tables and
  session_stats. GET /stats/user/{user_id} for user-scoped queries.

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
    description="Receives Arduino/webcam logs, auto-calculates stats, disposes raw logs.",
    version="0.6.0",
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
# CALCULATION FUNCTIONS
# Defined before ingest routes so they can be called inside them.
# None load bulk data into Python — SQL aggregation or cursor streaming only.
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


def _calc_arduino_stats(conn) -> dict:
    """
    Aggregate ALL arduino_log rows in a single SQL query.
    No Python-side data load — COUNT/SUM/AVG/MAX/MIN run entirely on the DB.
    Aggregates ALL rows because the bridge uses session_id as a pickup
    counter (1, 2, 3…), not a study-session ID.

    Stats produced:
      phone_pickups  — total times phone was picked up
      total_held_sec — total seconds phone was held
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
    Returns None on malformed input — caller skips the row so a bad
    timestamp never crashes the calculation or strands raw logs.
    """
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def _calc_study_stats(conn, session_id: int) -> dict:
    """
    Stream face-cam events one row at a time via cursor iteration.
    No fetchall — rows are processed and discarded as the cursor moves.

    Event pairs tracked:
      SS → SE  : session wall time  → session_duration_sec
      LA → LB  : look-away interval → total, count, avg, longest, first
      FL → FF  : face-lost interval → total, count

    Derived stats:
      focus_time_sec = session_duration - total_look_away - total_face_lost
      focus_pct      = (focus_time_sec / session_duration_sec) * 100
                       clamped to 0 to guard against clock drift or overlap
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

    for row in cursor:
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
            if first_look_away_sec is None:
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
        look_away_sec / look_away_count if look_away_count > 0 else None
    )

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
    processes the image content.

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
    Look up user_id from study_log for this session.
    Falls back to arduino_log if no study events exist yet.
    Returns None if user_id was never provided.
    """
    row = conn.execute(
        "SELECT user_id FROM study_log WHERE session_id = ? LIMIT 1",
        (session_id,),
    ).fetchone()
    if row and row["user_id"] is not None:
        return row["user_id"]
    # Fallback: check arduino_log (user_id may have been passed by bridge)
    row = conn.execute(
        "SELECT user_id FROM arduino_log LIMIT 1"
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
    Delete raw log rows after stats are safely saved.
    Runs inside the same transaction as _save_stats — if the save fails,
    the transaction rolls back and logs are preserved.

    Arduino: ALL rows cleared regardless of session_id (per-pickup counter).
    Study / phone-cam: filtered by session_id.

    Note: wal_checkpoint is intentionally NOT called here because this
    function runs before conn.commit(). The checkpoint is called by the
    callers after the with-block exits and the transaction is committed.
    """
    conn.execute("DELETE FROM arduino_log")
    conn.execute("DELETE FROM study_log     WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM phone_cam_log WHERE session_id = ?", (session_id,))


def _run_full_session_calc(conn, session_id: int, user_id):
    """
    Run the complete calculation for a study session:
    arduino stats + study stats + phone-cam stats → save → dispose logs.
    Called automatically when a study session ends (SE event or batch submit).
    Returns the stats dict. Checkpoint is handled by the caller after commit.
    """
    stats = {
        **_STAT_DEFAULTS,
        **_calc_arduino_stats(conn),
        **_calc_study_stats(conn, session_id),
        **_calc_phone_cam_stats(conn, session_id),
    }
    _save_stats(conn, session_id, user_id, stats)
    _dispose_logs(conn, session_id)
    return stats


# ═════════════════════════════════════════════════════════════════════════════
# INGEST ROUTES — receive data from hardware / webcams
# Each route stores data and triggers calculation automatically.
# ═════════════════════════════════════════════════════════════════════════════

# ── Arduino ──────────────────────────────────────────────────────────────────

@app.post("/arduino/log")
def log_arduino(entry: ArduinoEntry):
    """
    Receive a single pickup event and store it.
    Immediately runs the SQL aggregation and returns the running tally
    in the response so the caller has live stats without a second request.

    Does NOT write to session_stats here. Partial records with all study
    columns forced to None would create orphan rows and unnecessary write
    amplification on every pickup. session_stats is only written when a
    complete session ends via study/log (SE) or study/batch.
    Arduino logs remain in arduino_log until a study session disposes them.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO arduino_log (session_id, user_id, picked_up_at, duration_sec) "
            "VALUES (?,?,?,?)",
            (entry.session_id, entry.user_id, entry.picked_up_at, entry.duration_sec),
        )
        live_stats = _calc_arduino_stats(conn)

    return {"status": "ok", "running_tally": live_stats}


# ── Study Tracker (Face Webcam) ───────────────────────────────────────────────

@app.post("/study/log")
def log_study_event(event: StudyEvent):
    """
    Receive a single face-cam event.
    If the event is SE (session_end), automatically runs the full
    calculation (arduino + study + phone-cam) and disposes all logs.
    All other events are stored and awaited — no calculation mid-session.
    """
    event.validate_event()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO study_log (session_id, user_id, event_time, event_type) "
            "VALUES (?,?,?,?)",
            (event.session_id, event.user_id, event.event_time, event.event_type),
        )
        if event.event_type == "SE":
            user_id = event.user_id or _get_user_id_for_session(conn, event.session_id)
            _run_full_session_calc(conn, event.session_id, user_id)
    # Checkpoint runs here — after commit, so WAL pages are now eligible
    if event.event_type == "SE":
        with get_conn() as conn:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        return {"status": "ok", "calculated": True, "session_id": event.session_id}

    return {"status": "ok", "calculated": False}


@app.post("/study/batch")
def log_study_batch(batch: StudyBatch):
    """
    Receive a full study-session CSV dump.
    Validates all events, inserts via generator (no list in RAM), then
    immediately runs the full calculation and disposes logs.
    A batch always represents a complete session so calculation is always safe.
    """
    if not batch.events:
        return {"status": "ok", "logged": 0, "calculated": False}

    for e in batch.events:
        e.validate_event()

    session_id = batch.events[0].session_id
    user_id    = batch.events[0].user_id

    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO study_log (session_id, user_id, event_time, event_type) "
            "VALUES (?,?,?,?)",
            ((e.session_id, e.user_id, e.event_time, e.event_type) for e in batch.events),
        )
        resolved_user_id = user_id or _get_user_id_for_session(conn, session_id)
        _run_full_session_calc(conn, session_id, resolved_user_id)

    # Checkpoint after commit — WAL pages from the transaction are now committed
    with get_conn() as conn:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")

    return {"status": "ok", "logged": len(batch.events), "calculated": True}


# ── Phone Webcam (placeholder) ────────────────────────────────────────────────

@app.post("/phone-cam/log")
def log_phone_cam_event(event: PhoneCamEvent):
    """
    Placeholder — tracks when the phone screen lights up.
    Stored only for now. Auto-calculation will be added once event
    codes and formulas are defined in _calc_phone_cam_stats.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO phone_cam_log (session_id, user_id, event_time, event_type, extra_data) "
            "VALUES (?,?,?,?,?)",
            (event.session_id, event.user_id, event.event_time, event.event_type, event.extra_data),
        )
    return {"status": "ok"}


@app.post("/phone-cam/batch")
def log_phone_cam_batch(batch: PhoneCamBatch):
    """Placeholder batch insert. Calculation wired in once phone-cam format is defined."""
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO phone_cam_log (session_id, user_id, event_time, event_type, extra_data) "
            "VALUES (?,?,?,?,?)",
            ((e.session_id, e.user_id, e.event_time, e.event_type, e.extra_data) for e in batch.events),
        )
    return {"status": "ok", "logged": len(batch.events)}


# ═════════════════════════════════════════════════════════════════════════════
# STATS ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/stats/calculate/{session_id}", response_model=SessionStats)
def calculate_stats(session_id: int):
    """
    Manual override — force a full recalculation for a session.
    Not required for normal operation (auto-calculation handles this),
    but useful for re-running stats or debugging.
    """
    with get_conn() as conn:
        user_id = _get_user_id_for_session(conn, session_id)
        stats   = _run_full_session_calc(conn, session_id, user_id)
    with get_conn() as conn:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
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
            detail=f"No stats for session {session_id}. Data may not have arrived yet.",
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
    Return all cached sessions for a specific user.
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
    Return a specific session's stats scoped to a user.
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