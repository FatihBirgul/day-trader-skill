import unittest
from datetime import datetime, timezone
from forex.sessions import active_sessions, broker_status

class Sessions(unittest.TestCase):
    def test_dst_london(self):
        winter=datetime(2026,1,15,8,tzinfo=timezone.utc)
        summer=datetime(2026,7,15,7,tzinfo=timezone.utc)
        self.assertIn('London',active_sessions(winter))
        self.assertIn('London',active_sessions(summer))
        self.assertNotIn('London',active_sessions(datetime(2026,1,15,7,tzinfo=timezone.utc)))
    def test_overlap(self):
        self.assertIn('London_New_York_overlap',active_sessions(datetime(2026,7,15,14,tzinfo=timezone.utc)))
    def test_unknown_weekend_and_disabled(self):
        weekday=datetime(2026,7,15,12,tzinfo=timezone.utc)
        self.assertEqual(broker_status(weekday,'XAUUSD')['status'],'UNKNOWN')
        self.assertEqual(broker_status(weekday,'XAUUSD',False)['status'],'CLOSED')
        self.assertEqual(broker_status(datetime(2026,7,18,12,tzinfo=timezone.utc),'XAUUSD')['status'],'CLOSED')
    def test_configured_hours(self):
        policy={'timezone':'Europe/London','weekly':{'2':[['08:00','17:00']]}}
        self.assertEqual(broker_status(datetime(2026,7,15,7,tzinfo=timezone.utc),'XAUUSD',True,policy)['status'],'OPEN')
        self.assertEqual(broker_status(datetime(2026,7,15,15,45,tzinfo=timezone.utc),'XAUUSD',True,policy)['status'],'CLOSING_SOON')
        self.assertEqual(broker_status(datetime(2026,7,15,6,45,tzinfo=timezone.utc),'XAUUSD',True,policy)['status'],'OPENING_SOON')
