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
