import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('transition', Path(__file__).resolve().parents[1] / 'diagnostics/transition-latency.py')
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)


class TransitionTest(unittest.TestCase):
    def score(self, values):
        pixels = [bytes([v] * 12) for v in values]
        frames = [{'monotonic': n * .1} for n in range(len(values))]
        return scorer.score(pixels, frames, [{'action': 'zoom', 'start_monotonic': .25}])[0]

    def test_first_change_and_final_settling_are_distinct(self):
        row = self.score([10, 10, 10, 10, 50, 100, 100, 100])
        self.assertEqual(row['status'], 'scored')
        self.assertAlmostEqual(row['first_change_ms'], 150)
        self.assertAlmostEqual(row['settled_ms'], 250)

    def test_frozen_image_and_blank_final_are_not_success(self):
        self.assertEqual(self.score([10] * 8)['status'], 'unscored')
        row = self.score([10, 10, 10, 28, 28, 28, 28, 28])
        self.assertEqual(row['status'], 'unscored')
        self.assertEqual(row['blank_region_samples'], 5)

    def test_unsettled_baseline_is_rejected(self):
        row = self.score([10, 50, 100, 100, 150, 150, 150, 150])
        self.assertEqual(row['status'], 'unscored')
        self.assertIn('Pre-input', row['reason'])
