import unittest
from forex.microstructure import executable_prices,exit_on_bar
from forex.core import DataError,backtest

class Microstructure(unittest.TestCase):
    def test_bid_buy_and_sell(self):
        buy=executable_prices('BUY',100,99,102,.2)
        sell=executable_prices('SELL',100,101,98,.2)
        self.assertAlmostEqual(buy['entry'],100.2)
        self.assertAlmostEqual(buy['risk'],1.2)
        self.assertAlmostEqual(sell['entry'],100)
        self.assertAlmostEqual(sell['stop_exit'],101.2)
        self.assertAlmostEqual(sell['risk'],1.2)
        self.assertAlmostEqual(exit_on_bar(buy,{'open':100,'high':102,'low':100})['net_r'],1.8/1.2)
        self.assertAlmostEqual(exit_on_bar(sell,{'open':100,'high':100,'low':98})['net_r'],1.8/1.2)
    def test_stop_first_and_gap(self):
        buy=executable_prices('BUY',100,99,102,.2)
        self.assertEqual(exit_on_bar(buy,{'open':100,'high':103,'low':98})['outcome'],'stop')
        self.assertLess(exit_on_bar(buy,{'open':98,'high':99,'low':97})['net_r'],-1)
        sell=executable_prices('SELL',100,101,98,.2)
        self.assertLess(exit_on_bar(sell,{'open':102,'high':103,'low':101})['net_r'],-1)
    def test_mid_and_unknown(self):
        m=executable_prices('BUY',100,99,102,.2,'mid')
        self.assertAlmostEqual(m['entry'],100.1)
        with self.assertRaises(DataError): executable_prices('BUY',100,99,102,.2,'unknown')
    def test_single_trade_spread_and_basis(self):
        bars=[{'open':100,'high':100,'low':100,'close':100},
              {'open':100,'high':102,'low':100,'close':101}]
        a=backtest(bars,'BUY',100,99,102,0)
        b=backtest(bars,'BUY',100,99,102,.2)
        self.assertGreater(a['result_r'],b['result_r'])
        self.assertEqual(b['price_basis'],'bid')
