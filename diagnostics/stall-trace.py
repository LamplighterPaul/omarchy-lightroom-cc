#!/usr/bin/env python3
"""Read-only thread/IO sampling for a running Lightroom process; no stack or photo data."""
import argparse
import datetime
import json
import os
from pathlib import Path
import time


def thread_snapshot(process, tids=None):
    result = {}
    tasks = ((process/'task'/str(tid) for tid in tids) if tids is not None
             else (process/'task').glob('[0-9]*'))
    for task in tasks:
        try:
            stat = (task / 'stat').read_text().rsplit(')', 1)[1].split()
            runtime, delay, slices = map(int, (task / 'schedstat').read_text().split())
            result[int(task.name)] = dict(start=int(stat[19]), runtime=runtime,
                delay=delay, slices=slices, state=stat[0],
                wait=(task / 'wchan').read_text().strip())
        except (OSError, ValueError, IndexError):
            continue
    return result


def thread_deltas(before, after, scheduler_stats):
    result = []
    for tid, item in after.items():
        old = before.get(tid)
        if old is None or old['start'] != item['start']:
            continue
        if item['runtime'] < old['runtime'] or item['delay'] < old['delay']:
            continue
        row = dict(tid=tid, cpu_ms=(item['runtime']-old['runtime'])/1e6,
                   state=item['state'], wait=item['wait'])
        # Disabled schedstats can expose old nonzero counters. Never present
        # their unchanged values as evidence that runnable threads did not wait.
        if scheduler_stats:
            row['runqueue_ms'] = (item['delay']-old['delay'])/1e6
        result.append(row)
    return result


def process_io(process):
    try:
        fields = dict(line.split(':', 1) for line in (process/'io').read_text().splitlines())
        return {key: int(fields[key]) for key in ('read_bytes', 'write_bytes', 'rchar', 'wchar')}
    except (OSError, ValueError, KeyError):
        return {}


def record(pid, seconds, interval, output, tids=None, all_threads=False):
    process = Path('/proc') / str(pid)
    if process.stat().st_uid != os.getuid() or (process/'comm').read_text().strip().lower() != 'lightroom.exe':
        raise ValueError('Expected your own running lightroom.exe process')
    identity = (process/'stat').read_text().rsplit(')', 1)[1].split()[19]
    schedpath = Path('/proc/sys/kernel/sched_schedstats')
    enabled = schedpath.exists() and schedpath.read_text().strip() == '1'
    selected = None if all_threads else sorted(set(tids or [pid]))
    before = thread_snapshot(process, selected)
    io_before = process_io(process)
    started = previous = time.monotonic()
    cpu_started = time.process_time()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids overwriting another trace.
    with output.open('x') as stream:
        stream.write(json.dumps(dict(type='metadata', pid=pid, start_epoch=time.time(),
            started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            interval=interval, tids=selected, scheduler_stats_enabled=enabled,
            note='Sampled Linux thread states, not call stacks. Runnable delay is unavailable when schedstats is disabled. IO counters include cache activity. Sampling can perturb timing.'))+'\n')
        count = 0
        while time.monotonic()-started < seconds:
            time.sleep(max(0, min(interval, seconds-(time.monotonic()-started))))
            scan_start = time.monotonic()
            try:
                if (process/'stat').read_text().rsplit(')', 1)[1].split()[19] != identity:
                    break
            except OSError:
                break
            after = thread_snapshot(process, selected)
            io_after = process_io(process)
            # Recheck the global availability flag; never enable it ourselves.
            current_enabled = schedpath.exists() and schedpath.read_text().strip() == '1'
            now = time.monotonic()
            stream.write(json.dumps(dict(type='sample', epoch=time.time(), t=now-started,
                elapsed_ms=(now-previous)*1000, scan_ms=(now-scan_start)*1000,
                scheduler_stats_enabled=current_enabled,
                threads=thread_deltas(before, after, enabled and current_enabled),
                io={k: v-io_before[k] for k,v in io_after.items() if k in io_before and v>=io_before[k]}))+'\n')
            before, io_before, previous, enabled = after, io_after, now, current_enabled
            count += 1
        wall = time.monotonic()-started
        summary = dict(type='summary', samples=count, duration=wall,
                       sampler_cpu_seconds=time.process_time()-cpu_started)
        stream.write(json.dumps(summary)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pid', type=int, nargs='?')
    parser.add_argument('--prefix', type=Path, help='Find Lightroom in this prefix instead of supplying a PID.')
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--interval', type=float, default=.05)
    parser.add_argument('--output', type=Path, required=True)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--tid', type=int, action='append', help='Thread to sample; repeat for several. Default: main thread.')
    selection.add_argument('--all-threads', action='store_true', help='Expensive diagnostic mode; measure sampler overhead.')
    args = parser.parse_args()
    if (args.pid is None) == (args.prefix is None):
        parser.error('Supply exactly one of PID or --prefix')
    if args.prefix:
        from resources import snapshot
        matches = [pid for pid, item in snapshot(args.prefix.expanduser().resolve()).items()
                   if item['name'].lower() == 'lightroom.exe']
        if len(matches) != 1:
            parser.error(f'Expected one Lightroom process in the prefix; found {len(matches)}')
        args.pid = matches[0]
    if not 1 <= args.seconds <= 120 or not .02 <= args.interval <= 1:
        parser.error('Use 1–120 seconds and a 0.02–1 second interval')
    print(json.dumps(record(args.pid, args.seconds, args.interval, args.output,
                            args.tid, args.all_threads), indent=2))


if __name__ == '__main__':
    main()
