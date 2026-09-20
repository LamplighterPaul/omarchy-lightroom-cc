#!/usr/bin/env python3
"""Score input-to-content changes in private composited captures, offline.

Times are capture-completion observations, including readback and sampling delay.
This is not unobserved app latency or physical-display latency. Default region
assumes the 720x450 downsampled private fixture with a photo covering its center.
"""
import argparse
import csv
import json
from pathlib import Path
import re
import struct
import subprocess


def difference(a, b):
    if len(a) != len(b) or not a:
        raise ValueError('Region sizes differ or are empty')
    return sum(abs(x-y) for x, y in zip(a, b)) / len(a)


def blank_region(pixels):
    return sum(pixels[j:j+3] == b'\x1c\x1c\x1c' for j in range(0, len(pixels), 3)) > len(pixels)/3*.9


def score(pixels, frames, phases):
    times = [float(row['monotonic']) for row in frames]
    if len(pixels) != len(frames) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Frame count or monotonic timestamps invalid')
    if any(b['start_monotonic'] <= a['start_monotonic'] for a, b in zip(phases, phases[1:])):
        raise ValueError('Input phases are not ordered')
    result = []
    for i, phase in enumerate(phases):
        start = phase['start_monotonic']
        end = phases[i+1]['start_monotonic'] if i+1 < len(phases) else times[-1] + .001
        before = [n for n, t in enumerate(times) if t < start]
        active = [n for n, t in enumerate(times) if start <= t < end]
        if len(before) < 3 or len(active) < 3:
            raise ValueError('Insufficient baseline or transition capture window')
        baseline, target = pixels[before[-1]], pixels[active[-1]]
        row = {'action': phase['action'], 'input_monotonic': start,
               'baseline_frame': before[-1], 'target_frame': active[-1],
               'reference_difference': difference(baseline, target),
               'blank_region_samples': sum(blank_region(pixels[n]) for n in active)}
        if blank_region(baseline) or blank_region(target):
            row.update(status='unscored', reason='Baseline or final region is blank background')
        elif any(difference(pixels[n], baseline) >= 2 for n in before[-3:]):
            row.update(status='unscored', reason='Pre-input region not stable')
        elif any(difference(pixels[n], target) >= 2 for n in active[-3:]):
            row.update(status='unscored', reason='Final region not stable')
        elif row['reference_difference'] <= 10:
            row.update(status='unscored', reason='No distinct final image in region')
        else:
            distances = [difference(pixels[n], baseline) for n in active]
            final_distances = [difference(pixels[n], target) for n in active]
            first = next(n for n, d in zip(active, distances) if d > 5)
            settled = next(active[k] for k in range(len(active)-2)
                           if all(d < 2 for d in final_distances[k:]))
            row.update(status='scored', first_change_ms=(times[first]-start)*1000,
                       settled_ms=(times[settled]-start)*1000, first_frame=first,
                       settled_frame=settled)
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('images', type=Path)
    parser.add_argument('capture_csv', type=Path)
    parser.add_argument('phases_json', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--actions', default='zoom', help='Comma-separated actions to score')
    parser.add_argument('--region', default='160x160+270+100')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists')
    region = re.fullmatch(r'(\d+)x(\d+)\+(\d+)\+(\d+)', args.region)
    if not region:
        parser.error('Region must be WIDTHxHEIGHT+X+Y')
    width, height, left, top = map(int, region.groups())
    if not 0 < width <= 720 or not 0 < height <= 450:
        parser.error('Invalid region size')
    frames = list(csv.DictReader(args.capture_csv.read_text().splitlines()))
    if not 3 <= len(frames) <= 600:
        parser.error('Expected 3–600 captured frames')
    files = []
    for i, row in enumerate(frames):
        if int(row['frame']) != i:
            parser.error('Non-sequential capture frame IDs')
        path = (args.images / f'frame-{i:04d}.png').resolve()
        with path.open('rb') as stream:
            header = stream.read(24)
        if header[:8] != b'\x89PNG\r\n\x1a\n' or len(header) != 24:
            parser.error('Invalid PNG')
        w, h = struct.unpack('>II', header[16:24])
        if (w, h) != (720, 450) or left + width > w or top + height > h:
            parser.error('Expected 720x450 frames and an in-bounds region')
        files.append(path)
    raw = subprocess.check_output(['magick', *map(str, files), '-crop', args.region,
                                   '+repage', '-depth', '8', 'rgb:-'], timeout=60)
    size = width * height * 3
    if len(raw) != size * len(files):
        parser.error('Unexpected region byte count')
    pixels = [raw[n*size:(n+1)*size] for n in range(len(files))]
    actions = set(args.actions.split(','))
    phases = [p for p in json.loads(args.phases_json.read_text()) if p['action'] in actions]
    if not phases:
        parser.error('No matching input phases')
    result = {'region': args.region, 'change_threshold_mae': 5, 'settled_threshold_mae': 2,
              'note': 'Capture-completion timing, with observer overhead and sampling delay. Region-based, not whole-frame or physical-display latency.',
              'transitions': score(pixels, frames, phases)}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
