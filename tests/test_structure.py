import unittest
from forex.structure import market_structure
from forex.core import DataError

class Structure(unittest.TestCase):
    def test_pivot_waits_for_right_candles(self):
        highs=[1,2,5,2,1,1,2,6,2,1]
        bars=[{'time':i+1,'high':h,'low':1,'close':1.5} for i,h in enumerate(highs)]
        result=market_structure(bars,left=2,right=2)
        self.assertEqual(result['confirmed_highs'],2)
        self.assertEqual(result['last_high']['detected_at'],8)
        self.assertEqual(result['last_high']['confirmed_at'],10)
        self.assertLessEqual(result['last_high']['confirmed_at'],bars[-1]['time'])
    def test_future_pivot_not_visible(self):
        highs=[1,2,5,2,1,1,2,6,2,1]
        bars=[{'time':i+1,'high':h,'low':1,'close':1.5} for i,h in enumerate(highs)]
        self.assertEqual(market_structure(bars[:-2])['confirmed_highs'],1)
    def test_bad_order(self):
        bars=[{'time':i,'high':2,'low':1,'close':1.5} for i in range(8)]
        bars[-1]['time']=bars[-2]['time']
        with self.assertRaises(DataError): market_structure(bars)
