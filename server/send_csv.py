"""
Send CSV files from the logs/ directory to the Vultr server.

Run with:  python send_csv.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Load .env from project root ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SERVER_IP = os.getenv("VULTR_IPV4")
if not SERVER_IP:
    print("ERROR: VULTR_IPV4 not found in .env")
    sys.exit(1)

URL = f"http://{SERVER_IP}:8000/upload"

# ── Gather CSVs from logs/ (all optional) ──
LOGS_DIR = PROJECT_ROOT / "logs"

CSV_NAMES = {
    "notifications": "notifications.csv",
    "session_log":   "session_log.csv",
    "pickedup":      "pickedup.csv",
}

files_to_send = {}
handles = []

for field, filename in CSV_NAMES.items():
    csv_path = LOGS_DIR / filename
    if csv_path.is_file():
        fh = open(csv_path, "rb")
        handles.append(fh)
        files_to_send[field] = (filename, fh, "text/csv")
        print(f"  ✓ Found {csv_path}")
    else:
        print(f"  ⚠ Skipping {filename} (not found)")

if not files_to_send:
    print("ERROR: No CSV files found in logs/ — nothing to send.")
    sys.exit(1)

print(f"\nSending {len(files_to_send)} CSV(s) to {URL} ...")

try:
    resp = requests.post(URL, files=files_to_send, timeout=30)
    resp.raise_for_status()
    print("Success!", resp.json())
except requests.exceptions.ConnectionError:
    print(f"ERROR: Could not connect to {URL}. Is the server running?")
    sys.exit(1)
except requests.exceptions.HTTPError:
    print(f"ERROR: Server returned {resp.status_code}: {resp.text}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    for fh in handles:
        fh.close()
