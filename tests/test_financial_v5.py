import unittest
from forex.core import size_lots, DataError
from test_forex import META


class CostRisk(unittest.TestCase):
    def test_independent_cost_budget_buy_sell(self):
        # 100oz contract: $1 movement=$100/lot. $0.10 adverse stop
        # slippage adds $10/lot; round-trip commission adds $5/lot.
        # $100 budget / $115 = 0.86956; grid floor gives 0.86 lot/$98.90.
        for side, entry, stop in [('BUY', 2000, 1999), ('SELL', 2000, 2001)]:
            with self.subTest(side=side):
                result = size_lots(10000, 1, entry, stop, META, side=side,
                                   commission_per_lot=5, slippage_price=.1)
                self.assertEqual(result['lots'], .86)
                self.assertAlmostEqual(result['estimated_risk'], 98.9)

    def test_positive_final_broker_profit_cannot_hide_behind_commission(self):
        calls = []
        def inconsistent(side, lots, entry, stop):
            calls.append(lots)
            return -1 if len(calls) == 1 else .001
        with self.assertRaisesRegex(DataError, 'stop-loss loss'):
            size_lots(10000, 1, 2000, 1999, META, inconsistent, commission_per_lot=100)

    def test_broker_receives_stop_execution_price_and_cost_grid(self):
        seen = []
        def profit(side, lots, entry, stop):
            seen.append(stop)
            return (stop-entry)*(1 if side == 'BUY' else -1)*100*lots
        result = size_lots(10000, 1, 2000, 1999, META, profit,
                           commission_per_lot=5, slippage_price=.1)
        self.assertTrue(all(abs(stop-1998.9)<1e-8 for stop in seen))
        self.assertEqual(result['lots'], .86)
        self.assertLessEqual(result['estimated_risk'], 100)

    def test_minimum_currency_and_nonfinite_costs(self):
        with self.assertRaises(DataError): size_lots(10, 1, 2000, 1999, META, commission_per_lot=5)
        with self.assertRaises(DataError): size_lots(10000, 1, 2000, 1999, META, account_currency='EUR')
        for cost in (-1, float('nan'), float('inf')):
            with self.assertRaises(DataError): size_lots(10000, 1, 2000, 1999, META, commission_per_lot=cost)

    def test_daily_policy_uses_unrounded_risk(self):
        from forex.policy import assess
        from datetime import datetime, timezone
        now=datetime(2026,11,6,12,tzinfo=timezone.utc)
        plan={'symbol':'XAUUSD','timeframe':'M15','direction':'BUY','entry':2000,
              'stop_loss':1999.98999,'take_profit_1':2000.03}
        meta={**META,'stops_level':0,'spread':0}
        result=assess(plan,meta,100,1,[{'date':'2026-11-06','planned_risk':2.0095}],now=now)
        self.assertEqual(result['decision'],'BLOCK')
        self.assertIn('daily planned risk limit',result['reasons'])

    def test_risk_plan_prices_grid_and_metadata(self):
        from forex.core import risk_check
        plan={'direction':'BUY','entry':2000,'stop_loss':1999,'take_profit_1':2002,'take_profit_2':2003}
        meta={**META,'spread':.2}
        self.assertEqual(risk_check(plan,meta,1)['decision'],'PASS')
        for modified,metadata,limit in (({**plan,'take_profit_1':-1},meta,1),
                                        ({**plan,'take_profit_2':2001},meta,1),
                                        ({**plan,'stop_loss':1999.005},meta,1),
                                        (plan,{**meta,'stops_level':-1},1),
                                        (plan,meta,float('nan'))):
            self.assertEqual(risk_check(modified,metadata,limit)['decision'],'BLOCK')

    def test_broker_trade_modes_and_direction_permissions(self):
        from forex.providers import MT5Provider
        from forex.core import risk_check
        from test_forex import FakeMT5
        class ModeMT5(FakeMT5):
            mode=3
            def symbol_info(self,symbol):
                info=super().symbol_info(symbol)
                info.trade_mode=self.mode
                return info
            def account_info(self):
                from types import SimpleNamespace
                return SimpleNamespace(currency='USD',trade_allowed=True)
        terminal=ModeMT5();provider=MT5Provider(terminal,{'XAUUSD':'XAUUSD.r'})
        for mode,allowed in ((0,[]),(1,['BUY']),(2,['SELL']),(3,[]),(4,['BUY','SELL'])):
            terminal.mode=mode
            meta=provider.metadata('XAUUSD')
            self.assertEqual(meta['allowed_directions'],allowed)
            self.assertEqual(meta['trade_allowed'],bool(allowed))
        plan={'direction':'BUY','entry':2000,'stop_loss':1999,'take_profit_1':2002}
        result=risk_check(plan,{**META,'spread':.2,'allowed_directions':['SELL']},1)
        self.assertIn('broker direction not permitted',result['reasons'])
        with self.assertRaises(DataError):provider.loss_for('XAUUSD','INVALID',1,2000,1999)
