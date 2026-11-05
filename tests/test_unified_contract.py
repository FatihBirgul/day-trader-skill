import unittest
from forex.contracts import capture, SnapshotProvider
from forex.core import DataError
from forex.extensions import context_evidence
from test_forex import fixture, NOW


class SnapshotContract(unittest.TestCase):
    def test_owned_snapshot(self):
        p = fixture()
        snap = capture(p, 'XAUUSD', 'M15', NOW)
        original = snap.payload()
        p.data['XAUUSD']['candles']['M15'][-1]['close'] = 1
        changed = snap.payload()
        changed['frames']['M15'][-1]['close'] = 2
        self.assertEqual(snap.payload(), original)
        self.assertEqual(SnapshotProvider(snap).candles('XAUUSD', 'M15')[-1]['close'],
                         original['frames']['M15'][-1]['close'])

    def test_missing_open_bar_rejected(self):
        p = fixture()
        del p.data['XAUUSD']['candles']['M15'][10]
        with self.assertRaisesRegex(DataError, 'missing candle'):
            capture(p, 'XAUUSD', 'M15', NOW)

    def test_real_volume_unfinished_and_boolean_rejected(self):
        for fields in ({'volume_kind': 'real', 'volume': 10}, {'is_final': False},
                       {'time': True}, {'close': True}, {'volume_kind': 'tick', 'tick_volume': -1}):
            with self.subTest(fields=fields):
                p = fixture()
                p.data['XAUUSD']['candles']['M15'][-1].update(fields)
                with self.assertRaises(DataError): capture(p, 'XAUUSD', 'M15', NOW)

    def test_higher_asof_and_invalid_identity(self):
        p = fixture()
        snap = capture(p, 'XAUUSD', 'M15', NOW)
        primary_close = snap.payload()['decision_close_utc']
        self.assertTrue(all(b['close_time_utc'] <= primary_close for b in snap.payload()['frames']['H4']))
        p.data['XAUUSD']['metadata']['symbol'] = 'BTCUSDT'
        with self.assertRaises(DataError): capture(p, 'XAUUSD', 'M15', NOW)

    def test_mixed_candle_identity_is_not_discarded(self):
        for fields in ({'source':'foreign-provider'}, {'symbol':'EURUSD'}, {'price_kind':'ask'}, {'timeframe':'H1'}):
            p=fixture();p.data['XAUUSD']['candles']['M15'][10].update(fields)
            with self.assertRaisesRegex(DataError,'identity mismatch'):
                capture(p,'XAUUSD','M15',NOW)


class ContextVeto(unittest.TestCase):
    def evidence(self):
        return dict(source='fixture', event_id='same-price-event', category='trend', direction='BUY',
                    known_at=float(NOW - 1), confirmed=True)

    def test_same_event_and_correlation_do_not_add_votes(self):
        first = self.evidence()
        second = {**first, 'category': 'momentum', 'source': 'second-indicator'}
        other = {**first, 'event_id': 'different-price-event'}
        result = context_evidence([first, second, other], NOW)
        self.assertEqual(len(result['evidence']), 2)
        self.assertEqual(result['independent_price_groups'], 1)
        self.assertIsNone(result['score'])

    def test_conflict_kept_and_context_cannot_direct(self):
        a = self.evidence()
        b = {**a, 'direction': 'SELL'}
        self.assertEqual(context_evidence([a, b], NOW)['conflicts'], ['BUY', 'SELL'])
        for category in ('pattern', 'mtf', 'volatility'):
            context = context_evidence([{**b, 'category': category}, a], NOW)
            self.assertEqual(context['conflicts'], [])
        self.assertEqual(context_evidence([{**a, 'known_at': float(NOW + 1)}], NOW)['evidence'], [])

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            context_evidence([{**self.evidence(), 'known_at': float('nan')}], NOW)

class BrokerGapPolicy(unittest.TestCase):
    def test_verified_weekend_gap_is_allowed_but_unknown_gap_is_not(self):
        from datetime import datetime, timezone
        p=fixture()
        friday=int(datetime(2026,11,6,23,45,tzinfo=timezone.utc).timestamp())
        monday=int(datetime(2026,11,9,tzinfo=timezone.utc).timestamp())
        rows=p.data['XAUUSD']['candles']['M15']
        for i,b in enumerate(rows):
            b['time']=friday-(199-i)*900 if i<200 else monday+(i-200)*900
        now=rows[-1]['time']+1800
        p.data['XAUUSD']['quote']['time']=now-1
        hours={'timezone':'UTC','weekly':{str(i):[['00:00','24:00']] for i in range(5)}}
        p.data['XAUUSD']['metadata']['broker_hours']=hours
        snapshot=capture(p,'XAUUSD','M15',now,('M15',))
        self.assertEqual(len(snapshot.payload()['frames']['M15']),220)
        p.data['XAUUSD']['metadata']['broker_hours']=None
        with self.assertRaisesRegex(DataError,'missing candle'):
            capture(p,'XAUUSD','M15',now,('M15',))
