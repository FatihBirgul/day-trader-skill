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
