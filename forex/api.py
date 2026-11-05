"""Local read-only REST facade. Set a provider in app.state.provider before use."""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal
from .core import SYMBOLS, TIMEFRAMES, DataError, analyze, size_lots, backtest
from .providers import MT5Provider

app=FastAPI(title='Trade AI Forex',version='0.1.0')
app.state.provider=None

def provider():
    if app.state.provider is None:
        try: app.state.provider=MT5Provider()
        except DataError as exc: raise HTTPException(503,{'status':'DATA_UNAVAILABLE','reason':str(exc)})
    return app.state.provider

def call(fn):
    try: return fn()
    except DataError as exc: raise HTTPException(422,{'status':'ERROR','reason':str(exc)})
    except KeyError as exc: raise HTTPException(404,{'status':'DATA_UNAVAILABLE','reason':str(exc)})

class RiskRequest(BaseModel):
    symbol: str
    direction: Literal['BUY','SELL']
    balance: float=Field(gt=0)
    risk_pct: float=Field(gt=0,le=5)
    entry: float=Field(gt=0)
    stop_loss: float=Field(gt=0)
    account_currency: str

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: Literal['M5','M15','M30','H1','H4','D1']='M15'
    direction: Literal['BUY','SELL']
    entry: float=Field(gt=0)
    stop_loss: float=Field(gt=0)
    take_profit: float=Field(gt=0)
    spread: float=Field(ge=0)
    count: int=Field(ge=2,le=10000)

@app.get('/api/v1/health')
def health():
    p=app.state.provider
    return {'status':'OK' if p else 'DATA_UNAVAILABLE','provider':p.name if p else None,
            'timestamp':datetime.now(timezone.utc).isoformat()}

@app.get('/api/v1/symbols')
def symbols(): return {'symbols':SYMBOLS,'provider':provider().name,'data_status':'OK'}

@app.get('/api/v1/symbols/{symbol}/metadata')
def metadata(symbol:str): return call(lambda: {'data':provider().metadata(symbol),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/quotes/{symbol}')
def quotes(symbol:str): return call(lambda: {'data':provider().quote(symbol),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/candles/{symbol}')
def candles(symbol:str,timeframe:str='M15',count:int=Query(220,ge=1,le=10000)):
    return call(lambda: {'data':provider().candles(symbol,timeframe,count),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/analysis/{symbol}')
def analysis(symbol:str,timeframe:str='M15'):
    return call(lambda: analyze(provider(),symbol,timeframe))

@app.get('/api/v1/signals/{symbol}')
def signals(symbol:str,timeframe:str='M15'): return analysis(symbol,timeframe)

@app.post('/api/v1/risk/calculate')
def calculate(req:RiskRequest):
    return call(lambda: size_lots(req.balance,req.risk_pct,req.entry,req.stop_loss,provider().metadata(req.symbol),
                (lambda side,lots,e,s: provider().loss_for(req.symbol,side,lots,e,s)) if hasattr(provider(),'loss_for') else None,
                req.direction,req.account_currency))

@app.get('/api/v1/news')
def news(): return {'items':[],'provider':None,'data_status':'DATA_UNAVAILABLE','reason':'Forex news source not configured'}

@app.get('/api/v1/calendar')
def calendar(): return {'events':[],'provider':None,'data_status':'DATA_UNAVAILABLE','reason':'Economic calendar source not configured'}

@app.post('/api/v1/backtests')
def backtests(req:BacktestRequest):
    return call(lambda: {'result':backtest(provider().candles(req.symbol,req.timeframe,req.count),req.direction,
                req.entry,req.stop_loss,req.take_profit,req.spread),'provider':provider().name,'data_status':'OK'})
