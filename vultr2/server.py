"""
CSV Ingestion Server — receives notifications, session_log, and pickedup CSVs,
sanitizes them, stores in SQLite, and serves data back as JSON.

Run with:  uv run python server.py
"""

import csv
import io
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
import uvicorn

DB_PATH = "data.db"

VALID_TABLES = {"notifications", "session_log", "pickedup"}

# ── Database setup ───────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            filename    TEXT,
            has_notification TEXT,
            urgency     TEXT,
            source      TEXT,
            sender      TEXT,
            summary     TEXT,
            error       TEXT
        );
        CREATE TABLE IF NOT EXISTS session_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT,
            time        TEXT,
            event       TEXT
        );
        CREATE TABLE IF NOT EXISTS pickedup (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            iteration   INTEGER,
            time_held   REAL
        );
    """)
    conn.close()

# ── CSV parsing helpers ──────────────────────────────────────────────────────

def parse_notifications(raw: str) -> int:
    reader = csv.reader(io.StringIO(raw))
    header = None
    rows = []
    for line in reader:
        cells = [c.strip() for c in line]
        if not cells or all(c == "" for c in cells):
            continue
        if header is None:
            header = cells
            continue
        # Pad short rows with empty strings
        while len(cells) < 8:
            cells.append("")
        rows.append(tuple(cells[:8]))

    conn = get_db()
    conn.executemany(
        "INSERT INTO notifications (timestamp,filename,has_notification,urgency,source,sender,summary,error) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def parse_session_log(raw: str) -> int:
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        # Skip the header row
        if parts[0] == "S" and parts[1] == "T" and parts[2] == "E":
            continue
        rows.append((parts[0], parts[1], parts[2]))

    conn = get_db()
    conn.executemany(
        "INSERT INTO session_log (session_id, time, event) VALUES (?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def parse_pickedup(raw: str) -> int:
    reader = csv.reader(io.StringIO(raw))
    header = None
    rows = []
    for line in reader:
        cells = [c.strip() for c in line]
        if not cells or all(c == "" for c in cells):
            continue
        if header is None:
            header = cells
            continue
        try:
            rows.append((int(cells[0]), float(cells[1])))
        except (ValueError, IndexError):
            continue

    conn = get_db()
    conn.executemany(
        "INSERT INTO pickedup (iteration, time_held) VALUES (?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)

# ── FastAPI app ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="CSV Ingestion Server", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(
    notifications: UploadFile | None = File(None),
    session_log: UploadFile | None = File(None),
    pickedup: UploadFile | None = File(None),
):
    results = {}
    if notifications:
        results["notifications_rows"] = parse_notifications(
            (await notifications.read()).decode("utf-8-sig"))
    if session_log:
        results["session_log_rows"] = parse_session_log(
            (await session_log.read()).decode("utf-8-sig"))
    if pickedup:
        results["pickedup_rows"] = parse_pickedup(
            (await pickedup.read()).decode("utf-8-sig"))
    if not results:
        raise HTTPException(400, "No CSV files provided")
    return results


@app.get("/data/{table}")
def get_data(table: str):
    if table not in VALID_TABLES:
        raise HTTPException(status_code=400, detail=f"Invalid table. Choose from: {VALID_TABLES}")
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
