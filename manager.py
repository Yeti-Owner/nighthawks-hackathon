"""
Manager — FastAPI backend for the Aurelius setup flow.

Endpoints:
    POST /start/{step}         — Launch a setup step
    GET  /status/{step}        — Poll for completion
    POST /stop/{step}          — Kill a running step
    POST /sync/send            — Send CSVs to Vultr server
    GET  /sync/send/status     — Poll send status
    POST /sync/receive         — Fetch data from Vultr server
    GET  /sync/data/{table}    — Read saved server data
    POST /pipeline/end         — End session: stop → fix → parse → send → receive
    GET  /pipeline/end/status  — Poll pipeline progress

Start with:
    python manager.py
"""

import asyncio
import json
import subprocess
import sys

import httpx
import uvicorn
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

VULTR_BASE = "http://45.32.173.69:8000"
VULTR_TABLES = ["notifications", "session_log", "pickedup"]

# step name → relative script path
SCRIPTS = {
    "camera_select":  "cam_select/camera_select.py",
    "configlandmarks": "distraction_tracker/configlandmarks.py",
    "study_tracker":   "distraction_tracker/study_tracker.py",
    "noti_watcher":    "notifications/noti_watcher.py",
    "arduino_reader":  "arduino/reader.py",
}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Aurelius Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class StepState:
    """Tracks a single running subprocess."""
    __slots__ = ("process", "status", "exit_code")

    def __init__(self, process: asyncio.subprocess.Process):
        self.process = process
        self.status = "running"
        self.exit_code: int | None = None

steps: dict[str, StepState] = {}


async def _wait_for(step: str) -> None:
    """Background task — waits for the subprocess to finish."""
    state = steps.get(step)
    if state is None:
        return
    await state.process.wait()
    if state.status == "running":                       # not already stopped
        state.exit_code = state.process.returncode
        state.status = "completed" if state.exit_code == 0 else "error"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class StepResponse(BaseModel):
    step: str
    status: str
    exit_code: int | None = None

class SyncReceiveResponse(BaseModel):
    status: str
    tables: dict[str, str]   # table_name → "ok" | error message

# ---------------------------------------------------------------------------
# Endpoints — Setup Steps
# ---------------------------------------------------------------------------

@app.post("/start/{step}", response_model=StepResponse)
async def start_step(step: str, headless: bool = Query(False)):
    """Launch a setup step as a subprocess."""
    if step not in SCRIPTS:
        raise HTTPException(400, f"Unknown step '{step}'. Available: {list(SCRIPTS)}")

    # Don't start if already running
    if step in steps and steps[step].status == "running":
        return StepResponse(step=step, status="running")

    script = BASE_DIR / SCRIPTS[step]
    if not script.is_file():
        raise HTTPException(404, f"Script not found: {script}")

    cmd = [sys.executable, str(script)]
    if step == "study_tracker" and headless:
        cmd.append("--headless")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(script.parent),
    )

    steps[step] = StepState(proc)
    asyncio.create_task(_wait_for(step))

    return StepResponse(step=step, status="running")


@app.get("/status/{step}", response_model=StepResponse)
async def get_status(step: str):
    """Poll the current status of a step."""
    if step not in SCRIPTS:
        raise HTTPException(400, f"Unknown step '{step}'.")

    state = steps.get(step)
    if state is None:
        return StepResponse(step=step, status="idle")

    return StepResponse(step=step, status=state.status, exit_code=state.exit_code)


@app.post("/stop/{step}", response_model=StepResponse)
async def stop_step(step: str):
    """Kill a running step."""
    state = steps.get(step)
    if state is None or state.status != "running":
        status = state.status if state else "idle"
        return StepResponse(step=step, status=status)

    state.process.terminate()
    try:
        await asyncio.wait_for(state.process.wait(), timeout=5)
    except asyncio.TimeoutError:
        state.process.kill()

    state.status = "stopped"
    state.exit_code = state.process.returncode
    return StepResponse(step=step, status="stopped", exit_code=state.exit_code)


# ---------------------------------------------------------------------------
# Endpoints — Data Sync
# ---------------------------------------------------------------------------

@app.post("/sync/send", response_model=StepResponse)
async def sync_send():
    """Run send_csv.py to upload local CSVs to the Vultr server."""
    step = "_sync_send"

    # Don't start if already running
    if step in steps and steps[step].status == "running":
        return StepResponse(step=step, status="running")

    script = BASE_DIR / "server" / "send_csv.py"
    if not script.is_file():
        raise HTTPException(404, f"Script not found: {script}")

    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script),
        cwd=str(BASE_DIR),
    )

    steps[step] = StepState(proc)
    asyncio.create_task(_wait_for(step))

    return StepResponse(step=step, status="running")


@app.get("/sync/send/status", response_model=StepResponse)
async def sync_send_status():
    """Poll the send_csv subprocess status."""
    step = "_sync_send"
    state = steps.get(step)
    if state is None:
        return StepResponse(step=step, status="idle")
    return StepResponse(step=step, status=state.status, exit_code=state.exit_code)


@app.post("/sync/receive", response_model=SyncReceiveResponse)
async def sync_receive():
    """Fetch data from the Vultr server and save to data/ directory."""
    DATA_DIR.mkdir(exist_ok=True)
    results: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in VULTR_TABLES:
            url = f"{VULTR_BASE}/data/{table}"
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                out_path = DATA_DIR / f"{table}.json"
                out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                results[table] = "ok"
            except httpx.ConnectError:
                results[table] = f"Connection failed — is the Vultr server running?"
            except httpx.HTTPStatusError as e:
                results[table] = f"HTTP {e.response.status_code}"
            except Exception as e:
                results[table] = str(e)

    all_ok = all(v == "ok" for v in results.values())
    return SyncReceiveResponse(
        status="ok" if all_ok else "partial",
        tables=results,
    )


