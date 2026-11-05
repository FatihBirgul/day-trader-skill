import unittest
from forex.core import DataError, indicators, scanner, ema

class Indicators(unittest.TestCase):
    def test_reference_rsi_and_flat(self):
        closes=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,
                45.89,46.03,45.61,46.28,46.28,46.00,46.03,46.41,46.22,45.64,
                46.21,46.25,45.71,46.45,45.78,45.35,44.03,44.18,44.22,44.57,
                43.42,42.66,43.13]
        self.assertAlmostEqual(scanner.rsi(closes[:15]),70.46,places=1)
        self.assertEqual(scanner.rsi([1]*20),50)
    def test_constant_series_and_insufficient(self):
        bars=[{'high':2,'low':.5,'close':1,'open':1} for _ in range(220)]
        m=indicators(bars)
        self.assertEqual(m['ema200'],1)
        self.assertAlmostEqual(m['macd_histogram'],0)
        self.assertEqual(m['rsi14'],50)
        self.assertAlmostEqual(m['atr14'],1.5)
        with self.assertRaises(DataError): indicators(bars[:199])
