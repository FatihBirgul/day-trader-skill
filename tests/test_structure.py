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

class StructureCloseTime(unittest.TestCase):
    def test_first_knowledge_is_confirmation_close(self):
        rows=[{'time':1000+i*900,'high':h,'low':1,'close':1.5} for i,h in enumerate([2,3,5,3,2,2,3,6,3,2])]
        result=market_structure(rows,timeframe_seconds=900)
        pivot=result['last_high']
        self.assertEqual(pivot['formed_at'],rows[7]['time']+900)
        self.assertEqual(pivot['first_detectable_at'],rows[9]['time']+900)
        self.assertEqual(pivot['confirmed_at'],rows[9]['time']+900)

    def test_structure_break_is_not_repeated(self):
        # Strict 2/2 pivot at 5; first closed cross is an event, next bar is not.
        prices=[(2,1.5),(3,2),(5,3),(3,2),(2,1.5),(2,1.5),(6,5.5),(7,6)]
        rows=[{'time':1000+i*900,'high':h,'low':1,'close':c} for i,(h,c) in enumerate(prices)]
        self.assertEqual(market_structure(rows[:-1],timeframe_seconds=900)['break_of_structure'],'BUY')
        self.assertIsNone(market_structure(rows,timeframe_seconds=900)['break_of_structure'])
