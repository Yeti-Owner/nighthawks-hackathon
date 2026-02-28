"""
Test script — exercises the manager's sync endpoints.

Usage:  python test_sync.py          (manager must be running on localhost:8000)
"""

import time
import requests

BASE = "http://localhost:8000"


def _pretty(label: str, resp: requests.Response) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"  Status: {resp.status_code}")
    try:
        print(f"  Body:   {resp.json()}")
    except Exception:
        print(f"  Body:   {resp.text[:300]}")
    print(f"{'─' * 50}")


def main() -> None:
    print("=" * 56)
    print("  AURELIUS — Manager Sync Test")
    print("=" * 56)

    # ── 1. Send CSVs ──
    print("\n▶ POST /sync/send  (upload CSVs to Vultr) ...")
    r = requests.post(f"{BASE}/sync/send")
    _pretty("Send started", r)

    # Poll until done
    print("\n⏳ Polling /sync/send/status ...")
    for _ in range(60):
        time.sleep(1)
        r = requests.get(f"{BASE}/sync/send/status")
        data = r.json()
        status = data.get("status", "?")
        print(f"   status = {status}")
        if status != "running":
            break
    _pretty("Send final status", r)

    # ── 2. Receive data ──
    print("\n▶ POST /sync/receive  (download data from Vultr) ...")
    r = requests.post(f"{BASE}/sync/receive")
    _pretty("Receive result", r)

    # ── 3. Read each table back ──
    for table in ["notifications", "session_log", "pickedup"]:
        print(f"\n▶ GET /sync/data/{table} ...")
        r = requests.get(f"{BASE}/sync/data/{table}")
        _pretty(f"Data — {table}", r)

    print("\n✅ All tests completed.\n")


if __name__ == "__main__":
    main()
