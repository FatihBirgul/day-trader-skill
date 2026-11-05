"""V5 read-only orchestration around the existing V4 engine and an optional ABI."""
from datetime import datetime, timezone
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import capture, canonical, provider_read, SnapshotProvider
from .core import DataError, analyze, finite
from .extensions import Evidence, ExtensionResult, context_evidence
from .policy import assess

ENGINE_VERSION = 'forex-unified-5.1'
ALGORITHMS = {'ema': 'sma-seed-1', 'rsi14': 'legacy-wilder-1',
              'atr14': 'legacy-true-range-sma-1', 'macd': 'sma-seed-12-26-9-1',
              'bollinger': 'population-std20-2-1', 'strategies': 'forex-v4-1',
              'structure': 'forex-structure-2'}


@lru_cache(maxsize=1)
def public_code_digest():
    """Content fingerprint without git/network/private source dependencies."""
    root = Path(__file__).resolve().parent.parent
    paths = sorted((root/'forex').glob('*.py')) + [root/folder/file for folder,file in (
        ('trader-scanner','scan.py'),('trader-entry','entry.py'),('trader-exit','exit.py'),
        ('trader-timemachine','timemachine.py'),('trader-news','news.py'))]
    return hashlib.sha256(canonical({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in paths}).encode()).hexdigest()


class ExtensionCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    strategy: str = Field(min_length=1, max_length=120)
    direction: Literal['BUY', 'SELL', 'WAIT']
    reason: str = Field(max_length=500)


class ExtensionPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    regime: dict | None = None
    technical_methods: dict | None = None
    price_action: dict | None = None
    candlestick_patterns: dict | None = None
    chart_patterns: dict | None = None
    confluence: dict | None = None
    evidence: list[Evidence] = Field(default_factory=list, max_length=1000)
    strategy_candidates: list[ExtensionCandidate] = Field(default_factory=list, max_length=30)
    missing_capabilities: list[str] = Field(default_factory=list, max_length=100)
    algorithm_versions: dict[str, str] = Field(default_factory=dict)


