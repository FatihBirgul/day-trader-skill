import unittest
from fastapi.testclient import TestClient
from forex.core import DataError, analyze, backtest, risk_check, size_lots, validate_bars
from forex.providers import FixtureProvider
from forex.api import app

NOW=1800000000
META={'contract_size':100,'tick_size':0.01,'tick_value':1,'tick_value_currency':'USD','point':0.01,
      'volume_step':0.01,'volume_min':0.01,'volume_max':10,'stops_level':10,
      'account_currency':'USD','max_spread':1,'broker_hours':{'timezone':'UTC','weekly':{str(i):[['00:00','24:00']] for i in range(7)}}}

def bars(tf):
    seconds={'M15':900,'H4':14400}[tf]
    start=NOW-221*seconds
    out=[]
    for i in range(220):
        close=1900+i*.1+(5 if i==219 else 0)
        out.append({'time':start+i*seconds,'open':close-.05,'high':close+.1,
                    'low':close-.2,'close':close})
    return out

def fixture():
    return FixtureProvider({'XAUUSD':{'metadata':dict(META),
        'quote':{'bid':1926,'ask':1926.2,'time':NOW-10},
        'candles':{'M15':bars('M15'),'H4':bars('H4')}}})

class Forex(unittest.TestCase):
    def test_buy_signal_and_api(self):
        p=fixture(); result=analyze(p,'XAUUSD',now=NOW)
        self.assertEqual(result['signal'],'BUY')
        self.assertEqual(result['data_status'],'OK')
        self.assertLess(result['plan']['stop_loss'],result['plan']['entry'])
        app.state.provider=p
        client=TestClient(app)
        self.assertEqual(client.get('/api/v1/symbols').status_code,200)
        self.assertEqual(client.get('/api/v1/symbols/XAUUSD/metadata').status_code,200)
        self.assertEqual(client.get('/api/v1/quotes/XAUUSD').status_code,200)
        self.assertEqual(client.get('/api/v1/candles/XAUUSD').status_code,200)
        self.assertIn('/api/v1/analysis/{symbol}',client.get('/openapi.json').json()['paths'])
        self.assertEqual(client.get('/api/v1/calendar').json()['data_status'],'DATA_UNAVAILABLE')
        self.assertEqual(client.get('/api/v1/news').json()['data_status'],'DATA_UNAVAILABLE')
        app.state.provider=None
    def test_stale_and_incomplete(self):
        p=fixture();p.data['XAUUSD']['quote']['time']=NOW-500
        self.assertEqual(analyze(p,'XAUUSD',now=NOW)['data_status'],'STALE')
        with self.assertRaises(DataError): validate_bars([{'time':NOW-800,'open':1,'high':2,'low':.5,'close':1}],'M15',NOW)
    def test_sizing_and_limits(self):
        s=size_lots(10000,1,2000,1999.5,META,account_currency='USD')
        self.assertEqual(s['lots'],2)
        self.assertEqual(s['estimated_risk'],100)
        with self.assertRaises(DataError): size_lots(10,1,2000,1990,META)
        self.assertEqual(risk_check({'direction':'SELL','entry':2,'stop_loss':2.1,'take_profit_1':1.8},
                         {**META,'spread':.01},.05)['decision'],'PASS')
    def test_stop_first_backtest(self):
        data=[{'open':1,'high':1,'low':1,'close':1},{'open':1,'high':3,'low':.2,'close':1}]
        self.assertEqual(backtest(data,'BUY',1,.5,2,.01)['outcomes_r'][0],-1)

if __name__=='__main__': unittest.main()

class FakeMT5:
    TIMEFRAME_M15=15
    TIMEFRAME_H4=240
    ORDER_TYPE_BUY=0
    ORDER_TYPE_SELL=1
    calls=[]
    def initialize(self): return True
    def shutdown(self): pass
    def last_error(self): return (0,'')
    def symbol_info(self,s):
        if s!='XAUUSD.r': return None
        from types import SimpleNamespace
        return SimpleNamespace(trade_contract_size=100,trade_tick_size=.01,trade_tick_value=1,
            point=.01,volume_min=.01,volume_max=10,volume_step=.01,trade_stops_level=10)
    def symbol_select(self,s,on): return s=='XAUUSD.r'
    def account_info(self):
        from types import SimpleNamespace
        return SimpleNamespace(currency='USD')
    def symbol_info_tick(self,s):
        from types import SimpleNamespace
        return SimpleNamespace(bid=1900,ask=1900.2,time_msc=int(__import__('time').time()*1000))
    def copy_rates_from_pos(self,s,tf,start,count):
        now=int(__import__('time').time())
        return [{'time':now-1800,'open':1,'high':2,'low':.5,'close':1.5,'tick_volume':5},
                {'time':now-100,'open':1,'high':2,'low':.5,'close':1.5,'tick_volume':5}]
    def order_calc_profit(self,typ,s,lots,entry,stop): return -50*lots

