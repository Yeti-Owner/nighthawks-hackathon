"""
Manager Script — FastAPI backend for the Nighthawks Hackathon project.

Provides endpoints for a React/Next.js frontend to:
  - List the known Python scripts
  - Run one (or more) scripts concurrently as subprocesses
  - Check on the status / output of any running script
  - Stop a running script

Start with:
    python -m uvicorn manager:app --reload --port 8000
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# Hard-coded registry of scripts that the frontend is allowed to run.
# Keys are short identifiers sent by the frontend; values are relative paths.
SCRIPTS = {
    "camera_select":  "cam_select/camera_select.py",
    "configlandmarks": "distraction_tracker/configlandmarks.py",
    "study_tracker":   "distraction_tracker/study_tracker.py",
    "noti_watcher":    "notifications/noti_watcher.py",
}

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Nighthawks Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory run tracking
# ---------------------------------------------------------------------------

# Each entry: {
#   "run_id": str,
#   "script": str,           # key from SCRIPTS
#   "status": "running" | "completed" | "error" | "stopped",
#   "exit_code": int | None,
#   "stdout": str,
#   "stderr": str,
#   "process": asyncio.subprocess.Process,
# }
active_runs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    script: str  # one of the SCRIPTS keys


class RunResponse(BaseModel):
    run_id: str
    script: str
    message: str


class StatusResponse(BaseModel):
    run_id: str
    script: str
    status: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


class StopResponse(BaseModel):
    run_id: str
    message: str


class ScriptInfo(BaseModel):
    key: str
    path: str


# ---------------------------------------------------------------------------
# Background task: wait for process to finish and capture output
# ---------------------------------------------------------------------------

async def _watch_process(run_id: str) -> None:
    """Wait for the subprocess to exit and record its output."""
    entry = active_runs.get(run_id)
    if entry is None:
        return

    proc: asyncio.subprocess.Process = entry["process"]
    stdout_bytes, stderr_bytes = await proc.communicate()

    # Only update if the process wasn't already marked as stopped
    if entry["status"] == "running":
        entry["status"] = "completed" if proc.returncode == 0 else "error"

    entry["exit_code"] = proc.returncode
    entry["stdout"] = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
    entry["stderr"] = stderr_bytes.decode(errors="replace") if stderr_bytes else ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/scripts", response_model=list[ScriptInfo])
async def list_scripts():
    """Return the list of scripts that can be run."""
    return [
        ScriptInfo(key=key, path=path)
        for key, path in SCRIPTS.items()
    ]


@app.post("/run", response_model=RunResponse)
async def run_script(req: RunRequest):
    """
    Launch a Python script as a subprocess.

    The script keeps running until it finishes on its own or is explicitly
    stopped via /stop.  Multiple scripts (or the same script more than once)
    can run concurrently.
    """
    if req.script not in SCRIPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown script '{req.script}'. "
                   f"Available: {list(SCRIPTS.keys())}",
        )

    script_path = BASE_DIR / SCRIPTS[req.script]
    if not script_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Script file not found: {script_path}",
        )

    run_id = uuid.uuid4().hex[:12]

    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(script_path.parent),   # run inside the script's own folder
    )

    active_runs[run_id] = {
        "run_id": run_id,
        "script": req.script,
        "status": "running",
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "process": proc,
    }

    # Fire-and-forget: watch the process in the background
    asyncio.create_task(_watch_process(run_id))

    return RunResponse(
        run_id=run_id,
        script=req.script,
        message=f"Started '{req.script}' (pid {proc.pid})",
    )


@app.get("/status/{run_id}", response_model=StatusResponse)
async def get_status(run_id: str):
    """Check the current status of a run."""
    entry = active_runs.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Run ID not found")

    return StatusResponse(
        run_id=entry["run_id"],
        script=entry["script"],
        status=entry["status"],
        exit_code=entry["exit_code"],
        stdout=entry["stdout"],
        stderr=entry["stderr"],
    )


@app.post("/stop/{run_id}", response_model=StopResponse)
async def stop_script(run_id: str):
    """Kill a running subprocess."""
    entry = active_runs.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Run ID not found")

    if entry["status"] != "running":
        return StopResponse(
            run_id=run_id,
            message=f"Script already {entry['status']}",
        )

    proc: asyncio.subprocess.Process = entry["process"]
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()

    entry["status"] = "stopped"
    entry["exit_code"] = proc.returncode

    return StopResponse(
        run_id=run_id,
        message=f"Script '{entry['script']}' stopped",
    )


@app.get("/active", response_model=list[StatusResponse])
async def list_active():
    """Return all runs that are currently in 'running' state."""
    return [
        StatusResponse(
            run_id=e["run_id"],
            script=e["script"],
            status=e["status"],
            exit_code=e["exit_code"],
            stdout=e["stdout"],
            stderr=e["stderr"],
        )
        for e in active_runs.values()
        if e["status"] == "running"
    ]
