"""
debug_db.py
-----------
Standalone database inspector — run this on Vultr to see what's
currently in every table. Does NOT modify any data.

Run with:
  uv run debug_db.py
  — or point at a different DB file:
  uv run debug_db.py --db /path/to/other.db
  — limit rows shown:
  uv run debug_db.py --limit 50

Output sections:
  [1] arduino_log    — raw pickup rows waiting to be calculated
  [2] study_log      — raw face-cam events waiting to be calculated
  [3] phone_cam_log  — raw phone-cam events (placeholder)
  [4] session_stats  — calculated and cached results (all stat columns)
  [5] Row counts     — quick summary of all four tables
  [6] Hints          — diagnostic suggestions based on table state
"""

import sqlite3
import argparse
import sys
import os

DEFAULT_DB = "middleman.db"
DIVIDER    = "-" * 80


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
    print(f"\n{'═' * 80}")
    print(f"  {label}")
    print('═' * 80)

    try:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        rows  = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
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

    _print_rows(rows)
    return total


def print_session_stats(conn: sqlite3.Connection, limit: int = 50) -> int:
    """
    Print session_stats table. No 'id' column — sorted by session_id.
    Displays all stat columns including new user_id and face-cam detail stats.
    """
    print(f"\n{'═' * 80}")
    print(f"  [4] session_stats  (calculated results)")
    print('═' * 80)

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

    _print_rows(rows, none_display="—")
    return total


def _print_rows(rows, none_display: str = "None"):
    """Render rows as a fixed-width table."""
    cols = rows[0].keys()
    col_widths = {
        c: max(
            len(c),
            max(len(str(row[c]) if row[c] is not None else none_display) for row in rows)
        )
        for c in cols
    }
    header = "  " + "  ".join(c.ljust(col_widths[c]) for c in cols)
    print(header)
    print("  " + DIVIDER)
    for row in rows:
        line = "  " + "  ".join(
            str(row[c] if row[c] is not None else none_display).ljust(col_widths[c])
            for c in cols
        )
        print(line)


def print_summary(counts: dict) -> None:
    print(f"\n{'═' * 80}")
    print("  ROW COUNT SUMMARY")
    print('═' * 80)
    for table, count in counts.items():
        note = ""
        if table == "arduino_log"   and count > 0: note = "  ← raw pickups pending calculation"
        if table == "study_log"     and count > 0: note = "  ← raw events pending calculation"
        if table == "phone_cam_log" and count > 0: note = "  ← raw phone-cam events pending"
        if table == "session_stats" and count == 0: note = "  ← no sessions calculated yet"
        print(f"  {table:<22} {count} row(s){note}")
    print()


def print_hints(counts: dict) -> None:
    hints = []

    if counts["arduino_log"] == 0 and counts["session_stats"] == 0:
        hints.append(
            "arduino_log is empty — has serial_bridge.py sent any data yet?\n"
            "    Run:  python serial_bridge.py  on the PC connected to the Arduino."
        )
    if counts["arduino_log"] > 0 and counts["session_stats"] == 0:
        hints.append(
            f"arduino_log has {counts['arduino_log']} row(s) but no stats calculated.\n"
            "    Run:  POST /stats/calculate/{{session_id}}  to process and store them."
        )
    if counts["study_log"] > 0 and counts["session_stats"] == 0:
        hints.append(
            f"study_log has {counts['study_log']} row(s) pending calculation."
        )
    if counts["phone_cam_log"] > 0:
        hints.append(
            f"phone_cam_log has {counts['phone_cam_log']} row(s) — "
            "phone-cam stats are placeholders until event codes are defined."
        )

    if hints:
        print(f"{'═' * 80}")
        print("  HINTS")
        print('═' * 80)
        for h in hints:
            print(f"  • {h}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect the Middleman SQLite database — read-only, no modifications."
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

    counts["arduino_log"]   = print_table(conn, "arduino_log",   "[1] arduino_log   (raw pickup data from bridge)",  args.limit)
    counts["study_log"]     = print_table(conn, "study_log",     "[2] study_log     (raw face-cam events)",          args.limit)
    counts["phone_cam_log"] = print_table(conn, "phone_cam_log", "[3] phone_cam_log (raw phone-cam events)",         args.limit)
    counts["session_stats"] = print_session_stats(conn, args.limit)

    print_summary(counts)
    print_hints(counts)

    conn.close()


if __name__ == "__main__":
    main()