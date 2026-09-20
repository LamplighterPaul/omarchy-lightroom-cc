#!/usr/bin/env python3
"""Record a bounded MangoHud window inside an active private-fixture photo pan.

First visually confirm a settled photo at 100% zoom, with room to pan vertically,
and MangoHud logging off. This reports renderer frame intervals, not display FPS.
No socket connection: multiple Vulkan instances can leave the advertised socket
attached to an inactive instance. Numeric output is retained on validation errors.
"""
import argparse
import csv
import datetime
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time


def summarize(path, start, stop, pan):
    rows = list(csv.DictReader(path.read_text().splitlines()[2:]))
    if not rows:
        raise ValueError('No frame samples')
    values = [float(row['frametime']) for row in rows]
    elapsed = [float(row['elapsed']) / 1e9 for row in rows]
    if (any(not math.isfinite(x) or x <= 0 for x in values)
            or any(not math.isfinite(x) or x < 0 for x in elapsed)
            or any(b < a for a, b in zip(elapsed, elapsed[1:]))):
        raise ValueError('Invalid frame samples')
    log_start = datetime.datetime.strptime(path.stem.removeprefix('lightroom_'), '%Y-%m-%d_%H-%M-%S').timestamp()
    # The filename has whole-second precision. Reject a previous recording or
    # a double toggle instead of reporting a short accidental burst as a pass.
    if not start['start_epoch'] - 1 <= log_start <= start['end_epoch'] + 1:
        raise ValueError('CSV belongs to another recording')
    span = elapsed[-1] - elapsed[0]
    if not 4 <= span <= 7:
        raise ValueError(f'Expected sustained recording; observed {span:.3f} seconds')
    if not (pan['start_monotonic'] < start['start_monotonic']
            and stop['end_monotonic'] < pan['end_monotonic']):
        raise ValueError('Logging hotkeys were not contained in the active gesture')
    ordered = sorted(values)
    percentile = lambda q: ordered[math.ceil(q * len(ordered)) - 1]
    interior = sorted(v for v, t in zip(values, elapsed) if elapsed[0] + .5 <= t <= elapsed[-1] - .5)
    return {'samples': len(values), 'recorded_span_seconds': span,
            'median_ms': statistics.median(values), 'p95_ms': percentile(.95),
            'p99_ms': percentile(.99), 'max_ms': max(values),
            'over_16_67_ms': sum(x > 16.67 for x in values),
            'over_33_33_ms': sum(x > 33.33 for x in values),
            'interior_0_5s_trim': {
                'samples': len(interior), 'max_ms': max(interior) if interior else None,
                'over_16_67_ms': sum(x > 16.67 for x in interior),
                'note': 'Secondary view excluding fixed half-second control boundaries. Full recording above remains primary.'},
            'note': 'All CSV intervals retained, including stalls. Renderer timing, not physical display FPS.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output directory already exists')
    if os.environ.get('DISPLAY') != ':1' or os.environ.get('WAYLAND_DISPLAY') != 'lightroom-test':
        parser.error('Requires the owned private lightroom-test/:1 fixture')
    helper = Path(__file__).with_name('isolated-input.py')
    logs = Path(os.environ.get('LRCC_DATA', Path.home() / '.local/share/omarchy-lightroom-cc')) / 'measurements/mangohud'
    args.output.mkdir(parents=True)
    before = set(logs.glob('*.csv'))
    result = {'status': 'incomplete', 'files': [], 'phases': [],
              'precondition': 'Caller must independently verify settled photo at 100% zoom; logging initially off.'}
    pan = None
    started = False

    def action(name):
        output = subprocess.check_output(['python3', str(helper), name], text=True, timeout=5)
        phase = json.loads(output.splitlines()[-1])
        result['phases'].append(phase)
        return phase

    try:
        # isolated-input verifies the X server belongs to our headless Weston
        # before sending anything. Leave warm-up and cooldown outside recording.
        pan = subprocess.Popen(['python3', str(helper), 'pan-vertical'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(1)
        if pan.poll() is not None:
            raise RuntimeError('Gesture failed before recording: ' + pan.communicate()[1])
        start = action('record')
        started = True
        time.sleep(5)
        stop = action('record')
        started = False
        stdout, stderr = pan.communicate(timeout=15)
        if pan.returncode:
            raise RuntimeError('Gesture failed: ' + stderr)
        gesture = json.loads(stdout.splitlines()[-1])
        result['phases'].append(gesture)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            raw = [p for p in set(logs.glob('*.csv')) - before if not p.name.endswith('_summary.csv')]
            if raw and all(p.stat().st_size > 256 for p in raw):
                break
            time.sleep(.1)
        for path in sorted(set(logs.glob('*.csv')) - before):
            shutil.copy2(path, args.output / path.name)
            result['files'].append(path.name)
        if len(raw) != 1:
            raise ValueError(f'Expected one recording, found {len(raw)}; verify logging is off before retrying')
        result['timing'] = summarize(args.output / raw[0].name, start, stop, gesture)
        result['status'] = 'complete'
    except (OSError, ValueError, KeyError, csv.Error, RuntimeError, subprocess.SubprocessError) as exc:
        result['error'] = str(exc)
        raise
    finally:
        if started:
            try:
                action('record')
            except (OSError, ValueError, subprocess.SubprocessError):
                result['logging_state_unknown'] = True
        if pan is not None and pan.poll() is None:
            # Allow the bounded gesture to release its held button normally.
            try:
                pan.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                result['gesture_still_running'] = pan.pid
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['timing'], indent=2))


if __name__ == '__main__':
    main()
