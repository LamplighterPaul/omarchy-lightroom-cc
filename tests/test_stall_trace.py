import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('stall_trace', Path(__file__).resolve().parents[1]/'diagnostics/stall-trace.py')
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class StallTraceTest(unittest.TestCase):
    def sample(self, start=1, runtime=10_000_000, delay=4_000_000):
        return dict(start=start, runtime=runtime, delay=delay, state='S', wait='futex_wait_queue', slices=10)

    def test_disabled_schedstats_is_not_reported_as_zero_wait(self):
        rows = trace.thread_deltas({1:self.sample()}, {1:self.sample(runtime=12_000_000)}, False)
        self.assertEqual(rows[0]['cpu_ms'], 2)
        self.assertNotIn('runqueue_ms', rows[0])

    def test_enabled_scheduler_delay_is_independent_of_cpu_time(self):
        rows = trace.thread_deltas({1:self.sample()}, {1:self.sample(runtime=11_000_000, delay=24_000_000)}, True)
        self.assertEqual(rows[0]['cpu_ms'], 1)
        self.assertEqual(rows[0]['runqueue_ms'], 20)

    def test_reused_tid_does_not_produce_false_spike(self):
        self.assertEqual(trace.thread_deltas({1:self.sample()}, {1:self.sample(start=2)}, True), [])

    def test_counter_reset_is_discarded(self):
        self.assertEqual(trace.thread_deltas({1:self.sample()}, {1:self.sample(runtime=0)}, True), [])
