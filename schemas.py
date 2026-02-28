"""
schemas.py
----------
Pydantic models for all data sources.
Batch sizes are capped to prevent oversized payloads from
spiking memory on the 512MB Vultr instance.

user_id note:
  user_id is Optional[int] = None on every ingest model.
  It is never required and never validated — purely a storage slot
  for future personalization. Pass it when you have it; omit it otherwise.

Arduino / bridge note:
  serial_bridge.py sends one POST per pickup to /arduino/log.
  Payload: { session_id, picked_up_at, duration_sec }
  user_id can be added to the bridge payload once user accounts exist.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


MAX_BATCH = 500   # safety ceiling on all batch payloads


# ── Arduino ───────────────────────────────────────────────────────────────────

class ArduinoEntry(BaseModel):
    """
    One pickup event from serial_bridge.py.
    session_id is a per-pickup counter (1, 2, 3…) — not a study-session ID.
    user_id is optional — add once user accounts are implemented.
    """
    session_id:   int            = Field(..., description="Per-pickup counter from bridge (1, 2, 3…)")
    user_id:      Optional[int]  = Field(None, description="Optional user identifier — nullable")
    picked_up_at: str            = Field(..., description="ISO datetime from PC — e.g. 2025-01-15T14:32:00")
    duration_sec: float          = Field(..., ge=0, description="Seconds the phone was held")


# ── Study Tracker Log (Face Webcam) ──────────────────────────────────────────

VALID_FACE_EVENTS = frozenset({"SS", "SE", "FL", "FF", "LA", "LB"})

class StudyEvent(BaseModel):
    """
    Single face-cam event.
    user_id is optional — add once user accounts are implemented.
    """
    session_id: int
    user_id:    Optional[int] = Field(None, description="Optional user identifier — nullable")
    event_time: str           = Field(..., description="HH:MM:SS EST")
    event_type: str           = Field(..., description="SS | SE | FL | FF | LA | LB")

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
    Placeholder — tracks when the phone lights up.
    A separate AI will process the image content.
    Define event_type codes once the log format is finalized.
    user_id is optional — add once user accounts are implemented.
    """
    session_id: int
    user_id:    Optional[int] = Field(None, description="Optional user identifier — nullable")
    event_time: str           = Field(..., description="HH:MM:SS EST")
    event_type: str           = Field(..., description="TBD — fill in phone-cam event codes")
    extra_data: Optional[str] = Field(None, description="Optional JSON string for extra fields")


class PhoneCamBatch(BaseModel):
    events: List[PhoneCamEvent] = Field(..., max_length=MAX_BATCH)


# ── Stats Response ────────────────────────────────────────────────────────────

class SessionStats(BaseModel):
    """
    Calculated values returned to the frontend for a single session.

    Arduino stats are aggregated across ALL pickups (not per session_id)
    due to the bridge incrementing session_id per pickup rather than per
    study session.

    All face-cam stats are derived from the LA/LB/FL/FF/SS/SE event stream.
    """
    session_id:  int
    user_id:     Optional[int]   = None

    # ── Arduino-derived ───────────────────────────────────────────────────
    phone_pickups:         Optional[int]   = None   # total pickups in session
    total_held_sec:        Optional[float] = None   # total seconds phone held
    avg_held_sec:          Optional[float] = None   # average per pickup
    max_held_sec:          Optional[float] = None   # longest single pickup
    min_held_sec:          Optional[float] = None   # shortest single pickup

    # ── Face-cam-derived ──────────────────────────────────────────────────
    session_duration_sec:  Optional[float] = None   # SS → SE wall time
    total_look_away_sec:   Optional[float] = None   # sum of all LA→LB intervals
    look_away_count:       Optional[int]   = None   # number of LA events
    avg_look_away_sec:     Optional[float] = None   # total_look_away / count
    longest_look_away_sec: Optional[float] = None   # longest single LA→LB
    first_look_away_sec:   Optional[float] = None   # duration of very first LA→LB
    total_face_lost_sec:   Optional[float] = None   # sum of all FL→FF intervals
    face_lost_count:       Optional[int]   = None   # number of FL events
    focus_time_sec:        Optional[float] = None   # session - look_away - face_lost
    focus_pct:             Optional[float] = None   # (focus_time / session) * 100

    # ── Phone-cam-derived (placeholder) ──────────────────────────────────
    phone_cam_stat_1:      Optional[float] = None   # rename when defined
    phone_cam_stat_2:      Optional[float] = None   # rename when defined