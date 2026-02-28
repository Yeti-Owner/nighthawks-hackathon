"""
Manager — FastAPI backend for the Aurelius setup flow.

Endpoints:
    POST /start/{step}         — Launch a setup step
    GET  /status/{step}        — Poll for completion
    POST /stop/{step}          — Kill a running step

Start with:
    python manager.py
"""

import asyncio
import sys

import uvicorn
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# step name → relative script path
SCRIPTS = {
    "camera_select":  "cam_select/camera_select.py",
    "configlandmarks": "distraction_tracker/configlandmarks.py",
    "study_tracker":   "distraction_tracker/study_tracker.py",
    "noti_watcher":    "notifications/noti_watcher.py",
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

class UserRequest(BaseModel):
    user_id: str

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/user")
async def set_user(req: UserRequest):
    """Save the authenticated Auth0 user ID to user.txt"""
    with open(BASE_DIR / "user.txt", "w") as f:
        f.write(req.user_id)
    return {"status": "ok", "user_id": req.user_id}

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


if __name__ == "__main__":
    uvicorn.run("manager:app", host="0.0.0.0", port=8000)
