#!/usr/bin/env python3
"""Slider event diagnostics -- reads slider_events.db and prints failure stats.

Usage:
    python scripts/slider_diagnose.py [--hours 24] [--db data/slider_events.db]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import Counter


def main() -> None:
    parser = argparse.ArgumentParser(description="Slider event diagnostics")
    parser.add_argument("--hours", type=int, default=24, help="Look back N hours (default: 24)")
    parser.add_argument("--db", type=str, default=None, help="Path to slider_events.db")
    args = parser.parse_args()

    db_path = args.db or os.path.join(os.path.dirname(__file__), "..", "data", "slider_events.db")
    db_path = os.path.abspath(db_path)

    if not os.path.isfile(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT * FROM slider_events WHERE created_at >= datetime('now', ?) ORDER BY id DESC",
        (f"-{args.hours} hours",),
    ).fetchall()

    if not rows:
        print(f"No slider events in the last {args.hours} hours.")
        return

    total = len(rows)
    results = Counter(r["result"] for r in rows)
    fail_reasons = Counter(r["fail_reason"] for r in rows if r["fail_reason"])
    trigger_sources = Counter(r["trigger_source"] or "unknown" for r in rows)
    slider_types = Counter(r["slider_type"] or "none" for r in rows)

    passed = results.get("passed", 0)
    attempts_with_type = sum(1 for r in rows if r["slider_type"] in ("nc", "puzzle"))
    rate = round(passed / attempts_with_type * 100, 1) if attempts_with_type else 0

    print(f"=== Slider Diagnostics (last {args.hours}h) ===")
    print(f"Total events: {total}")
    print(f"Success rate: {passed}/{attempts_with_type} = {rate}%")
    print()

    print("-- Results --")
    for result, count in results.most_common():
        print(f"  {result}: {count}")
    print()

    print("-- Failure Reasons --")
    if fail_reasons:
        for reason, count in fail_reasons.most_common():
            pct = round(count / total * 100, 1)
            print(f"  {reason}: {count} ({pct}%)")
    else:
        print("  (none)")
    print()

    print("-- Trigger Sources --")
    for src, count in trigger_sources.most_common():
        print(f"  {src}: {count}")
    print()

    print("-- Slider Types --")
    for stype, count in slider_types.most_common():
        print(f"  {stype}: {count}")
    print()

    ttls = [r["cookie_ttl_seconds"] for r in rows if r["cookie_ttl_seconds"] is not None]
    if ttls:
        print(f"-- Cookie TTL --")
        print(f"  avg: {sum(ttls) / len(ttls):.0f}s  min: {min(ttls)}s  max: {max(ttls)}s")
        print()

    print("-- Recent Events (last 10) --")
    for r in rows[:10]:
        ts = r["created_at"] or r["trigger_ts"] or "?"
        result_str = r["result"] or "?"
        reason = r["fail_reason"] or ""
        stype = r["slider_type"] or "?"
        src = r["trigger_source"] or "?"
        rgv = r["rgv587_consecutive"] or 0
        line = f"  [{ts}] {result_str:<8} type={stype:<8} src={src:<12} rgv={rgv}"
        if reason:
            line += f" reason={reason}"
        print(line)

    conn.close()


if __name__ == "__main__":
    main()