class MT5Adapter(unittest.TestCase):
    def test_mapping_closed_candles_profit_and_shutdown(self):
        from forex.providers import MT5Provider
        p=MT5Provider(FakeMT5(),{'XAUUSD':'XAUUSD.r'})
        self.assertEqual(p.metadata('XAUUSD')['contract_size'],100)
        self.assertEqual(p.quote('XAUUSD')['ask'],1900.2)
        self.assertEqual(len(p.candles('XAUUSD','M15')),1)
        self.assertEqual(p.loss_for('XAUUSD','BUY',1,1900,1899),-50)
        p.close()
    def test_unverified_mapping_blocks(self):
        from forex.providers import MT5Provider
        with self.assertRaises(DataError): MT5Provider(FakeMT5()).metadata('XAUUSD')

class MoreForex(unittest.TestCase):
    def test_sell_signal(self):
        p=fixture()
        for tf in ('M15','H4'):
            for i,b in enumerate(p.data['XAUUSD']['candles'][tf]):
                c=2100-i*.1-(5 if i==219 else 0)
                b.update(open=c+.05,high=c+.2,low=c-.1,close=c)
        p.data['XAUUSD']['quote'].update(bid=2073,ask=2073.2)
        result=analyze(p,'XAUUSD',now=NOW)
        self.assertEqual(result['signal'],'SELL')
        self.assertGreater(result['plan']['stop_loss'],result['plan']['entry'])
        self.assertLess(result['plan']['take_profit_1'],result['plan']['entry'])
    def test_precision_and_wrong_stop(self):
        from forex.core import price_round
        self.assertEqual(price_round(1.23456,.00001,'down'),1.23456)
        self.assertEqual(price_round(150.123,.001,'up'),150.123)
        with self.assertRaises(DataError): size_lots(10000,1,2000,2001,META)
    def test_api_validation(self):
        app.state.provider=fixture()
        client=TestClient(app)
        self.assertEqual(client.get('/api/v1/candles/XAUUSD?count=10001').status_code,422)
        self.assertEqual(client.get('/api/v1/analysis/BAD').status_code,422)
        self.assertEqual(client.post('/api/v1/backtests',json={'symbol':'XAUUSD','direction':'BUY','entry':1,'stop_loss':.5,'take_profit':2,'spread':0,'count':10001}).status_code,422)
        app.state.provider=None

