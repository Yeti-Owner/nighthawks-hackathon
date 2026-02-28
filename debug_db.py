"""
debug_db.py
-----------
Standalone database inspector — run this on Vultr to see what's
currently in every table. Does NOT modify any data.

Run with:
  uv run debug_db.py
  — or optionally point at a different DB file:
  uv run debug_db.py --db /path/to/other.db

Output sections:
  [1] arduino_log    — raw pickup rows waiting to be calculated
  [2] study_log      — raw face-cam events waiting to be calculated
  [3] phone_cam_log  — raw phone-cam events (placeholder)
  [4] session_stats  — calculated and cached results
  [5] Row counts     — quick summary of all four tables
"""

import sqlite3
import argparse
import sys
import os

DEFAULT_DB = "middleman.db"
DIVIDER    = "-" * 72


def connect(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        sys.exit(
            f"[debug] Database not found at '{db_path}'.\n"
            f"        Has the server been started at least once? (init_db runs on startup)"
        )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def print_table(conn: sqlite3.Connection, table: str, label: str, limit: int = 100) -> int:
    """Print up to `limit` rows from a table. Returns actual row count."""
    print(f"\n{'═' * 72}")
    print(f"  {label}")
    print('═' * 72)

    try:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        rows  = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    except sqlite3.OperationalError as e:
        print(f"  ERROR reading table '{table}': {e}")
        return 0

    if total == 0:
        print("  (empty — no rows)")
        return 0

    if total > limit:
        print(f"  Showing latest {limit} of {total} rows  (oldest rows omitted)\n")
    else:
        print(f"  {total} row(s)\n")

    # Print column headers
    cols = rows[0].keys()
    col_widths = {c: max(len(c), max(len(str(row[c])) for row in rows)) for c in cols}
    header = "  " + "  ".join(c.ljust(col_widths[c]) for c in cols)
    print(header)
    print("  " + DIVIDER)

    for row in rows:
        line = "  " + "  ".join(str(row[c]).ljust(col_widths[c]) for c in cols)
        print(line)

    return total


def print_session_stats(conn: sqlite3.Connection, limit: int = 50) -> int:
    """session_stats has no 'id' column — sort by session_id instead."""
    print(f"\n{'═' * 72}")
    print(f"  [4] session_stats  (calculated results)")
    print('═' * 72)

    try:
        total = conn.execute("SELECT COUNT(*) FROM session_stats").fetchone()[0]
        rows  = conn.execute(
            "SELECT * FROM session_stats ORDER BY session_id DESC LIMIT ?", (limit,)
        ).fetchall()
    except sqlite3.OperationalError as e:
        print(f"  ERROR reading session_stats: {e}")
        return 0

    if total == 0:
        print("  (empty — no stats calculated yet)")
        print("  Tip: POST to /stats/calculate/{session_id} to populate this table.")
        return 0

    if total > limit:
        print(f"  Showing latest {limit} of {total} sessions\n")
    else:
        print(f"  {total} session(s)\n")

    cols = rows[0].keys()
    col_widths = {c: max(len(c), max(len(str(row[c] if row[c] is not None else "None")) for row in rows)) for c in cols}
    header = "  " + "  ".join(c.ljust(col_widths[c]) for c in cols)
    print(header)
    print("  " + DIVIDER)

    for row in rows:
        line = "  " + "  ".join(
            str(row[c] if row[c] is not None else "—").ljust(col_widths[c])
            for c in cols
        )
        print(line)

    return total


def print_summary(counts: dict) -> None:
    print(f"\n{'═' * 72}")
    print("  ROW COUNT SUMMARY")
    print('═' * 72)
    for table, count in counts.items():
        status = ""
        if table == "arduino_log" and count > 0:
            status = "  ← raw pickups pending calculation"
        elif table == "study_log" and count > 0:
            status = "  ← raw events pending calculation"
        elif table == "session_stats" and count == 0:
            status = "  ← no sessions calculated yet"
        print(f"  {table:<20} {count} rows{status}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect the Middleman SQLite database without modifying anything."
    )
    parser.add_argument(
        "--db", default=DEFAULT_DB,
        help=f"Path to the database file (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Max rows to display per table (default: 100)"
    )
    args = parser.parse_args()

    print(f"\n[debug] Inspecting: {os.path.abspath(args.db)}")

    conn   = connect(args.db)
    counts = {}

    counts["arduino_log"]   = print_table(conn, "arduino_log",   "[1] arduino_log   (raw pickup data from bridge)", args.limit)
    counts["study_log"]     = print_table(conn, "study_log",     "[2] study_log     (raw face-cam events)",          args.limit)
    counts["phone_cam_log"] = print_table(conn, "phone_cam_log", "[3] phone_cam_log (raw phone-cam events)",         args.limit)
    counts["session_stats"] = print_session_stats(conn, args.limit)

    print_summary(counts)

    # Quick diagnostic hints
    hints = []
    if counts["arduino_log"] == 0 and counts["session_stats"] == 0:
        hints.append("arduino_log is empty — has serial_bridge.py sent any data yet?")
    if counts["arduino_log"] > 0 and counts["session_stats"] == 0:
        hints.append(
            f"arduino_log has {counts['arduino_log']} row(s) but no stats yet. "
            "POST to /stats/calculate/{session_id} to process and store them."
        )
    if counts["study_log"] > 0 and counts["session_stats"] == 0:
        hints.append(
            f"study_log has {counts['study_log']} row(s) pending calculation."
        )

    if hints:
        print("  HINTS")
        print("  " + DIVIDER)
        for h in hints:
            print(f"  • {h}")
        print()

    conn.close()


if __name__ == "__main__":
    main()