#!/usr/bin/env python3
"""Record prefix resource timelines; never capture tokens, filenames or photos."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from resources import snapshot


def host_state():
    """Read policy and pressure without changing power or scheduler settings."""
    paths = {
        'platform_profile': '/sys/firmware/acpi/platform_profile',
        'governor': '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor',
        'energy_preference': '/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference',
        'no_turbo': '/sys/devices/system/cpu/intel_pstate/no_turbo',
        'cpu_pressure': '/proc/pressure/cpu',
        'memory_pressure': '/proc/pressure/memory',
        'io_pressure': '/proc/pressure/io',
    }
    result = {}
    for name, path in paths.items():
        try:
            result[name] = Path(path).read_text().strip()
        except OSError:
            pass
    clocks = []
    for path in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_cur_freq'):
        try:
            clocks.append(int(path.read_text()) / 1000)
        except (OSError, ValueError):
            pass
    if clocks:
        result['cpu_policy_mhz'] = dict(min=min(clocks), max=max(clocks), mean=sum(clocks)/len(clocks))
    return result


def record(prefix, seconds, interval=1):
    hz = os.sysconf('SC_CLK_TCK')
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    started = last = time.monotonic()
    before = snapshot(prefix)
    samples = []
    while time.monotonic() - started < seconds:
        time.sleep(min(interval, max(0, seconds - (time.monotonic() - started))))
        now = time.monotonic()
        after = snapshot(prefix)
        rows, engines = [], {}
        for pid, item in after.items():
            prior = before.get(pid)
            cpu = None
            if prior and prior['start'] == item['start']:
                cpu = (item['ticks'] - prior['ticks']) / hz / (now - last) * 100
                for key, (busy, total) in item['engines'].items():
                    old = prior['engines'].get(key)
                    if old and total > old[1] and busy >= old[0]:
                        # Shared DRM clients are counted once across processes.
                        engines[key] = round(100 * (busy-old[0]) / (total-old[1]), 2)
            rows.append(dict(pid=pid, name=item['name'], cpu_percent=None if cpu is None else round(cpu, 2),
                             pss_mib=round(item['pss_kib']/1024, 2)))
        focused = None
        try:
            window = json.loads(subprocess.check_output(['hyprctl', 'activewindow', '-j'],
                                stderr=subprocess.DEVNULL, timeout=1))
            focused = window.get('pid') in after
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        samples.append(dict(t=round(now-started, 3), prefix_window_focused=focused,
            cpu_percent=round(sum(r['cpu_percent'] or 0 for r in rows), 2),
            pss_mib=round(sum(r['pss_mib'] for r in rows), 2),
            gpu_engine_percent=engines, processes=rows, host=host_state(),
            exited_processes=len(set(before)-set(after))))
        before, last = after, now
    return dict(started_utc=utc,
        duration=round(last-started, 3), interval=interval,
        note='CPU 100% = one core. GPU percentages are per DRM client/engine, not whole-GPU utilization. '
             'PSS apportions shared memory. Exited/new processes can make CPU incomplete. '
             'This records resources, not presentation FPS. Match with MangoHud and an actual interaction.',
        samples=samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300:
        parser.error('--seconds must be between 1 and 300')
    prefix = args.prefix.expanduser().resolve()
    if not (prefix / 'system.reg').is_file():
        parser.error('Expected an initialized Wine/Proton prefix')
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-resources.json')
    print(f'Recording {args.seconds:g}s to {path}. Use the same photo and zoom for comparisons.', flush=True)
    report = record(prefix, args.seconds)
    path.write_text(json.dumps(report, indent=2)+'\n')
    samples = report['samples']
    print(json.dumps(dict(path=str(path), peak_cpu_percent=max(s['cpu_percent'] for s in samples),
        peak_pss_mib=max(s['pss_mib'] for s in samples),
        focused_samples=sum(s['prefix_window_focused'] is True for s in samples)), indent=2))


if __name__ == '__main__':
    main()
