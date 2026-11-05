import unittest
from types import SimpleNamespace
from forex.mt5_diagnostic import diagnose
from forex.providers import MT5Provider
from test_forex import FakeMT5

class Diagnostic(unittest.TestCase):
    def test_read_only_failure_report(self):
        class Healthy(FakeMT5):
            def terminal_info(self): return SimpleNamespace(connected=True,trade_allowed=True)
        p=MT5Provider(Healthy(),{'XAUUSD':'XAUUSD.r'})
        result=diagnose(p,['XAUUSD','EURUSD'])
        self.assertEqual(result['symbols']['XAUUSD']['status'],'OK')
        self.assertEqual(result['symbols']['EURUSD']['status'],'ERROR')
        p.close()