class UnifiedAnalysis(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    analysis_id: str
    schema_version: Literal['forex-analysis-5'] = 'forex-analysis-5'
    engine_version: str = ENGINE_VERSION
    source_versions: dict
    symbol: str
    market_type: str = 'unverified'
    contract_type: str = 'unverified'
    broker_symbol: str | None = None
    provider: str
    timeframe: str
    as_of_utc: str
    snapshot_id: str | None = None
    market_status: str = 'UNKNOWN'
    data_status: str = 'DATA_UNAVAILABLE'
    trading_eligibility: Literal['ELIGIBLE', 'BLOCKED', 'NOT_EVALUATED'] = 'NOT_EVALUATED'
    integration_status: Literal['PUBLIC_CORE_ONLY', 'PRIVATE_PARTIAL', 'PRIVATE_AVAILABLE'] = 'PUBLIC_CORE_ONLY'
    private_extension: dict = Field(default_factory=dict)
    trend: dict | None = None
    momentum: dict | None = None
    volatility: dict | None = None
    indicators: dict | None = None
    market_structure: dict | None = None
    candlestick_patterns: dict | None = None
    chart_patterns: dict | None = None
    confluence: dict | None = None
    confirmations: list[dict] = Field(default_factory=list)
    strategy_candidates: list[dict] = Field(default_factory=list)
    strategy_conflicts: list[str] = Field(default_factory=list)
    final_decision: Literal['BUY_CANDIDATE', 'SELL_CANDIDATE', 'WAIT', 'NO_TRADE', 'INSUFFICIENT_DATA', 'MARKET_CLOSED', 'STALE_DATA', 'PROVIDER_UNAVAILABLE'] = 'PROVIDER_UNAVAILABLE'
    legacy_signal: Literal['BUY', 'SELL', 'WAIT'] = 'WAIT'
    decision_reasons: list[str] = Field(default_factory=list)
    entry_zone: dict | None = None
    stop_loss: float | None = None
    take_profit_1: float | None = None
    take_profit_2: float | None = None
    risk_reward: float | None = None
    lot_size: float | None = None
    risk_amount: float | None = None
    risk_policy: dict | None = None
    missing_capabilities: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    research_status: str = 'UNVERIFIED_IN_MARKET'
    information: dict = Field(default_factory=dict)


def _extension(extension, snapshot, core):
    if extension is None:
        return {'status': 'UNAVAILABLE', 'reason': 'private extension not configured'}, {}
    try:
        result = ExtensionResult.model_validate(extension.evaluate(snapshot, context_json=canonical(core)))
        if result.snapshot_id != snapshot.snapshot_id or result.source_sha != extension.source_sha:
            raise DataError('extension source or snapshot mismatch')
        if len(result.data_json) > 1_000_000:
            raise DataError('extension payload exceeds budget')
        def invalid_constant(value):
            raise ValueError('nonfinite extension value')
        payload = json.loads(result.data_json, parse_constant=invalid_constant)
        if not isinstance(payload, dict):
            raise DataError('invalid extension payload')
        canonical(payload)  # Also rejects overflow literals such as 1e999.
        payload = ExtensionPayload.model_validate(payload).model_dump(exclude_none=True)
        return {'status': result.status, 'source_sha': result.source_sha,
                'bridge_version': result.bridge_version}, payload if result.status != 'UNAVAILABLE' else {}
    except Exception:
        # Never leak a private traceback, source path or credentials to public API/logs.
        return {'status': 'UNAVAILABLE', 'reason': 'private extension contract or calculation failure'}, {}


def unified_analyze(provider, symbol, timeframe='M15', *, now=None, confirmations=('H4',),
                    extension=None, require_private=False, balance=None, risk_pct=1,
                    records=(), commission_per_lot=0, slippage_price=0, information_provider=None):
    now = finite(now if now is not None else datetime.now(timezone.utc).timestamp(), 'as of')
    body = UnifiedAnalysis(analysis_id='', symbol=symbol, timeframe=timeframe,
                           provider=provider.name,
                           as_of_utc=datetime.fromtimestamp(now, timezone.utc).isoformat(),
                           source_versions={'public_core': ENGINE_VERSION, 'public_code_sha256': public_code_digest(),
                                            'algorithms': ALGORITHMS.copy()},
                           missing_capabilities=['real_volume', 'order_flow', 'vwap', 'verified_calendar',
                                                 'margin_estimate', 'verified_swap'],
                           warnings=['Analytical candidates only; no execution permission.',
                                     'Real MT5 and market profitability remain unverified.']).model_dump()
    from .macro import information_context
    body['information'] = information_context(information_provider, as_of=datetime.fromtimestamp(now, timezone.utc))
    try:
        snapshot = capture(provider, symbol, timeframe, now, confirmations)
        saved = snapshot.payload()
        body.update(snapshot_id=snapshot.snapshot_id, broker_symbol=saved['broker_symbol'],
                    market_type=saved['market_type'], contract_type=saved['contract_type'])
        core = analyze(SnapshotProvider(snapshot), symbol, timeframe, now=now,
                       confirmation_timeframes=confirmations)
        body['market_status'] = core.get('session', {}).get('broker', {}).get('status', 'UNKNOWN')
        body['data_status'] = core['data_status']
        body['decision_reasons'] = core['reasons'][:]
        body['confirmations'] = core.get('confirmations', [])
        body['strategy_candidates'] = core.get('strategies', [])
        body['market_structure'] = core.get('market_structure')
        metrics = core.get('indicators')
        body['indicators'] = metrics
        if metrics:
            body['trend'] = {k: metrics[k] for k in ('ema20', 'ema50', 'ema200', 'ema20_slope')}
            body['momentum'] = {k: metrics[k] for k in ('rsi14', 'macd', 'macd_histogram', 'momentum_change')}
            body['volatility'] = {k: metrics[k] for k in ('atr14', 'normalized_atr', 'bollinger_width')}
        if core['data_status'] != 'OK':
            reason = '; '.join(core['reasons'])
            body['final_decision'] = ('MARKET_CLOSED' if body['market_status'] in ('CLOSED', 'DISABLED')
                                      else 'STALE_DATA' if core['data_status'] == 'STALE'
                                      else 'NO_TRADE' if 'spread' in reason or 'broker market' in reason
                                      else 'INSUFFICIENT_DATA')
            if body['final_decision'] in ('MARKET_CLOSED', 'NO_TRADE'):
                body['data_status'] = 'OK'  # Session/risk refusal is separate from candle health.
        else:
            extension_meta, extra = _extension(extension, snapshot, core)
            body['private_extension'] = extension_meta
            if extension_meta['status'] != 'UNAVAILABLE':
                body['integration_status'] = 'PRIVATE_AVAILABLE' if extension_meta['status'] == 'AVAILABLE' else 'PRIVATE_PARTIAL'
                body['source_versions']['private'] = extension_meta['source_sha']
                body['source_versions']['private_algorithms'] = extra.get('algorithm_versions', {})
            else:
                body['missing_capabilities'].append('private_v2_analysis')
                body['warnings'].append('Private V2 unavailable; only the existing public Forex core was evaluated.')
            for name in ('candlestick_patterns', 'chart_patterns'):
                body[name] = extra.get(name, {'status': 'UNAVAILABLE', 'reason': 'private module not configured'})
            body['strategy_candidates'] += extra.get('strategy_candidates', [])
            if extra.get('regime'):
                body['trend']['regime'] = extra['regime']
            if extra.get('technical_methods'):
                body['indicators']['extension_methods'] = extra['technical_methods']
            if extra.get('price_action'):
                body['market_structure']['extension_context'] = extra['price_action']
            body['missing_capabilities'] += extra.get('missing_capabilities', [])
            ev = list(extra.get('evidence', []))
            for vote in core.get('strategies', []):
                ev.append({'source': 'public_forex_v4',
                           'event_id': 'primary-close:' + str(int(saved['decision_close_utc'] * 1000)),
                           'category': 'trend', 'direction': vote['direction'],
                           'known_at': float(saved['decision_close_utc']), 'confirmed': True})
            body['confluence'] = context_evidence(ev, saved['decision_close_utc'])
            # Retain private confluence as descriptive context, never a probability.
            body['confluence']['extension_context'] = extra.get('confluence')
            directions = {v['direction'] for v in body['strategy_candidates'] if v['direction'] in ('BUY', 'SELL')}
            if len(directions) > 1 or body['confluence']['conflicts']:
                body['strategy_conflicts'] = sorted(directions | set(body['confluence']['conflicts']))
            plan = core['plan']
            if body['strategy_conflicts']:
                body['final_decision'] = 'WAIT'
                body['decision_reasons'].append('opposing strategy or confirmed price evidence')
            elif require_private and extension_meta['status'] != 'AVAILABLE':
                body['final_decision'] = 'NO_TRADE'
                body['decision_reasons'].append('required complete private integration unavailable')
            elif plan:
                policy = None
                if balance is not None:
                    meta = {**saved['metadata'], 'spread': saved['quote']['ask'] - saved['quote']['bid']}
                    calc = ((lambda side, lots, e, s: provider_read(provider,'loss_for',symbol,side,lots,e,s))
                            if hasattr(provider, 'loss_for') else None)
                    policy = assess(plan, meta, balance, risk_pct, records,
                                    calc_profit=calc, account_currency=meta.get('account_currency'),
                                    now=datetime.fromtimestamp(now, timezone.utc),
                                    commission_per_lot=commission_per_lot, slippage_price=slippage_price)
                    body['risk_policy'] = policy
                if policy and policy['decision'] == 'BLOCK':
                    body['final_decision'] = 'NO_TRADE'
                    body['decision_reasons'] += policy['reasons']
                else:
                    body['final_decision'] = core['signal'] + '_CANDIDATE'
                    body['legacy_signal'] = core['signal']
                    body['entry_zone'] = {'low': plan['entry'], 'high': plan['entry'],
                                          'price_side': 'ask' if core['signal'] == 'BUY' else 'bid'}
                    for key in ('stop_loss', 'take_profit_1', 'take_profit_2', 'risk_reward'):
                        body[key] = plan[key]
                    if policy:
                        body['lot_size'] = policy['sizing']['lots']
                        body['risk_amount'] = policy['sizing']['estimated_risk']
                    body['trading_eligibility'] = 'ELIGIBLE' if policy else 'NOT_EVALUATED'
                    if policy is None:
                        body['missing_capabilities'].append('account_risk_policy')
                        body['warnings'].append('Account risk budget not evaluated; no verified lot is available.')
            else:
                body['final_decision'] = 'NO_TRADE' if core.get('risk_verdict', {}).get('decision') == 'BLOCK' else 'WAIT'
        if body['final_decision'] not in ('BUY_CANDIDATE', 'SELL_CANDIDATE'):
            body['trading_eligibility'] = 'BLOCKED'
    except (DataError, KeyError, TypeError, ValueError, OverflowError) as exc:
        # Public provider exceptions are bounded too; do not expose arbitrary payloads.
        reason = str(exc) if isinstance(exc, DataError) else 'invalid provider or extension contract'
        body.update(trading_eligibility='BLOCKED', decision_reasons=[reason])
        body['final_decision'] = ('STALE_DATA' if 'stale' in reason else
                                  'PROVIDER_UNAVAILABLE' if any(k in reason for k in ('unavailable', 'failed', 'disconnected')) else
                                  'INSUFFICIENT_DATA')
        body['data_status'] = 'STALE' if body['final_decision'] == 'STALE_DATA' else 'DATA_UNAVAILABLE'
        body.update(entry_zone=None, stop_loss=None, take_profit_1=None, take_profit_2=None,
                    risk_reward=None, lot_size=None, risk_amount=None, legacy_signal='WAIT')
    body['missing_capabilities'] = sorted(set(body['missing_capabilities']))
    body['analysis_id'] = hashlib.sha256(canonical(body).encode()).hexdigest()
    return UnifiedAnalysis.model_validate(body)
