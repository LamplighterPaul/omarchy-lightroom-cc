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
        'min_perf_pct': '/sys/devices/system/cpu/intel_pstate/min_perf_pct',
        'max_perf_pct': '/sys/devices/system/cpu/intel_pstate/max_perf_pct',
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
    policies = {}
    for policy in Path('/sys/devices/system/cpu/cpufreq').glob('policy*'):
        values = {}
        for name in ('scaling_driver', 'scaling_governor', 'energy_performance_preference',
                     'scaling_min_freq', 'scaling_max_freq', 'cpuinfo_max_freq'):
            try:
                values[name] = (policy / name).read_text().strip()
            except OSError:
                pass
        policies[policy.name] = values
    result['cpu_policies'] = policies
    supplies = {}
    for path in Path('/sys/class/power_supply').glob('*/online'):
        try:
            supplies[path.parent.name] = int(path.read_text())
        except (OSError, ValueError):
            pass
    result['power_supplies_online'] = supplies
    # RAPL constraints are hardware policy, not a VM or application quota.
    # Energy counters may require privilege; do not invent a wattage from limits.
    caps = {}
    for domain in Path('/sys/class/powercap').glob('intel-rapl:*'):
        values = {}
        for path in [domain / 'name', domain / 'enabled', *domain.glob('constraint_*')]:
            try:
                values[path.name] = path.read_text().strip()
            except OSError:
                pass
        if values:
            caps[domain.name] = values
    result['rapl_constraints'] = caps
    temperatures = {}
    for sensor in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            name = (sensor / 'name').read_text().strip()
            if name not in ('coretemp', 'k10temp', 'zenpower', 'xe', 'amdgpu', 'acpitz'):
                continue
            for path in sensor.glob('temp*_input'):
                label = path.with_name(path.name.replace('_input', '_label'))
                key = label.read_text().strip() if label.exists() else path.stem
                temperatures[f'{sensor.name}/{name}/{key}'] = int(path.read_text()) / 1000
        except (OSError, ValueError):
            pass
    result['temperatures_c'] = temperatures
    gpu_clocks = {}
    for directory in Path('/sys/class/drm').glob('card*/device/tile*/gt*/freq*'):
        values = {}
        for name in ('act_freq', 'cur_freq', 'min_freq', 'max_freq', 'rp0_freq', 'power_profile'):
            try:
                values[name] = (directory / name).read_text().strip()
            except OSError:
                pass
        if values:
            gpu_clocks[str(directory.relative_to('/sys/class/drm'))] = values
    if gpu_clocks:
        result['xe_gpu_frequency_mhz'] = gpu_clocks
    throttles = {}
    for path in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/thermal_throttle/*throttle_count'):
        try:
            throttles[f'{path.parent.parent.name}/{path.name}'] = int(path.read_text())
        except (OSError, ValueError):
            pass
    if throttles:
        result['thermal_throttle_counts'] = throttles
    return result


def process_constraints(pid):
    """Capture effective placement and every cgroup ancestor, including quotas."""
    result = {}
    try:
        result.update(nice=os.getpriority(os.PRIO_PROCESS, pid),
                      cpu_affinity=sorted(os.sched_getaffinity(pid)),
                      scheduler_policy=os.sched_getscheduler(pid))
        membership = (Path('/proc') / str(pid) / 'cgroup').read_text().splitlines()
        relative = next(line[3:] for line in membership if line.startswith('0::'))
        root = Path('/sys/fs/cgroup')
        group = root / relative.lstrip('/')
        ancestors = []
        while group.is_relative_to(root):
            values = {}
            for name in ('cpu.max', 'cpu.weight', 'cpu.stat', 'cpuset.cpus.effective',
                         'memory.max', 'memory.high'):
                try:
                    values[name] = (group / name).read_text().strip()
                except OSError:
                    pass
            # Ancestors can cover other apps. Do not attribute their usage to Lightroom.
            ancestors.append(dict(level=len(ancestors), **values))
            if group == root:
                break
            group = group.parent
        result['cgroup_ancestors'] = ancestors
    except (OSError, StopIteration):
        pass
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
            main_process_constraints={str(pid): process_constraints(pid)
                for pid, item in after.items() if item['name'].lower() == 'lightroom.exe'},
            exited_processes=len(set(before)-set(after))))
        before, last = after, now
    return dict(started_utc=utc,
        duration=round(last-started, 3), interval=interval,
        note='CPU 100% = one core. GPU percentages are per DRM client/engine, not whole-GPU utilization. '
             'PSS apportions shared memory. Exited/new processes can make CPU incomplete. '
             'Throttle counts are cumulative: compare changes during this run, not absolute values. '
             'Cgroup ancestor counters may include other applications. GPU clocks are instantaneous. '
             'RAPL limits are configured hardware constraints, not measured power consumption. '
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
