"""
serial_bridge.py
----------------
Runs on the PC physically connected to the Arduino via USB.
NOT deployed to Vultr — this runs locally on your machine.

Rewritten to match the new approach from Arduino_ending.docx:
  - Monitors Serial output LIVE instead of sending the 'e' export command
  - Collects pickups in memory as they happen
  - Sends ALL pickups to the server when CTRL+C is pressed
  - Uses only stdlib (urllib.request) — no 'requests' library needed

Install dependencies (run once, on your local machine):
  uv add pyserial

Usage:
  uv run serial_bridge.py

Config — edit the constants below before running:
  PORT       : serial port the Arduino is on
  BASE_URL   : your Vultr server address
  SESSION_ID : study session ID to tag Arduino data with
               (incremented per pickup automatically when sending)

How it parses Arduino output:
  ">> PICKED UP #N"      → increments total_pickups counter
  "   Was held for:  Xh Xm Xs (N sec)"  → extracts N seconds
     (splits on '(' and strips ' sec)')
"""

import serial
import time
import json
import urllib.request
from datetime import datetime

# ── Config — edit these before running ───────────────────────────────────────
PORT       = "/dev/ttyACM0"              # Windows: "COM3", Linux: "/dev/ttyUSB0" or "/dev/ttyACM0"
BAUD       = 9600
BASE_URL   = "http://45.32.173.69:8000"  # your Vultr server
SESSION_ID = 1                           # study session ID (starting value)


# ── HTTP helper ───────────────────────────────────────────────────────────────

def send_post_request(endpoint: str, payload: dict) -> dict:
    """Send a POST request using stdlib urllib — no third-party libraries needed."""
    url  = BASE_URL.rstrip("/") + "/" + endpoint.lstrip("/")
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}


# ── Sender ────────────────────────────────────────────────────────────────────

def send_all_sessions(all_sessions: list, total_pickups: int) -> None:
    """
    POST each pickup individually to /arduino/log.
    session_id increments per pickup (matches bridge behavior expected by server).
    picked_up_at is set once for the whole batch (datetime.now() at send time).
    """
    print("\nSending data to server...")
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    sid = SESSION_ID

    for s in all_sessions:
        payload = {
            "session_id":   sid,
            "picked_up_at": timestamp,
            "duration_sec": s["seconds"],
        }
        print(f"  Sending pickup {s['session']}...")
        response = send_post_request("/arduino/log", payload)
        print(f"  Server replied: {response}")
        sid += 1

    print(f"\nDone! Total pickups sent: {total_pickups}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Connected to Arduino on {PORT}")
    print(f"Sending data to {BASE_URL}")
    print("Press CTRL+C to end session and send data to server")
    print("----------------------------------------------------")

    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)   # wait for Arduino to finish resetting after DTR toggle

    total_pickups = 0
    total_seconds = 0
    all_sessions  = []

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            print(line)

            # Arduino prints: ">> PICKED UP #N"
            if line.startswith(">> PICKED UP"):
                total_pickups += 1

            # Arduino prints: "   Was held for:       00h 00m 15s (15 sec)"
            elif line.startswith("Was held for:") or "Was held for:" in line:
                parts = line.split("(")
                if len(parts) > 1:
                    try:
                        sec = int(parts[1].replace("sec)", "").strip())
                        total_seconds += sec
                        all_sessions.append({
                            "session": total_pickups,
                            "seconds": sec,
                        })
                    except ValueError:
                        print(f"  [bridge] WARNING — could not parse duration from: {line!r}")

    except KeyboardInterrupt:
        print("\nSession ended!")
        if all_sessions:
            send_all_sessions(all_sessions, total_pickups)
        else:
            print("No pickup data to send.")

    finally:
        ser.close()


if __name__ == "__main__":
    main()