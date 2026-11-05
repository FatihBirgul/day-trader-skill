import json
from pathlib import Path
import unittest
from forex.core import indicators, scanner

GOLDEN=json.loads((Path(__file__).parent/'fixtures/forex-v5/indicator-golden.json').read_text())


class IndependentGolden(unittest.TestCase):
    def test_wilder_closed_form_with_warmup(self):
        closes=list(range(100,115))+list(range(113,99,-1))
        self.assertAlmostEqual(scanner.rsi(closes),GOLDEN['rsi_wilder']['expected'],places=10)
        self.assertIsNone(scanner.rsi(closes[:14]))
        self.assertEqual(scanner.rsi(closes[:15]),100)

    def test_linear_seed_macd_atr_and_population_bands(self):
        rows=[dict(open=float(c),high=float(c+1),low=float(c-1),close=float(c)) for c in range(1,221)]
        metrics=indicators(rows)
        for key,value in GOLDEN['linear'].items():
            if key in ('construction','derivation'): continue
            with self.subTest(indicator=key):
                self.assertAlmostEqual(metrics[key],value,places=10)
