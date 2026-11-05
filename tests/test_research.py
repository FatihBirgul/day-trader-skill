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

class StrategyComparison(unittest.TestCase):
    def test_comparison_counts_tags(self):
        result=strategy_backtest(series(),.02)
        for name,report in result['strategy_comparison'].items():
            self.assertEqual(report['metrics']['trade_count'],len(report['trades']))
            self.assertTrue(all(name in t['strategy'] for t in report['trades']))

class RollingEvaluation(unittest.TestCase):
    def test_chronological_windows(self):
        from forex.research import walk_forward
        result=walk_forward(series(300),.02,folds=2)
        self.assertEqual(len(result['folds']),2)
        for fold in result['folds']:
            self.assertLess(fold['train_end_index'],fold['test_start_index'])
            self.assertTrue(all(fold['test_start_index']<=t['entry_index']<=fold['test_end_index']
                                for t in fold['trades']))
    def test_future_candles_do_not_change_past_trades(self):
        short=strategy_backtest(series(260),.02)['trades']
        long=strategy_backtest(series(300),.02)['trades']
        self.assertEqual(short,[t for t in long if t['exit_index']<260])

class BootstrapDistribution(unittest.TestCase):
    def test_seed_stability_and_ordered_quantiles(self):
        from forex.research import _bootstrap
        trades=[{'r':x} for x in (2,-1,2,-1,-1,2)]
        a=_bootstrap(trades,7);b=_bootstrap(trades,7)
        self.assertEqual(a,b)
        self.assertLessEqual(a['p5_total_r'],a['median_total_r'])
        self.assertLessEqual(a['median_total_r'],a['p95_total_r'])
        self.assertGreaterEqual(a['worst_drawdown_r'],a['median_drawdown_r'])
        self.assertEqual(a['sample_size'],6)

class FoldIsolationV5(unittest.TestCase):
    def test_fold_starts_flat_and_never_inherits_training_position(self):
        from forex.research import walk_forward
        result=walk_forward(series(300),.02,folds=2)
        for fold in result['folds']:
            isolated=strategy_backtest(series(300)[:fold['test_end_index']+1],.02,compare=False,
                                        evaluation_start=fold['test_start_index'])
            self.assertEqual(fold['trades'],isolated['trades'])
            self.assertTrue(all(t['entry_index']>=fold['test_start_index'] for t in fold['trades']))

    def test_unfinished_timestamp_and_provenance(self):
        for field,value in (('time',True),('is_final',False)):
            rows=series();rows[12][field]=value
            with self.assertRaises(DataError): strategy_backtest(rows,.02)
        result=strategy_backtest(series(),.02)
        self.assertEqual(len(result['dataset_sha256']),64)
        self.assertFalse(result['forward_validated'])
        self.assertEqual(result['metrics']['equity_curve_r'][0],0)
        self.assertAlmostEqual(result['metrics']['equity_curve_r'][-1],result['metrics']['total_r'])
        self.assertIn('small empirical sample',result['monte_carlo']['warning'])
        self.assertLessEqual(result['monte_carlo']['p5_drawdown_r'],result['monte_carlo']['p95_drawdown_r'])
