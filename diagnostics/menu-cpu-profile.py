#!/usr/bin/env python3
"""Attribute perf instruction samples inside serial menu input-to-map intervals.

Record with --clockid mono. Export with perf script --ns -F
time,event,period,ip,sym,dso. Supply /proc/PID/maps saved for that same process.
Wine can map PE code anonymously: resolve its module using the file-backed PE
header and SizeOfImage, without guessing function names from distant exports.
This reports sampled instruction locations, not inclusive stacks or frame rate.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import struct


def pe_modules(maps):
    modules = []
    for line in maps.read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or int(fields[2], 16) != 0:
            continue
        path = Path(fields[5])
        if path.suffix.lower() not in ('.exe', '.dll'):
            continue
        with path.open('rb') as source:
            dos = source.read(64)
            if dos[:2] != b'MZ' or len(dos) != 64:
                raise ValueError(f'Invalid PE header: {path.name}')
            source.seek(struct.unpack_from('<I', dos, 60)[0])
            nt = source.read(88)
        if nt[:4] != b'PE\0\0' or len(nt) != 88:
            raise ValueError(f'Invalid PE header: {path.name}')
        base = int(fields[0].split('-')[0], 16)
        size = struct.unpack_from('<I', nt, 80)[0]
        if not size:
            raise ValueError(f'Empty PE image: {path.name}')
        modules.append((base, base + size, path.name))
    modules.sort()
    if any(a[1] > b[0] for a, b in zip(modules, modules[1:])):
        raise ValueError('Overlapping PE image ranges')
    return modules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples', type=Path)
    parser.add_argument('menus', type=Path)
    parser.add_argument('maps', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    menus = json.loads(args.menus.read_text())
    if menus['status'] != 'complete':
        parser.error('menu sequence is incomplete')
    windows = [(r['phase']['start_monotonic'], r['map']['monotonic'])
               for r in menus['openings']]
    if (not windows or any(b < a for a, b in windows)
            or any(a[1] > b[0] for a, b in zip(windows, windows[1:]))):
        parser.error('invalid or overlapping menu intervals')
    modules = pe_modules(args.maps)
    pattern = re.compile(r'\s*([\d.]+):\s+(\d+)\s+(\S+):\s+([0-9a-f]+) (.*) \((.*)\)$')
    counts, symbols, buckets = Counter(), Counter(), Counter()
    per_event = defaultdict(Counter)
    total, selected, per_opening = 0, 0, Counter()
    for line in args.samples.read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise ValueError(f'Unrecognized perf sample: {line[:120]}')
        timestamp, period, event, address, symbol, dso = match.groups()
        timestamp, address = float(timestamp), int(address, 16)
        total += 1
        opening = next((i for i, (a, b) in enumerate(windows) if a <= timestamp <= b), None)
        if opening is None:
            continue
        selected += 1
        per_opening[opening] += 1
        module = next(((a, name) for a, b, name in modules if a <= address < b), None)
        name = module[1] if module else Path(dso).name
        counts[name] += 1
        per_event[event][name] += 1
        # PE symbols from perf may be unavailable. Only retain symbols that perf
        # actually supplied, never label a whole address range by nearest export.
        if symbol != '[unknown]':
            symbols[f'{name}!{symbol}'] += 1
        if module:
            buckets[f'{name}+0x{(address-module[0])//256*256:x}'] += 1
    if not selected:
        raise ValueError('No samples overlap menu intervals; check PID and clock')
    result = {
        'note': 'Main-thread sampled IP counts, not inclusive stacks, CPU-time percentages or visible latency. Hybrid PMU events also reported separately.',
        'total_samples': total, 'selected_samples': selected,
        'openings': len(windows), 'samples_per_opening': [per_opening[i] for i in range(len(windows))],
        'modules': [{'module': name, 'samples': n, 'sample_percent': n/selected*100}
                    for name, n in counts.most_common()],
        'events': {event: dict(counter.most_common()) for event, counter in per_event.items()},
        'known_symbols': dict(symbols.most_common(40)),
        'pe_rva_256byte_buckets': dict(buckets.most_common(40)),
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'selected_samples': selected, 'modules': result['modules'][:8]}, indent=2))


if __name__ == '__main__':
    main()
