#!/usr/bin/env python3
"""Stage/start a private GPU-backed Weston test display, without desktop input."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
from resources import snapshot

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['stage', 'clone', 'start'])
parser.add_argument('--capture', action='store_true',
                    help='Enable composited screenshots on this private test display.')
args = parser.parse_args()
data = Path(os.environ.get('LRCC_DATA', Path.home()/'.local/share/omarchy-lightroom-cc')).resolve()
root = data/'tools/weston/usr'
state = data/'headless'
state.mkdir(parents=True, exist_ok=True)

if args.action == 'stage':
    packages = json.loads(Path(__file__).with_name('headless-packages.json').read_text())
    for package in packages:
        archive = data/'cache'/package['filename']
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            partial = archive.with_suffix('.partial')
            with urllib.request.urlopen(package['url'], timeout=30) as source, partial.open('wb') as target:
                shutil.copyfileobj(source, target)
            partial.replace(archive)
        with archive.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != package['sha256']:
                raise SystemExit(f'Checksum mismatch: {archive.name}')
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['bsdtar', '-xf', archive, '-C', root.parent, 'usr'], check=True)
    print('Staged application-local Weston; no system packages or desktop configuration changed.')
elif args.action == 'clone':
    source = data/'experiments/lightroom-omarchy-proton'
    target = data/'experiments/performance-headless'
    if snapshot((source/'prefix').resolve()):
        raise SystemExit('Close Lightroom, stop its prefix, and wait for its server before cloning.')
    if target.exists():
        raise SystemExit('The test prefix already exists; it was not replaced.')
    target.mkdir()
    subprocess.run(['cp', '-a', '--reflink=auto', source/'prefix', target/'prefix'], check=True)
    shutil.copy2(source/'profile.json', target/'profile.json')
    print('Cloned stopped prefix for non-destructive interaction tests.')
else:
    if Path('/tmp/.X1-lock').exists() or Path('/tmp/.X11-unix/X1').exists():
        raise SystemExit('Display :1 is occupied; refusing to affect its server.')
    config = state/'weston.ini'
    config.write_text(f'''[core]
idle-time=0
xwayland=true
[shell]
client={root}/lib/weston/weston-desktop-shell
panel-position=none
animation=none
startup-animation=none
focus-animation=none
[input-method]
path={root}/lib/weston/weston-keyboard
''')
    env = os.environ.copy()
    env.update(LD_LIBRARY_PATH=f'{root}/lib:{root}/lib/weston', WESTON_DATA_DIR=str(root/'share/weston'))
    modules = {'headless-backend.so':'libweston-15', 'gl-renderer.so':'libweston-15',
               'desktop-shell.so':'weston', 'xwayland.so':'libweston-15'}
    env['WESTON_MODULE_MAP'] = ';'.join(f'{name}={root}/lib/{directory}/{name}' for name,directory in modules.items())
    binary = root/'bin/weston'
    command = [str(binary), '--backend=headless', '--renderer=gl', '--socket=lightroom-test',
               '--width=2880', '--height=1800', '--refresh-rate=120000', '--no-xwm-decorations',
               f'--config={config}', f'--log={state / "weston.log"}']
    if args.capture:
        command += ['--debug', '--debug-scopes=log']
    os.execve(binary, command, env)
