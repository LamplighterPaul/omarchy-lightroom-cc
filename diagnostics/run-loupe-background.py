#!/usr/bin/env python3
"""Run the GPU/GDI regression probe only on the owned private Weston fixture."""
import argparse
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import selectors
import time

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
# Exercise X11 PatBlt, the observed Lightroom path, rather than a synthetic
# parent's cached DIB. Scope this setting to the fixture executable only.
module.wine('reg', 'add', r'HKCU\Software\Wine\AppDefaults\loupe-background.exe\X11 Driver',
            '/v', 'ClientSideGraphics', '/t', 'REG_SZ', '/d', 'N', '/f',
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
output = module.DATA/'measurements/loupe-regression'/f'{time.time_ns()}-{args.expect}'
output.mkdir(parents=True)
env = module.environment()
env.update(PROTON_VERB='runinprefix', PROTON_LOG='0', DXVK_LOG_LEVEL='error',
           LRCC_CAPTURE_DIR='Z:'+str(output))
rows = []
# Each request is acknowledged through a file after sampling the compositor.
# Wine under UMU does not reliably forward stdin to this Windows helper.
with (output/'runtime.log').open('w') as log:
    child = subprocess.Popen([str(module.DATA/'tools/umu/umu-run'),
                              str(module.DATA/'tools/loupe-background.exe'), args.expect],
                             env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=log, text=True, bufsize=1)
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)
    deadline = time.monotonic()+120
    pending = b''
    try:
        while time.monotonic() < deadline:
            if b'\n' not in pending:
                if not selector.select(timeout=1):
                    continue
                chunk = os.read(child.stdout.fileno(), 8192)
                if not chunk:
                    break
                pending += chunk
                continue
            raw, _, pending = pending.partition(b'\n')
            line = raw.decode('utf-8', errors='replace').rstrip('\r')
            print(line.rstrip(), flush=True)
            if not line.startswith('CAPTURE '):
                continue
            _, name, x, y, r, g, b = line.split()
            frame = output/f'{len(rows):02}-{name}'
            frame.mkdir()
            time.sleep(0.3)  # settle; appearance check, never a frame-time claim
            subprocess.run([str(module.DATA/'tools/composited-capture'), str(frame), '1', '20'],
                           check=True, stdout=subprocess.DEVNULL, timeout=10)
            # composited-capture stores every fourth physical output pixel.
            pos = (int(x)//4, int(y)//4)
            actual = tuple(subprocess.check_output([
                'magick', str(frame/'frame-0000.png'), '-crop',
                f'1x1+{pos[0]}+{pos[1]}', '-depth', '8', 'rgb:-'], timeout=10))
            expected = tuple(map(int, (r, g, b)))
            passed = actual == expected
            rows.append(dict(name=name, position=pos, actual=actual, expected=expected, passed=passed))
            print(f'{"PASS" if passed else "FAIL"} {name} {actual} expected {expected}', flush=True)
            ack = output/f'{len(rows)-1}.ack'
            temporary = ack.with_suffix('.tmp')
            temporary.write_text('PASS\n' if passed else 'FAIL\n')
            temporary.replace(ack)
        if child.poll() is None:
            child.wait(timeout=5)
    finally:
        selector.close()
        if child.poll() is None:
            child.terminate()
        (output/'checks.json').write_text(json.dumps(rows, indent=2)+'\n')
print(f'Results: {output}')
raise SystemExit(child.returncode if len(rows)==21 else 2)
