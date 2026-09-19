#!/usr/bin/env python3
"""Measure serial menu input-to-MapNotify on the owned private Weston fixture.

Wait for each opening before closing it: fixed sleeps can hide long stalls and
misattribute a late File popup to the following Edit request. No pixel capture.
X11 mapping precedes visible presentation and includes observer scheduling.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pairs', type=int, default=10)
    parser.add_argument('--input', choices=('mixed', 'mouse', 'keyboard'), default='mouse')
    args = parser.parse_args()
    if not 1 <= args.pairs <= 30:
        parser.error('--pairs must be between 1 and 30')
    if args.output.exists():
        parser.error('output already exists')
    env = os.environ.copy()
    env.update(DISPLAY=':1', WAYLAND_DISPLAY='lightroom-test')
    helper = Path(__file__).with_name('isolated-input.py')
    data = Path(env.get('LRCC_DATA', Path.home() / '.local/share/omarchy-lightroom-cc'))

    def action(name):
        # Helper verifies the X server belongs to the headless fixture before input.
        result = subprocess.run(['python3', str(helper), name], env=env,
                                capture_output=True, text=True, check=True, timeout=15)
        return json.loads(result.stdout.splitlines()[-1])

    action('escape')
    action('escape')
    observer = subprocess.Popen([str(data / 'tools/x11-menu-events'), '60'],
                                env=env, stdout=subprocess.PIPE, text=True)
    events = queue.Queue()

    def reader():
        for line in observer.stdout:
            events.put(line.strip())
        events.put(None)

    threading.Thread(target=reader, daemon=True).start()
    result = {'status': 'incomplete', 'openings': [],
              'note': 'Input submission to X11 map receipt, not visible display latency.'}
    try:
        if not events.get(timeout=5).startswith('event,') or not events.get(timeout=5).startswith('ready,'):
            raise RuntimeError('Menu observer did not become ready')
        for index in range(args.pairs * 2):
            actions = {'mixed': ('menu-open', 'edit-menu-open'),
                       'mouse': ('menu-open', 'edit-menu-click'),
                       'keyboard': ('file-menu-key', 'edit-menu-open')}
            name = actions[args.input][index % 2]
            phase = action(name)
            row = {'action': name, 'phase': phase, 'map': None}
            result['openings'].append(row)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                event = events.get(timeout=max(.001, deadline-time.monotonic()))
                if event is None:
                    raise RuntimeError('Menu observer exited before the opening mapped')
                fields = event.split(',')
                if fields[0] != 'map' or float(fields[2]) < phase['start_monotonic']:
                    continue
                row['map'] = dict(monotonic=float(fields[2]), window=fields[3],
                                  x=int(fields[4]), y=int(fields[5]),
                                  width=int(fields[6]), height=int(fields[7]))
                row['latency_ms'] = (row['map']['monotonic']-phase['start_monotonic'])*1000
                break
            if row['map'] is None:
                raise RuntimeError('Opening did not map; stopping before sending another request')
            print(f'{index+1}: {name} {row["latency_ms"]:.3f} ms', flush=True)
            time.sleep(.15)
            action('escape')
            action('escape')
            time.sleep(.15)
        result['status'] = 'complete'
    except (RuntimeError, queue.Empty, subprocess.SubprocessError) as exc:
        result['error'] = str(exc) or 'Timed out waiting for a menu map; no next opening sent'
        raise
    finally:
        if observer.poll() is None:
            observer.terminate()
        observer.wait(timeout=5)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