@app.get("/sync/data/{table}")
async def sync_data(table: str):
    """Return the contents of a previously-received data file."""
    if table not in VULTR_TABLES:
        raise HTTPException(400, f"Unknown table '{table}'. Available: {VULTR_TABLES}")

    file_path = DATA_DIR / f"{table}.json"
    if not file_path.is_file():
        raise HTTPException(404, f"No data for '{table}'. Run POST /sync/receive first.")

    return json.loads(file_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Endpoints — End-Session Pipeline
# ---------------------------------------------------------------------------

class PipelineState:
    """Tracks the end-session pipeline."""
    def __init__(self):
        self.status = "running"  # running | completed | error
        self.current_step = "stopping"
        self.error: str | None = None

pipeline_state: PipelineState | None = None


def _run_script_sync(script_path: Path, args: list[str] | None = None, cwd: Path | None = None):
    """Run a Python script synchronously, return (success, output)."""
    cmd = [sys.executable, str(script_path)] + (args or [])
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or script_path.parent),
            capture_output=True,
            text=True,
            timeout=120,
        )
        print(f"  [pipeline] {script_path.name} exit={result.returncode}")
        if result.stdout:
            print(f"  [stdout] {result.stdout[:500]}")
        if result.stderr:
            print(f"  [stderr] {result.stderr[:500]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  [pipeline] {script_path.name} TIMED OUT")
        return False
    except Exception as e:
        print(f"  [pipeline] {script_path.name} ERROR: {e}")
        return False


async def _stop_step_quiet(step: str):
    """Stop a step if it's running, ignore if it's not."""
    state = steps.get(step)
    if state and state.status == "running":
        state.process.terminate()
        try:
            await asyncio.wait_for(state.process.wait(), timeout=5)
        except asyncio.TimeoutError:
            state.process.kill()
        state.status = "stopped"
        state.exit_code = state.process.returncode


async def _receive_data() -> dict[str, str]:
    """Fetch all tables from Vultr and save to data/. Returns per-table results."""
    DATA_DIR.mkdir(exist_ok=True)
    results: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in VULTR_TABLES:
            url = f"{VULTR_BASE}/data/{table}"
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                out_path = DATA_DIR / f"{table}.json"
                out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                results[table] = "ok"
            except Exception as e:
                results[table] = str(e)
    return results


async def _run_end_pipeline():
    """The full end-session pipeline. Runs as a background task."""
    global pipeline_state
    ps = pipeline_state
    if ps is None:
        return

    try:
        # 1. Stop all running trackers
        ps.current_step = "stopping trackers"
        print("[pipeline] Step 1: Stopping trackers...")
        for s in ["study_tracker", "noti_watcher", "arduino_reader"]:
            await _stop_step_quiet(s)
        await asyncio.sleep(1)  # let processes settle

        # 2. Run fix_pic on captures
        ps.current_step = "fixing images"
        print("[pipeline] Step 2: Running fix_pic...")
        fix_pic = BASE_DIR / "notifications" / "fix_pic.py"
        captures = BASE_DIR / "notifications" / "captures"
        captures.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_script_sync, fix_pic, [str(captures)], BASE_DIR)

        # 3. Run parse_noti in batch mode
        ps.current_step = "parsing notifications"
        print("[pipeline] Step 3: Running parse_noti --batch...")
        parse_noti = BASE_DIR / "notifications" / "parse_noti.py"
        await loop.run_in_executor(None, _run_script_sync, parse_noti, ["--batch"], BASE_DIR)

        # 4. Send CSVs to server
        ps.current_step = "uploading CSVs"
        print("[pipeline] Step 4: Running send_csv...")
        send_csv = BASE_DIR / "server" / "send_csv.py"
        await loop.run_in_executor(None, _run_script_sync, send_csv, None, BASE_DIR)

        # 5. Brief pause
        ps.current_step = "waiting for server"
        print("[pipeline] Step 5: Waiting 2s for server to process...")
        await asyncio.sleep(2)

        # 6. Receive data from server
        ps.current_step = "downloading data"
        print("[pipeline] Step 6: Receiving data from Vultr...")
        results = await _receive_data()
        all_ok = all(v == "ok" for v in results.values())
        print(f"[pipeline] Receive results: {results}")

        ps.status = "completed" if all_ok else "completed"
        ps.current_step = "done"
        print("[pipeline] Pipeline finished successfully.")

    except Exception as e:
        ps.status = "error"
        ps.error = str(e)
        ps.current_step = "failed"
        print(f"[pipeline] Pipeline error: {e}")


@app.post("/pipeline/end")
async def pipeline_end():
    """Kick off the end-session pipeline (stop → fix → parse → send → receive)."""
    global pipeline_state

    # Don't start if already running
    if pipeline_state and pipeline_state.status == "running":
        return {"status": "running", "step": pipeline_state.current_step}

    pipeline_state = PipelineState()
    asyncio.create_task(_run_end_pipeline())
    return {"status": "running", "step": "stopping"}


@app.get("/pipeline/end/status")
async def pipeline_end_status():
    """Poll the end-session pipeline status."""
    if pipeline_state is None:
        return {"status": "idle", "step": None, "error": None}
    return {
        "status": pipeline_state.status,
        "step": pipeline_state.current_step,
        "error": pipeline_state.error,
    }


if __name__ == "__main__":
    uvicorn.run("manager:app", host="0.0.0.0", port=8000)
