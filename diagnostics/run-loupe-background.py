#!/usr/bin/env python3
"""Run the GPU/GDI regression probe only on the owned private Weston fixture."""
import argparse
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expect', choices=['retained', 'baseline'], required=True)
parser.add_argument('--runtime', default='lightroom-omarchy-proton-threadpool-test')
args = parser.parse_args()
if os.environ.get('DISPLAY') != ':1' or os.environ.get('WAYLAND_DISPLAY') != 'lightroom-test':
    raise SystemExit('Refusing non-fixture display')
server = Path('/proc') / str(int(Path('/tmp/.X1-lock').read_text()))
command = (server/'cmdline').read_bytes().split(b'\0')
if b'--socket=lightroom-test' not in command:
    parent = int((server/'stat').read_text().rsplit(')', 1)[1].split()[1])
    command = (Path('/proc')/str(parent)/'cmdline').read_bytes().split(b'\0')
if b'--socket=lightroom-test' not in command or b'--backend=headless' not in command:
    raise SystemExit('Display :1 is not the owned private Weston')
active = json.loads(subprocess.check_output(['hyprctl', 'activewindow', '-j']))
if 'lightroom' in active.get('class', '').lower():
    raise SystemExit('Production Lightroom is in use; defer the probe')
if Path(args.runtime).name != args.runtime or args.runtime in ('.', '..'):
    raise SystemExit('Expected an application-local runtime name')
launcher = Path(__file__).resolve().parents[1]/'bin/omarchy-lightroom-cc'
loader = importlib.machinery.SourceFileLoader('lrcc', str(launcher))
spec = importlib.util.spec_from_loader('lrcc', loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
module.RUNNER = 'lightroom-omarchy-proton'
module.PROTON = True
module.PREFIX = module.DATA/'experiments/performance-headless/prefix'
module.RUNTIME = module.DATA/'runtimes'/args.runtime/'files'
os.environ['WINEDLLOVERRIDES'] = os.environ.get('WINEDLLOVERRIDES', '') + ';d3d11,dxgi=n'
os.environ.update(LRCC_DISPATCHED='1', LRCC_PRIVATE_FIXTURE='lightroom-test:1',
                  LIGHTROOM_OMARCHY_RETAIN_LOUPE='1' if args.expect == 'retained' else '0')
module.wine(module.DATA/'tools/loupe-background.exe', args.expect)
