#!/usr/bin/env python3
"""One-shot main-thread performance hint for the selected Lightroom prefix.

No affinity restriction, elevated priority, global power change or ongoing poll.
Reset-on-fork prevents newly created native workers inheriting the UI hint.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import time


class SchedAttr(ctypes.Structure):
    _fields_ = [('size', ctypes.c_uint32), ('policy', ctypes.c_uint32),
                ('flags', ctypes.c_uint64), ('nice', ctypes.c_int32),
                ('priority', ctypes.c_uint32), ('runtime', ctypes.c_uint64),
                ('deadline', ctypes.c_uint64), ('period', ctypes.c_uint64),
                ('util_min', ctypes.c_uint32), ('util_max', ctypes.c_uint32)]


def scheduler():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.sched_getattr.argtypes = [ctypes.c_int, ctypes.POINTER(SchedAttr), ctypes.c_uint, ctypes.c_uint]
    libc.sched_getattr.restype = ctypes.c_int
    libc.sched_setattr.argtypes = [ctypes.c_int, ctypes.POINTER(SchedAttr), ctypes.c_uint]
    libc.sched_setattr.restype = ctypes.c_int
    return libc


def get_attr(libc, pid):
    attr = SchedAttr()
    if libc.sched_getattr(pid, ctypes.byref(attr), ctypes.sizeof(attr), 0):
        raise OSError(ctypes.get_errno(), 'sched_getattr failed')
    return attr


def hybrid_capacity(cpus, root=Path('/sys/devices/system/cpu')):
    try:
        capacities = {int((root / f'cpu{cpu}/cpu_capacity').read_text()) for cpu in cpus}
    except (OSError, ValueError):
        return False
    return len(capacities) > 1 and max(capacities) == 1024 and min(capacities) > 0


def matches(proc, prefix, runtime):
    try:
        if proc.stat().st_uid != os.getuid() or (proc / 'comm').read_text().strip().lower() != 'lightroom.exe':
            return False
        env = (proc / 'environ').read_bytes().split(b'\0')
        value = next((v[11:] for v in env if v.startswith(b'WINEPREFIX=')), None)
        if value is None or Path(os.fsdecode(value)).resolve() != prefix:
            return False
        paths = {f[5] for line in (proc / 'maps').read_text().splitlines()
                 if len(f := line.split(maxsplit=5)) == 6}
        executable = prefix / 'drive_c/Program Files/Adobe/Adobe Lightroom CC/lightroom.exe'
        return (str(executable) in paths
                and str(runtime / 'lib/wine/x86_64-unix/ntdll.so') in paths)
    except (OSError, ValueError):
        return False


def apply_hint(libc, pid):
    allowed = os.sched_getaffinity(pid)
    if not hybrid_capacity(allowed):
        return {'status': 'skipped', 'reason': 'No supported asymmetric CPU capacities'}
    attr = get_attr(libc, pid)
    # Preserve user/application scheduling choices and existing clamp requests.
    if attr.policy != os.SCHED_OTHER or attr.nice != 0 or attr.util_min != 0 or attr.util_max != 1024:
        return {'status': 'skipped', 'reason': 'Thread already has custom scheduling'}
    before = {'nice': attr.nice, 'runtime': attr.runtime, 'flags': attr.flags}
    attr.size = ctypes.sizeof(attr)
    # KEEP_PARAMS preserves nice/priority/slice. KEEP_POLICY must NOT be set:
    # on this kernel it also prevents RESET_ON_FORK from taking effect.
    attr.flags |= 0x01 | 0x10 | 0x20  # RESET_ON_FORK | KEEP_PARAMS | UTIL_CLAMP_MIN
    attr.util_min = 1024
    if libc.sched_setattr(pid, ctypes.byref(attr), 0):
        raise OSError(ctypes.get_errno(), 'sched_setattr failed')
    actual = get_attr(libc, pid)
    if (actual.util_min != 1024 or not actual.flags & 1
            or actual.policy != os.SCHED_OTHER or actual.nice != before['nice']
            or os.sched_getaffinity(pid) != allowed):
        actual.size = ctypes.sizeof(actual)
        actual.flags |= 0x10 | 0x20
        actual.util_min = 0
        if libc.sched_setattr(pid, ctypes.byref(actual), 0):
            raise OSError(ctypes.get_errno(), 'UI hint readback failed and minimum could not be restored')
        raise RuntimeError('UI hint readback failed; minimum restored, reset-on-fork may remain until exit')
    return {'status': 'applied', 'pid': pid, 'util_min': actual.util_min,
            'util_max': actual.util_max, 'reset_on_fork': bool(actual.flags & 1),
            'allowed_cpus': sorted(allowed), 'nice': actual.nice}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path, help='Selected Proton files directory')
    parser.add_argument('--pid', type=int, help='Restrict lookup to this process')
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    if not 0 <= args.timeout <= 120 or args.pid is not None and args.pid <= 0:
        parser.error('Invalid timeout or PID')
    prefix, runtime = args.prefix.resolve(), args.runtime.resolve()
    try:
        libc = scheduler()
        deadline = time.monotonic() + args.timeout
        while True:
            candidates = [Path('/proc') / str(args.pid)] if args.pid else Path('/proc').glob('[0-9]*')
            for proc in candidates:
                if matches(proc, prefix, runtime):
                    print(json.dumps(apply_hint(libc, int(proc.name))), flush=True)
                    return
            if time.monotonic() >= deadline:
                print(json.dumps({'status': 'skipped', 'reason': 'No matching Lightroom process before deadline'}))
                return
            time.sleep(.25)
    except (AttributeError, OSError, RuntimeError) as exc:
        # Optional performance tuning must never prevent the app from launching.
        print(json.dumps({'status': 'skipped', 'reason': str(exc)}), flush=True)


if __name__ == '__main__':
    main()
