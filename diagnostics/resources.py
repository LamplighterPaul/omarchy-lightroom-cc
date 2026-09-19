#!/usr/bin/env python3
"""Sample one Wine prefix's CPU and memory without recording process arguments."""
import argparse
import json
import os
from pathlib import Path
import time


def drm_fdinfo(process):
    """Skip event/timer/ntsync descriptors before asking drivers for fdinfo.

    Enumerate anew each sample so newly opened GPU devices are included. A
    descriptor can disappear or be reused during the scan; the subsequent
    drm-client-id check still rejects non-DRM fdinfo in that case.
    """
    for fd in (process / 'fd').iterdir():
        try:
            if os.readlink(fd).startswith('/dev/dri/'):
                yield process / 'fdinfo' / fd.name
        except OSError:
            continue


def snapshot(prefix, include_pss=True):
    result = {}
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            value = next((v.split(b'=', 1)[1] for v in (proc / 'environ').read_bytes().split(b'\0')
                          if v.startswith(b'WINEPREFIX=')), None)
            if value is None or Path(os.fsdecode(value)).resolve() != prefix:
                continue
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            memory = {'Rss': int(stat[21]) * os.sysconf('SC_PAGE_SIZE') // 1024}
            if include_pss:
                for line in (proc / 'smaps_rollup').read_text().splitlines()[1:]:
                    key, value = line.split(':', 1)
                    memory[key] = int(value.split()[0])
            gpu_kib = 0
            engines = {}
            clients = set()
            for fd in drm_fdinfo(proc):
                try:
                    fields = dict(line.split(':', 1) for line in fd.read_text().splitlines() if ':' in line)
                    client = fields.get('drm-client-id')
                    if not client or client in clients:
                        continue
                    clients.add(client)
                    device = fields.get('drm-pdev', '').strip()
                    for key, value in fields.items():
                        if key.startswith('drm-cycles-'):
                            engine = key.removeprefix('drm-cycles-')
                            total = fields.get('drm-total-cycles-' + engine)
                            if total:
                                engines[f'{device}/{client.strip()}/{engine}'] = [int(value), int(total)]
                        elif key.startswith('drm-engine-') and value.strip().endswith('ns'):
                            engine = key.removeprefix('drm-engine-')
                            engines[f'{device}/{client.strip()}/{engine}'] = [int(value.split()[0]), time.monotonic_ns()]
                    for key in ('drm-resident-gtt', 'drm-resident-system', 'drm-resident-vram'):
                        value = fields.get(key, '0 KiB').split()
                        gpu_kib += int(value[0]) * (1024 if value[1:] == ['MiB'] else 1)
                except (OSError, ValueError):
                    continue
            result[int(proc.name)] = dict(name=(proc / 'comm').read_text().strip(),
                ticks=int(stat[11]) + int(stat[12]), start=int(stat[19]),
                rss_kib=memory['Rss'], pss_kib=memory.get('Pss'), gpu_kib=gpu_kib,
                engines=engines)
        except (OSError, ValueError, IndexError):
            continue
    return result


def sample(prefix, seconds):
    before = snapshot(prefix)
    start = time.monotonic()
    time.sleep(seconds)
    after = snapshot(prefix)
    elapsed = time.monotonic() - start
    hz = os.sysconf('SC_CLK_TCK')
    rows = []
    for pid, item in after.items():
        prior = before.get(pid)
        cpu = None
        if prior and prior['start'] == item['start']:
            cpu = round((item['ticks'] - prior['ticks']) / hz / elapsed * 100, 2)
        rows.append(dict(pid=pid, name=item['name'], cpu_percent=cpu,
                         rss_mib=round(item['rss_kib'] / 1024, 1),
                         pss_mib=round(item['pss_kib'] / 1024, 1),
                         gpu_resident_mib=round(item['gpu_kib'] / 1024, 1)))
    return dict(seconds=round(elapsed, 2), cpu_percent=sum(r['cpu_percent'] or 0 for r in rows),
        rss_mib=round(sum(v['rss_kib'] for v in after.values()) / 1024, 1),
        pss_mib=round(sum(v['pss_kib'] for v in after.values()) / 1024, 1),
        gpu_resident_mib=round(sum(v['gpu_kib'] for v in after.values()) / 1024, 1),
        exited_processes=len(set(before) - set(after)),
        note='100% CPU = one core. CPU covers surviving processes; PSS apportions shared pages. GPU allocations may overlap CPU memory and other clients; do not add them to PSS.',
        processes=sorted(rows, key=lambda r: r['pss_mib'], reverse=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 60:
        parser.error('--seconds must be between 1 and 60')
    print(json.dumps(sample(args.prefix.expanduser().resolve(), args.seconds), indent=2))
