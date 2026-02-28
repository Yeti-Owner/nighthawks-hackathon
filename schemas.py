"""
schemas.py
----------
Pydantic models for all data sources.
Batch sizes are capped to prevent oversized payloads from
spiking memory on the 512MB Vultr instance.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


# ── Batch size cap ─────────────────────────────────────────────────────────────
# A typical study session won't come close to this. It's a safety ceiling
# to prevent a malformed or runaway sender from blowing up RAM.
MAX_BATCH = 500


# ── Arduino Log ───────────────────────────────────────────────────────────────

class ArduinoEntry(BaseModel):
    session_id:   int
    picked_up_at: str   = Field(..., description="HH:MM:SS EST — time phone was picked up")
    duration_sec: float = Field(..., ge=0, description="Seconds the phone was held")


class ArduinoBatch(BaseModel):
    entries: List[ArduinoEntry] = Field(..., max_length=MAX_BATCH)


# ── Study Tracker Log (Face Webcam) ──────────────────────────────────────────

VALID_FACE_EVENTS = frozenset({"SS", "SE", "FL", "FF", "LA", "LB"})

class StudyEvent(BaseModel):
    session_id: int
    event_time: str = Field(..., description="HH:MM:SS EST")
    event_type: str = Field(..., description="SS | SE | FL | FF | LA | LB")

    def validate_event(self):
        if self.event_type not in VALID_FACE_EVENTS:
            raise ValueError(
                f"Unknown event_type '{self.event_type}'. Valid: {sorted(VALID_FACE_EVENTS)}"
            )


class StudyBatch(BaseModel):
    events: List[StudyEvent] = Field(..., max_length=MAX_BATCH)


# ── Phone Webcam Log (placeholder) ───────────────────────────────────────────

class PhoneCamEvent(BaseModel):
    """
    Placeholder — define event_type codes once the phone-cam log format is set.
    """
    session_id: int
    event_time: str            = Field(..., description="HH:MM:SS EST")
    event_type: str            = Field(..., description="TBD — fill in phone-cam event codes")
    extra_data: Optional[str]  = Field(None, description="Optional JSON string for extra fields")


class PhoneCamBatch(BaseModel):
    events: List[PhoneCamEvent] = Field(..., max_length=MAX_BATCH)


# ── Stats Response ────────────────────────────────────────────────────────────

class SessionStats(BaseModel):
    """
    Calculated values returned to the frontend.
    All slots are present — formulas are filled in main.py.
    """
    session_id: int

    # Arduino-derived
    phone_pickups:        Optional[int]   = None
    total_phone_sec:      Optional[float] = None
    avg_pickup_duration:  Optional[float] = None

    # Face-cam-derived
    session_duration_sec: Optional[float] = None
    total_look_away_sec:  Optional[float] = None
    total_face_lost_sec:  Optional[float] = None
    look_away_count:      Optional[int]   = None
    face_lost_count:      Optional[int]   = None
    focus_pct:            Optional[float] = None

    # Phone-cam-derived (placeholder)
    phone_cam_stat_1:     Optional[float] = None
    phone_cam_stat_2:     Optional[float] = None