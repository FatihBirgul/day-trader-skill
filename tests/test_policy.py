import unittest
from datetime import datetime,timezone
from forex.policy import assess
from test_forex import META

NOW=datetime(2026,11,6,12,tzinfo=timezone.utc)
PLAN={'symbol':'XAUUSD','direction':'BUY','entry':2000,'stop_loss':1999,
      'take_profit_1':2002,'timeframe':'M15'}
class Policy(unittest.TestCase):
    def test_pass_and_duplicate(self):
        meta={**META,'spread':.2}
        result=assess(PLAN,meta,10000,1,now=NOW)
        self.assertEqual(result['decision'],'PASS')
        duplicate=assess(PLAN,meta,10000,1,records=[{'date':'2026-11-06',
                   'fingerprint':result['fingerprint']}],now=NOW)
        self.assertEqual(duplicate['decision'],'BLOCK')
    def test_daily_loss_and_open_limit(self):
        meta={**META,'spread':.2}
        result=assess(PLAN,meta,10000,1,records=[{'date':'2026-11-06',
                   'realized_loss':400,'status':'open'}],now=NOW)
        self.assertEqual(result['decision'],'BLOCK')
        self.assertIn('daily loss limit',result['reasons'])
        self.assertIn('position limit reached',result['reasons'])

class RiskBounds(unittest.TestCase):
    def test_negative_manual_loss_cannot_expand_budget(self):
        from forex.core import DataError
        with self.assertRaises(DataError): assess(PLAN,{**META,'spread':.2},10000,1,
            records=[{'date':'2026-11-06','planned_risk':-1000}],now=NOW)
    def test_stop_level_measured_from_executable_exit_side(self):
        from forex.core import risk_check
        meta={**META,'spread':.15,'stops_level':10,'point':.01}
        plan={**PLAN,'entry':100,'stop_loss':99.8,'take_profit_1':101}
        result=risk_check(plan,meta,.2)
        self.assertEqual(result['decision'],'BLOCK')
        self.assertIn('broker minimum stop distance after spread',result['reasons'])
