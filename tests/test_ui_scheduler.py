import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'diagnostics/ui-scheduler.py'
spec = importlib.util.spec_from_file_location('ui_scheduler', SOURCE)
hint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hint)


class SchedulerTest(unittest.TestCase):
    def test_capacity_detection_requires_supported_asymmetry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for cpu, capacity in ((0, 1024), (1, 676)):
                (root / f'cpu{cpu}').mkdir()
                (root / f'cpu{cpu}/cpu_capacity').write_text(str(capacity))
            self.assertTrue(hint.hybrid_capacity({0, 1}, root))
            self.assertFalse(hint.hybrid_capacity({0}, root))
            self.assertFalse(hint.hybrid_capacity({0, 2}, root))

    def test_target_requires_selected_prefix_executable_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc, prefix, runtime = root / 'proc', root / 'prefix', root / 'runtime'
            proc.mkdir()
            (proc / 'comm').write_text('lightroom.exe\n')
            (proc / 'environ').write_bytes(b'WINEPREFIX=' + os.fsencode(prefix) + b'\0')
            paths = [prefix / 'drive_c/Program Files/Adobe/Adobe Lightroom CC/lightroom.exe',
                     runtime / 'lib/wine/x86_64-unix/ntdll.so']
            maps = '\n'.join(f'1000-2000 r--p 00000000 00:00 1 {path}' for path in paths)
            (proc / 'maps').write_text(maps)
            self.assertTrue(hint.matches(proc, prefix, runtime))
            self.assertFalse(hint.matches(proc, root / 'other-prefix', runtime))
            self.assertFalse(hint.matches(proc, prefix, root / 'other-runtime'))
            (proc / 'maps').write_text(maps.splitlines()[1])
            self.assertFalse(hint.matches(proc, prefix, runtime))

    def test_custom_scheduling_is_preserved(self):
        from unittest.mock import Mock
        libc = Mock()
        for policy, minimum, maximum in ((0, 128, 1024), (0, 0, 512), (1, 0, 1024)):
            attr = hint.SchedAttr(policy=policy, util_min=minimum, util_max=maximum)
            with patch.object(hint, 'hybrid_capacity', return_value=True), \
                 patch.object(hint, 'get_attr', return_value=attr):
                self.assertEqual(hint.apply_hint(libc, os.getpid())['status'], 'skipped')
        libc.sched_setattr.assert_not_called()

    @unittest.skipUnless(sys.platform == 'linux', 'Linux scheduling API')
    def test_native_worker_does_not_inherit_boost_or_cpu_restriction(self):
        # Use a disposable process: an unprivileged thread cannot clear its
        # reset-on-fork flag after setting it. Never change the test runner.
        program = '''
import importlib.util,json,os,threading,sys
s=importlib.util.spec_from_file_location('hint',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
try:l=m.scheduler();before=m.get_attr(l,0)
except (AttributeError,OSError):sys.exit(77)
if before.policy or before.util_min or before.util_max!=1024:sys.exit(77)
m.hybrid_capacity=lambda _:True
allowed=sorted(os.sched_getaffinity(0));result=m.apply_hint(l,os.getpid());children=[]
def child():
 a=m.get_attr(l,0);children.append(dict(min=a.util_min,max=a.util_max,flags=a.flags,cpus=sorted(os.sched_getaffinity(0))))
t=threading.Thread(target=child);t.start();t.join()
print(json.dumps(dict(result=result,allowed=allowed,children=children)))
'''
        result = subprocess.run([sys.executable, '-c', program, str(SOURCE)],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 77:
            self.skipTest('No supported default scheduling API')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)
        self.assertEqual(state['result']['status'], 'applied')
        self.assertEqual(state['result']['allowed_cpus'], state['allowed'])
        self.assertEqual(state['children'], [{'min': 0, 'max': 1024, 'flags': 0, 'cpus': state['allowed']}])
