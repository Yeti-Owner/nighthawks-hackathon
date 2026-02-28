"""
schemas.py
----------
Pydantic models for all data sources.
Batch sizes are capped to prevent oversized payloads from
spiking memory on the 512MB Vultr instance.

Arduino / bridge note:
  serial_bridge.py sends one POST per pickup to /arduino/log.
  Payload per request:
    session_id   : int  — increments per pickup (1, 2, 3…); acts as pickup ID
    picked_up_at : str  — ISO datetime from the PC (e.g. "2025-01-15T14:32:00")
    duration_sec : float — seconds the phone was held
"""

from pydantic import BaseModel, Field
from typing import Optional, List


MAX_BATCH = 500   # safety ceiling on batch payloads


# ── Arduino ───────────────────────────────────────────────────────────────────

class ArduinoEntry(BaseModel):
    """
    One pickup event — matches the payload sent by serial_bridge.py.
    session_id here is a per-pickup counter from the bridge, not a
    study-session ID. Stats aggregate all arduino_log rows together.
    """
    session_id:   int   = Field(..., description="Per-pickup counter from bridge (1, 2, 3…)")
    picked_up_at: str   = Field(..., description="ISO datetime from PC — e.g. 2025-01-15T14:32:00")
    duration_sec: float = Field(..., ge=0, description="Seconds the phone was held")


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
    """Placeholder — define event_type codes once the phone-cam log format is set."""
    session_id: int
    event_time: str           = Field(..., description="HH:MM:SS EST")
    event_type: str           = Field(..., description="TBD — fill in phone-cam event codes")
    extra_data: Optional[str] = Field(None, description="Optional JSON string for extra fields")


class PhoneCamBatch(BaseModel):
    events: List[PhoneCamEvent] = Field(..., max_length=MAX_BATCH)


# ── Stats Response ────────────────────────────────────────────────────────────

class SessionStats(BaseModel):
    """
    Calculated values returned to the frontend.
    Arduino stats are aggregated across all pickups, not per session_id.
    All formula slots present — fill in main.py.
    """
    session_id: int

    # Arduino-derived (all pickups aggregated)
    phone_pickups:        Optional[int]   = None
    total_held_sec:       Optional[float] = None
    avg_held_sec:         Optional[float] = None

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