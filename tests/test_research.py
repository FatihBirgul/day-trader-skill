import unittest
from forex.research import strategy_backtest
from forex.core import DataError

def series(n=280):
    rows=[]
    for i in range(n):
        c=100+i*.1+(2 if i%12==0 else 0)
        rows.append({'time':1000+i*900,'open':c-.1,'high':c+.3,'low':c-.3,'close':c})
    return rows

class Research(unittest.TestCase):
    def test_deterministic_and_chronological(self):
        bars=series();a=strategy_backtest(bars,.02,seed=7);b=strategy_backtest(bars,.02,seed=7)
        self.assertEqual(a,b)
        self.assertEqual(a['policy'],'stop_first')
        for t in a['trades']:
            self.assertLessEqual(t['entry_index'],t['exit_index'])
            self.assertEqual(t['entry_time'],bars[t['entry_index']]['time'])
    def test_bad_data_rejected(self):
        bars=series();bars[10]['time']=bars[9]['time']
        with self.assertRaises(DataError): strategy_backtest(bars,.02)

class ResearchAPI(unittest.TestCase):
    def test_request_limit(self):
        from fastapi.testclient import TestClient
        from forex.api import app
        client=TestClient(app)
        self.assertEqual(client.post('/api/v1/strategy-backtests',json={
            'symbol':'XAUUSD','count':2001,'spread':.1}).status_code,422)
    def test_multiple_trades_and_holdout(self):
        result=strategy_backtest(series(),.02)
        self.assertGreater(result['metrics']['trade_count'],1)
        self.assertEqual(result['metrics']['trade_count'],len(result['trades']))
        self.assertEqual(result['development']['trade_count']+result['holdout']['trade_count'],
                         result['metrics']['trade_count'])
        self.assertTrue(all(t['entry_index']>=200 for t in result['trades']))

class GapPolicy(unittest.TestCase):
    def test_adverse_gap_can_exceed_one_r(self):
        from unittest.mock import patch
        from forex import research
        bars=series()
        original=research.candidates
        def one_signal(prefix,metrics):
            return [{'strategy':'trend_following','direction':'BUY','reason':'test'}] if len(prefix)==200 else []
        with patch.object(research,'candidates',side_effect=one_signal):
            bars[201].update(open=50,high=51,low=49,close=50)
            result=research.strategy_backtest(bars,.02)
        self.assertLess(result['trades'][0]['r'],-1)
