#!/usr/bin/env python3
"""Decode opt-in loupe-present-timing.patch traces; timestamps are host monotonic ns.

These measure CPU-side X11 submission, not GPU completion or visible frames.
Read after gestures stop. Uncommitted records are ignored; capacity is finite.
"""
import argparse
import csv
import json
from pathlib import Path
import struct


FIELDS = "start geometry clip blit flush end hwnd surface thread outcome width height commit".split()
ROW = struct.Struct("<13Q")


def read_trace(path):
    data = path.read_bytes()
    if len(data) < 16 or data[:8] != b"LRPRES01":
        raise ValueError("Unknown presentation trace format")
    capacity, = struct.unpack_from("<Q", data, 8)
    if len(data) != 16 + capacity * ROW.size or capacity != 65536:
        raise ValueError("Invalid trace size/capacity")
    rows = []
    for index, values in enumerate(ROW.iter_unpack(data[16:])):
        if values[-1] != index + 1:
            continue
        row = dict(zip(FIELDS, values))
        if not 0 < row["start"] <= row["end"]:
            raise ValueError("Invalid committed timestamps")
        rows.append(row)
    return rows, len(rows) == capacity


def stats(values):
    values = sorted(values)
    if not values:
        return None
    def percentile(p):
        point = (len(values) - 1) * p
        lo = int(point)
        hi = min(lo + 1, len(values) - 1)
        return round(values[lo] + (values[hi] - values[lo]) * (point - lo), 6)
    return {"count": len(values), "median_ms": percentile(.5), "p95_ms": percentile(.95),
            "p99_ms": percentile(.99), "max_ms": round(values[-1], 6),
            "over_16_67_ms": sum(v > 16.67 for v in values),
            "over_33_33_ms": sum(v > 33.33 for v in values)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--phase", type=Path, help="JSON object from isolated-input.py")
    parser.add_argument("--trim", type=float, default=0, help="Seconds excluded at each phase boundary")
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    rows, full = read_trace(args.trace)
    total = len(rows)
    if args.phase:
        phase = json.loads(args.phase.read_text())
        start = (phase["start_monotonic"] + args.trim) * 1e9
        end = (phase["end_monotonic"] - args.trim) * 1e9
        if start >= end:
            parser.error("Trim removes the entire phase")
        rows = [r for r in rows if r["start"] >= start and r["end"] <= end]
    elif args.trim:
        parser.error("--trim requires --phase")
    if args.csv:
        with args.csv.open("w") as out:
            writer = csv.DictWriter(out, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    groups = {}
    for row in rows:
        key = f'{row["hwnd"]:x}:{row["surface"]:x}:{row["width"]}x{row["height"]}'
        groups.setdefault(key, []).append(row)
    result = {"total_committed": total, "capacity_reached": full, "selected": len(rows), "surfaces": {}}
    for key, group in groups.items():
        group.sort(key=lambda row: row["start"])
        outcomes = {}
        for row in group:
            outcomes[str(row["outcome"])] = outcomes.get(str(row["outcome"]), 0) + 1
        phases = {}
        for name, a, b in [("callback", "start", "end"), ("geometry", "start", "geometry"),
                           ("clip", "geometry", "clip"), ("copy", "clip", "blit"),
                           ("flush", "blit", "flush")]:
            phases[name] = stats([(row[b] - row[a]) / 1e6 for row in group
                                  if row[a] and row[b] and row[b] >= row[a]])
        gaps = [(b["start"] - a["start"]) / 1e6 for a, b in zip(group, group[1:])]
        result["surfaces"][key] = {"outcomes": outcomes, "callback_entry_intervals": stats(gaps), "phases": phases}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
