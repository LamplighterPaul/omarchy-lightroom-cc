#!/usr/bin/env python3
"""Build the monitor scale API fix from pinned Wine source, without installing it."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('LRCC_DATA', Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'omarchy-lightroom-cc')).expanduser().resolve()
SOURCE = DATA / 'build/wine-11.10'
BUILD = DATA / 'build/shcore'
COMMIT = '2cac6ccf33c0807f374dc96f5a20e35a2da86157'
PATCH = REPO / 'patches/shcore-monitor-scale.patch'
env = os.environ.copy()
env['PATH'] = str(DATA / 'tools/usr/bin') + ':' + env['PATH']

def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, env=env, **kw)

for tool in ('git', 'make', 'gcc', 'x86_64-w64-mingw32-gcc', 'flex', 'bison'):
    if not shutil.which(tool, path=env['PATH']):
        raise SystemExit(f'Missing build dependency: {tool}')
if not SOURCE.exists():
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    run(['git', 'clone', '--depth', '1', '--branch', 'wine-11.10', '--single-branch',
         'https://github.com/wine-mirror/wine.git', SOURCE])
if subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() != COMMIT:
    raise SystemExit('Wine source revision mismatch')
reverse = subprocess.run(['git', '-C', str(SOURCE), 'apply', '--reverse', '--check', str(PATCH)],
                         capture_output=True)
if reverse.returncode:
    run(['git', '-C', SOURCE, 'apply', '--check', PATCH])
    run(['git', '-C', SOURCE, 'apply', PATCH])
BUILD.mkdir(parents=True, exist_ok=True)
with (BUILD / 'build.log').open('w') as log:
    if not (BUILD / 'Makefile').exists():
        run([SOURCE / 'configure', '--enable-archs=x86_64', '--without-x', '--without-freetype'],
            cwd=BUILD, stdout=log, stderr=log)
    for target in ('__tooldeps__', 'dlls/shcore/x86_64-windows/shcore.dll'):
        run(['make', '-j8', target], cwd=BUILD, stdout=log, stderr=log)
output = DATA / 'patches/shcore.dll'
output.parent.mkdir(parents=True, exist_ok=True)
data = bytearray((BUILD / 'dlls/shcore/x86_64-windows/shcore.dll').read_bytes())
marker = b'Wine builtin DLL'
if data.find(marker) != 0x40:
    raise SystemExit('Unexpected Wine PE header')
# Permit a native override of our Wine-built replacement component.
data[0x40:0x40 + len(marker)] = bytes(len(marker))
output.write_bytes(data)
metadata = {'wine_commit': COMMIT, 'patch_sha256': hashlib.sha256(PATCH.read_bytes()).hexdigest(),
            'dll_sha256': hashlib.sha256(data).hexdigest(), 'monitor_scale_api': True}
output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
print(f'Built {output}; not installed. Log: {BUILD / "build.log"}')