class FinancialSafety(unittest.TestCase):
    def test_single_trade_closes_once(self):
        rows=[{'open':1,'high':1,'low':1,'close':1},{'open':1,'high':2.1,'low':.8,'close':2},
              {'open':2,'high':2.2,'low':.2,'close':.3}]
        r=backtest(rows,'BUY',1,.5,2,.01)
        self.assertEqual((r['trades'],r['status'],len(r['outcomes_r'])),(1,'TARGET',1))
        self.assertEqual(r['bars_evaluated'],1)
    def test_stop_first_and_open(self):
        rows=[{'open':1,'high':1,'low':1,'close':1},{'open':1,'high':2.1,'low':.4,'close':1}]
        self.assertEqual(backtest(rows,'BUY',1,.5,2)['status'],'STOP')
        self.assertEqual(backtest([rows[0],{'open':1,'high':1.2,'low':.8,'close':1.1}],
                                  'BUY',1,.5,2)['status'],'OPEN')
    def test_sell_exit_and_cost(self):
        rows=[{'open':2,'high':2,'low':2,'close':2},{'open':2,'high':2.2,'low':.9,'close':1}]
        a=backtest(rows,'SELL',2,2.5,1,0)
        b=backtest(rows,'SELL',2,2.5,1,.1)
        self.assertEqual(a['status'],'TARGET')
        self.assertAlmostEqual(a['result_r'],2)
        self.assertAlmostEqual(b['result_r'],1.5)
        rows[1]['high']=2.6
        self.assertEqual(backtest(rows,'SELL',2,2.5,1)['status'],'STOP')
    def test_time_order_rejected(self):
        rows=[{'time':2,'open':1,'high':1,'low':1,'close':1},
              {'time':1,'open':1,'high':2,'low':.8,'close':1.1}]
        with self.assertRaises(DataError): backtest(rows,'BUY',1,.5,2)
    def test_broker_profit_sign_and_grid(self):
        meta={**META,'volume_min':.03,'volume_step':.02,'volume_max':.11,
              'account_currency':'EUR','tick_value_currency':'USD'}
        def loss(side,lots,entry,stop): return -100*lots
        result=size_lots(100,5,1,.5,meta,loss,'BUY','EUR')
        self.assertEqual(result['lots'],.05)
        self.assertEqual(result['currency'],'EUR')
        with self.assertRaises(DataError): size_lots(100,5,1,.5,meta,lambda *args: 5,'BUY','EUR')
        with self.assertRaises(DataError): size_lots(100,5,1,.5,meta,None,'BUY','EUR')
        with self.assertRaises(DataError): size_lots(100,5,1,.5,meta,loss,'BUY','USD')
    def test_fixture_symbol_isolation(self):
        p=FixtureProvider({'EURUSD':{'metadata':{**META,'tick_value':2},'quote':{},'candles':{}},
                           'USDJPY':{'metadata':{**META,'tick_value':3},'quote':{},'candles':{}}})
        self.assertEqual(p.loss_for('USDJPY','BUY',1,100,99),-300)
        self.assertEqual(p.loss_for('EURUSD','BUY',1,100,99),-200)
    def test_api_health_requires_terminal(self):
        from forex.providers import MT5Provider
        app.state.provider=MT5Provider(FakeMT5(),{'XAUUSD':'XAUUSD.r'})
        self.assertEqual(TestClient(app).get('/api/v1/health').status_code,503)
        app.state.provider=None

class ProviderFailures(unittest.TestCase):
    def test_missing_metadata_is_rejected(self):
        from forex.providers import MT5Provider
        class Broken(FakeMT5):
            def symbol_info(self,s):
                from types import SimpleNamespace
                return SimpleNamespace(point=.01)
        with self.assertRaises(DataError): MT5Provider(Broken(),{'XAUUSD':'XAUUSD.r'}).metadata('XAUUSD')
    def test_disconnect_reinitializes(self):
        from forex.providers import MT5Provider
        from types import SimpleNamespace
        class Reconnect(FakeMT5):
            def __init__(self): self.inits=0;self.connected=False
            def initialize(self): self.inits+=1;self.connected=True;return True
            def shutdown(self): self.connected=False
            def terminal_info(self): return SimpleNamespace(connected=self.connected,trade_allowed=True)
        mt=Reconnect();p=MT5Provider(mt,{'XAUUSD':'XAUUSD.r'})
        self.assertTrue(p.health()['connected'])
        mt.connected=False
        self.assertTrue(p.health()['connected'])
        self.assertEqual(mt.inits,2)
    def test_stale_tick_rejected(self):
        from forex.providers import MT5Provider
        from types import SimpleNamespace
        class OldTick(FakeMT5):
            def symbol_info_tick(self,s): return SimpleNamespace(bid=1,ask=1.1,time_msc=1000)
        with self.assertRaises(DataError): MT5Provider(OldTick(),{'XAUUSD':'XAUUSD.r'}).quote('XAUUSD')

class MetadataSafety(unittest.TestCase):
    def test_wrong_mapped_instrument(self):
        from forex.providers import MT5Provider
        class Wrong(FakeMT5):
            def symbol_info(self,s):
                from types import SimpleNamespace
                return SimpleNamespace(currency_base='EUR',currency_profit='USD')
        with self.assertRaises(DataError): MT5Provider(Wrong(),{'XAUUSD':'EURUSD.r'}).metadata('XAUUSD')
    def test_explicit_spread_policy_required_for_signal(self):
        p=fixture();p.data['XAUUSD']['metadata'].pop('max_spread')
        result=analyze(p,'XAUUSD',now=NOW)
        self.assertEqual(result['data_status'],'DATA_UNAVAILABLE')
        self.assertIsNone(result['plan'])

class PlanMetadata(unittest.TestCase):
    def test_missing_contract_blocks_plan(self):
        p=fixture();p.data['XAUUSD']['metadata'].pop('contract_size')
        result=analyze(p,'XAUUSD',now=NOW)
        self.assertEqual(result['data_status'],'DATA_UNAVAILABLE')
        self.assertIsNone(result['plan'])
