import json
import unittest
from unittest.mock import patch
from forex.unified import unified_analyze
from forex.extensions import ExtensionResult
from test_forex import fixture, NOW


class StubExtension:
    """ABI test double only; never represents real private source integration."""
    source_sha = '1' * 40
    def __init__(self, payload=None, status='PARTIAL'):
        self.payload, self.status = payload or {}, status
    def evaluate(self, snapshot, *, context_json):
        return ExtensionResult(source_sha=self.source_sha, bridge_version='test-double-1',
                               snapshot_id=snapshot.snapshot_id, status=self.status,
                               data_json=json.dumps(self.payload))


class UnifiedScenarios(unittest.TestCase):
    def test_buy_and_unavailable_are_explicit(self):
        p = fixture()
        result = unified_analyze(p, 'XAUUSD', now=NOW, balance=10000)
        self.assertEqual(result.final_decision, 'BUY_CANDIDATE')
        self.assertEqual(result.integration_status, 'PUBLIC_CORE_ONLY')
        self.assertEqual(result.private_extension['status'], 'UNAVAILABLE')
        self.assertGreater(result.lot_size, 0)
        self.assertLessEqual(result.risk_amount, 100)
        self.assertEqual(result.entry_zone['low'], 1926.2)
        self.assertEqual(result, unified_analyze(p, 'XAUUSD', now=NOW, balance=10000))
        unsized=unified_analyze(p,'XAUUSD',now=NOW)
        self.assertEqual(unsized.trading_eligibility,'NOT_EVALUATED')
        self.assertIsNone(unsized.lot_size)
        strict = unified_analyze(p, 'XAUUSD', now=NOW, require_private=True)
        self.assertEqual(strict.final_decision, 'NO_TRADE')
        self.assertIsNone(strict.entry_zone)

    def test_sell_symmetry(self):
        p = fixture()
        for tf in ('M15', 'H4'):
            for i, bar in enumerate(p.data['XAUUSD']['candles'][tf]):
                c = 2100 - i * .1 - (5 if i == 219 else 0)
                bar.update(open=c + .05, high=c + .2, low=c - .1, close=c)
        p.data['XAUUSD']['quote'].update(bid=2073, ask=2073.2)
        result = unified_analyze(p, 'XAUUSD', now=NOW, balance=10000)
        self.assertEqual(result.final_decision, 'SELL_CANDIDATE')
        self.assertEqual(result.entry_zone['low'], 2073)
        self.assertGreater(result.stop_loss, 2073)
        self.assertLess(result.take_profit_1, 2073)

    def test_strategy_conflict_veto(self):
        extra = {'strategy_candidates': [{'strategy': 'fixture-opponent', 'direction': 'SELL', 'reason': 'test'}]}
        result = unified_analyze(fixture(), 'XAUUSD', now=NOW, extension=StubExtension(extra))
        self.assertEqual(result.final_decision, 'WAIT')
        self.assertIsNone(result.stop_loss)
        self.assertEqual(result.strategy_conflicts, ['BUY', 'SELL'])

    def test_opposing_private_price_context_vetoes_public_buy(self):
        extra = {'evidence': [{'source': 'fixture-private-price', 'event_id': 'independent-test-event',
                              'category': 'structure', 'direction': 'SELL',
                              'known_at': float(NOW - 900), 'confirmed': True}]}
        result = unified_analyze(fixture(), 'XAUUSD', now=NOW, extension=StubExtension(extra))
        self.assertEqual(result.final_decision, 'WAIT')
        self.assertIsNone(result.entry_zone)

    def test_missing_higher_or_bad_timestamp(self):
        for change in ('missing', 'unfinished', 'time'):
            p = fixture()
            if change == 'missing': p.data['XAUUSD']['candles']['H4'] = []
            elif change == 'unfinished': p.data['XAUUSD']['candles']['M15'][-1]['is_final'] = False
            else: p.data['XAUUSD']['candles']['M15'][-1]['time'] = 'bad'
            result = unified_analyze(p, 'XAUUSD', now=NOW)
            self.assertEqual(result.final_decision, 'INSUFFICIENT_DATA')
            self.assertIsNone(result.entry_zone)

    def test_tick_volume_has_no_vwap_or_order_flow(self):
        p = fixture()
        for rows in p.data['XAUUSD']['candles'].values():
            for b in rows: b['tick_volume'] = 50
        result = unified_analyze(p, 'XAUUSD', now=NOW)
        self.assertIn('vwap', result.missing_capabilities)
        self.assertIn('order_flow', result.missing_capabilities)

    def test_closed_unknown_spread_and_risk_veto(self):
        p = fixture()
        p.data['XAUUSD']['metadata']['trade_allowed'] = False
        self.assertEqual(unified_analyze(p, 'XAUUSD', now=NOW).final_decision, 'MARKET_CLOSED')
        p = fixture(); p.data['XAUUSD']['metadata']['broker_hours'] = None
        self.assertEqual(unified_analyze(p, 'XAUUSD', now=NOW).final_decision, 'NO_TRADE')
        p = fixture(); p.data['XAUUSD']['metadata']['max_spread'] = .01
        result = unified_analyze(p, 'XAUUSD', now=NOW)
        self.assertEqual(result.data_status, 'OK')
        self.assertEqual(result.final_decision, 'NO_TRADE')
        result = unified_analyze(fixture(), 'XAUUSD', now=NOW, balance=1)
        self.assertEqual(result.final_decision, 'NO_TRADE')
        self.assertIsNone(result.lot_size)

    def test_adapter_failure_and_snapshot_mismatch_never_leak(self):
        class Broken:
            source_sha = '1' * 40
            def evaluate(self, *args, **kwargs): raise RuntimeError('private secret/path')
        result = unified_analyze(fixture(), 'XAUUSD', now=NOW, extension=Broken(), require_private=True)
        self.assertEqual(result.final_decision, 'NO_TRADE')
        self.assertNotIn('secret', result.model_dump_json())
        ext = StubExtension()
        original = ext.evaluate
        def corrupt(*args, **kwargs):
            return original(*args, **kwargs).model_copy(update={'snapshot_id': '0' * 64})
        ext.evaluate = corrupt
        self.assertEqual(unified_analyze(fixture(), 'XAUUSD', now=NOW, extension=ext).private_extension['status'], 'UNAVAILABLE')

    def test_source_calls_are_not_repeated(self):
        p = fixture()
        with patch.object(p, 'candles', wraps=p.candles) as candles, patch.object(p, 'quote', wraps=p.quote) as quote, patch.object(p, 'metadata', wraps=p.metadata) as metadata:
            unified_analyze(p, 'XAUUSD', now=NOW)
        self.assertEqual(candles.call_count, 2)
        self.assertEqual(quote.call_count, 1)
        self.assertEqual(metadata.call_count, 1)

    def test_provider_exception_is_an_explicit_unavailable_result(self):
        p=fixture()
        with patch.object(p,'candles',side_effect=RuntimeError('secret private path')):
            result=unified_analyze(p,'XAUUSD',now=NOW)
        self.assertEqual(result.final_decision,'PROVIDER_UNAVAILABLE')
        self.assertIsNone(result.entry_zone)
        self.assertNotIn('secret',result.model_dump_json())

