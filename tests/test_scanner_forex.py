import unittest
from fastapi.testclient import TestClient
from forex.api import app
from forex.scanner import scan
from forex.strategies import candidates,resolve
from test_forex import fixture,NOW

class Scanner(unittest.TestCase):
    def test_votes_and_result(self):
        p=fixture();result=scan(p,['XAUUSD'],['M15'],now=NOW)
        self.assertEqual(result['results'][0]['signal'],'BUY')
        self.assertTrue(result['results'][0]['strategies'])
    def test_conflict(self):
        direction,reasons=resolve([{'direction':'BUY','strategy':'a'},{'direction':'SELL','strategy':'b'}],'BUY')
        self.assertEqual(direction,'WAIT')
    def test_partial_failure_and_api(self):
        p=fixture(); result=scan(p,['EURUSD','XAUUSD'],['M15'],now=NOW)
        self.assertEqual(len(result['errors']),1)
        self.assertEqual(len(result['results']),1)
        app.state.provider=p
        client=TestClient(app)
        self.assertEqual(client.get('/api/v1/strategies').status_code,200)
        self.assertEqual(client.get('/api/v1/scanner?symbols=XAUUSD').status_code,200)
        self.assertEqual(client.get('/api/v1/scanner?symbols=BAD').status_code,422)
        app.state.provider=None

class PullbackTiming(unittest.TestCase):
    def test_prior_touch_uses_prior_ema(self):
        from unittest.mock import patch
        from forex import strategies
        bars=[{'open':100,'high':101,'low':99,'close':100} for _ in range(30)]
        bars[-2]={'open':101,'high':102,'low':100.5,'close':101}
        bars[-1]={'open':102,'high':104,'low':102,'close':103}
        metrics={'ema20':102,'ema50':100,'ema200':99,'rsi14':60,'macd':1,
                 'macd_signal':0}
        # Current EMA20 would make prev.low<=102 true. Prior EMA20 is near 100,
        # so this is not a valid touch of the previously known average.
        votes=strategies.candidates(bars,metrics)
        self.assertFalse(any(v['strategy']=='pullback' for v in votes))
