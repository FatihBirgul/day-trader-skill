import unittest
from datetime import datetime,timezone
from forex.information import parse_rss,filter_events
from forex.alerts import AlertEngine
from forex.core import DataError

class Information(unittest.TestCase):
    def test_rss_reuses_legacy_parser_and_dedupe(self):
        xml=b'<rss><channel><item><title>FOMC gold update</title><link>https://example.com/1</link><pubDate>Thu, 05 Nov 2026 12:00:00 GMT</pubDate></item><item><title>FOMC gold update</title><link>https://example.com/1</link><pubDate>Thu, 05 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        items=parse_rss(xml,'fixture',datetime(2026,11,6,tzinfo=timezone.utc))
        self.assertEqual(len(items),1)
        self.assertIn('USD',items[0]['currencies'])
    def test_calendar_validation_and_filter(self):
        events=[{'id':'1','time':'2026-11-06T12:00:00Z','currency':'USD','name':'CPI','source':'fixture'},
                {'id':'2','time':'2026-11-06T13:00:00Z','currency':'EUR','name':'ECB','source':'fixture'}]
        self.assertEqual(len(filter_events(events,'XAUUSD')),1)
        with self.assertRaises(DataError): filter_events([{'id':'x','time':'2026-11-06T12:00:00','currency':'USD','name':'CPI','source':'x'}])
    def test_alert_cooldown(self):
        engine=AlertEngine();now=datetime(2026,11,6,tzinfo=timezone.utc)
        result={'symbol':'XAUUSD','timeframe':'M15','data_status':'STALE','signal':'WAIT'}
        self.assertEqual(len(engine.evaluate(result,now=now)),1)
        self.assertEqual(engine.evaluate(result,now=now),[])

class InformationAPI(unittest.TestCase):
    def test_configured_calendar_and_news(self):
        from fastapi.testclient import TestClient
        from forex.api import app
        app.state.news_items=[{'source':'fixture','title':'sample'}]
        app.state.calendar_events=[{'id':'1','time':'2026-11-06T12:00:00Z',
            'currency':'USD','name':'CPI','source':'fixture'}]
        client=TestClient(app)
        self.assertEqual(client.get('/api/v1/news').json()['data_status'],'OK')
        self.assertEqual(len(client.get('/api/v1/calendar?symbol=XAUUSD').json()['events']),1)
        app.state.news_items=None;app.state.calendar_events=None

class AlertReliability(unittest.TestCase):
    def test_event_identity_and_reset(self):
        engine=AlertEngine(30);now=datetime(2026,11,6,tzinfo=timezone.utc)
        data={'symbol':'XAUUSD','timeframe':'M15','data_status':'DATA_UNAVAILABLE',
              'signal':'WAIT','reasons':['MT5 disconnected']}
        first=engine.evaluate(data,now=now)
        self.assertEqual(first[0]['type'],'MT5_DISCONNECTED')
        self.assertTrue(first[0]['id'])
        self.assertFalse(first[0]['acknowledged'])
        self.assertEqual(engine.evaluate(data,now=now),[])
        engine.reset()
        self.assertEqual(len(engine.evaluate(data,now=now)),1)

class RSSInputBounds(unittest.TestCase):
    def test_large_or_entity_feed_rejected(self):
        with self.assertRaises(DataError): parse_rss(b'x'*1_000_001,'fixture')
        with self.assertRaises(DataError): parse_rss(b'<!DOCTYPE rss [<!ENTITY x "hello">]><rss/>','fixture')
