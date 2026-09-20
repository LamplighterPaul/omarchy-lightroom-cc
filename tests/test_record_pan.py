import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('record_pan', Path(__file__).resolve().parents[1] / 'diagnostics/record-pan.py')
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


class PanRecordingTest(unittest.TestCase):
    def recording(self, frames='8.3,10000000\n120,2500000000\n8.4,5010000000\n'):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / 'lightroom_2026-09-20_02-07-01.csv'
        path.write_text('os,cpu\nTest,Test\nframetime,elapsed\n' + frames)
        epoch = recorder.datetime.datetime(2026, 9, 20, 2, 7, 1).timestamp()
        return path, {'start_epoch': epoch, 'end_epoch': epoch+.2, 'start_monotonic': 2}, \
            {'end_monotonic': 7.4}, {'start_monotonic': 1, 'end_monotonic': 11}

    def test_long_stalls_are_retained(self):
        result = recorder.summarize(*self.recording())
        self.assertEqual(result['samples'], 3)
        self.assertEqual(result['max_ms'], 120)
        self.assertEqual(result['over_33_33_ms'], 1)
        self.assertEqual(result['interior_0_5s_trim']['max_ms'], 120)

    def test_accidental_double_toggle_burst_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'sustained recording'):
            recorder.summarize(*self.recording(frames='8.3,10000000\n8.4,410000000\n'))

    def test_stale_recording_and_idle_toggle_are_rejected(self):
        path, start, stop, pan = self.recording()
        start['start_epoch'] += 60
        with self.assertRaisesRegex(ValueError, 'another recording'):
            recorder.summarize(path, start, stop, pan)
        path, start, stop, pan = self.recording()
        stop['end_monotonic'] = 12
        with self.assertRaisesRegex(ValueError, 'active gesture'):
            recorder.summarize(path, start, stop, pan)