class UnifiedAPI(unittest.TestCase):
    def test_v5_response_and_legacy_paths(self):
        from fastapi.testclient import TestClient
        from forex.api import app
        from datetime import datetime, timezone
        app.state.provider = fixture()
        app.state.analytical_extension = None
        try:
            client = TestClient(app)
            with patch('forex.unified.datetime') as clock:
                clock.now.return_value = datetime.fromtimestamp(NOW, timezone.utc)
                clock.fromtimestamp.side_effect = datetime.fromtimestamp
                response = client.post('/api/v5/analysis', json={'symbol': 'XAUUSD', 'balance': 10000})
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body['final_decision'], 'BUY_CANDIDATE')
            self.assertEqual(body['legacy_signal'], 'BUY')
            paths = client.get('/openapi.json').json()['paths']
            self.assertIn('/api/v1/analysis/{symbol}', paths)
            self.assertIn('/api/v1/walk-forward', paths)
            self.assertIn('/api/v5/analysis', paths)
            self.assertEqual(client.post('/api/v5/analysis', json={'symbol': 'XAUUSD', 'execute': True}).status_code, 422)
            self.assertEqual(client.post('/api/v5/analysis', json={'symbol': 'XAUUSD', 'risk_pct': 10}).status_code, 422)
        finally:
            app.state.provider = None
            app.state.analytical_extension = None

    def test_malformed_extension_is_unavailable(self):
        for payload in ({'strategy_candidates': [{'direction': 'BUY'}]}, {'evidence': [{'known_at': float('inf')}]}, {'regime': []}, {'unknown': 'private'}):
            result = unified_analyze(fixture(), 'XAUUSD', now=NOW, extension=StubExtension(payload), require_private=True)
            self.assertEqual(result.private_extension['status'], 'UNAVAILABLE')
            self.assertEqual(result.final_decision, 'NO_TRADE')
