"""Read-only daily Forex risk policy using explicit caller-supplied manual records."""
from datetime import datetime,timezone
import hashlib,json
from .core import DataError, finite, risk_check, size_lots

def assess(plan, meta, balance, risk_pct, records=(), max_daily_risk_pct=3,
           max_daily_loss_pct=3, max_trades=3, max_open=1, max_spread=None,
           min_rr=1.5, calc_profit=None, account_currency=None, now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise DataError('UTC-aware now required')
    today=now.astimezone(timezone.utc).date().isoformat()
    key={k:plan.get(k) for k in ('symbol','direction','entry','stop_loss','take_profit_1','timeframe')}
    fingerprint=hashlib.sha256(json.dumps(key,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
    today_rows=[r for r in records if r.get('date')==today]
    reasons=[]
    if any(r.get('fingerprint')==fingerprint for r in today_rows): reasons.append('duplicate plan')
    if len(today_rows)>=max_trades: reasons.append('daily trade count limit')
    open_count=sum(1 for r in records if r.get('status')=='open')
    daily_planned=sum(finite(r.get('planned_risk',0),'planned_risk') for r in today_rows)
    daily_loss=sum(finite(r.get('realized_loss',0),'realized_loss') for r in today_rows)
    capital=finite(balance,'balance')
    if capital<=0: raise DataError('invalid balance')
    if daily_loss>=capital*finite(max_daily_loss_pct,'max_daily_loss_pct')/100: reasons.append('daily loss limit')
    spread_limit=finite(max_spread if max_spread is not None else meta.get('max_spread'),'max_spread')
    check=risk_check(plan,meta,spread_limit,min_rr,max_open,open_count)
    reasons+=check['reasons']
    try:
        sized=size_lots(capital,risk_pct,plan['entry'],plan['stop_loss'],meta,calc_profit,
                        plan['direction'],account_currency)
        if daily_planned+sized['estimated_risk']>capital*finite(max_daily_risk_pct,'max_daily_risk_pct')/100:
            reasons.append('daily planned risk limit')
    except (DataError,KeyError) as exc:
        sized=None;reasons.append(str(exc))
    return {'decision':'BLOCK' if reasons else 'PASS','reasons':reasons,
            'fingerprint':fingerprint,'sizing':sized,'records_source':'caller_supplied_manual',
            'daily_planned_risk':daily_planned,'daily_realized_loss':daily_loss}
