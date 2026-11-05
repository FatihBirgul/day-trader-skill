import unittest
from fastapi.testclient import TestClient
from forex.core import DataError, analyze, backtest, risk_check, size_lots, validate_bars
from forex.providers import FixtureProvider
from forex.api import app

NOW=1800000000
META={'tick_size':0.01,'tick_value':1,'tick_value_currency':'USD','point':0.01,
      'volume_step':0.01,'volume_min':0.01,'volume_max':10,'stops_level':10,
      'account_currency':'USD','max_spread':1}

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
        data=[{'high':1,'low':1},{'high':3,'low':.2}]
        self.assertLess(backtest(data,'BUY',1,.5,2,.01)['outcomes_r'][0],-1)

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
        return SimpleNamespace(bid=1900,ask=1900.2,time_msc=NOW*1000)
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
