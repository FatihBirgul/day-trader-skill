import unittest
from datetime import datetime, timezone
from forex.macro import MacroEvent, SuppliedCalendar, information_context

NOW=datetime(2026,11,6,12,tzinfo=timezone.utc)
EVENT={'event_id':'fixture-cpi','source':'test-source','url':'https://example.org/cpi',
       'published_at':'2026-11-06T09:00:00Z','retrieved_at':'2026-11-06T11:00:00Z',
       'release_at':'2026-11-06T13:00:00Z','currency':'USD','event_type':'CPI',
       'importance':'HIGH','forecast':2.5,'previous':2.4}


class MacroContract(unittest.TestCase):
    def test_unavailable_and_declared_are_distinct(self):
        self.assertEqual(information_context(as_of=NOW)['data_status'],'DATA_UNAVAILABLE')
        context=information_context(SuppliedCalendar([EVENT,EVENT]),as_of=NOW)
        self.assertEqual(context['data_status'],'DECLARED_SOURCE')
        self.assertEqual(len(context['events']),1)
        self.assertIsNone(context['events'][0]['actual'])
        self.assertFalse(context['event_filter_verified'])
        self.assertFalse(context['directional_permission'])

    def test_future_provenance_actual_and_stale_fail_closed(self):
        for fields in ({'retrieved_at':'2026-11-06T14:00:00Z'}, {'actual':2.7},
                       {'published_at':'2026-11-04T09:00:00Z','retrieved_at':'2026-11-04T11:00:00Z'}):
            with self.subTest(fields=fields):
                result=information_context(SuppliedCalendar([{**EVENT,**fields}]),as_of=NOW)
                self.assertEqual(result['data_status'],'DATA_UNAVAILABLE')
                self.assertEqual(result['events'],[])

    def test_bad_url_naive_timestamp_and_nonfinite_rejected(self):
        for fields in ({'url':'file:///tmp/a'}, {'release_at':'2026-11-06T13:00:00'}, {'forecast':float('nan')}):
            with self.assertRaises(ValueError): MacroEvent.model_validate({**EVENT,**fields})

    def test_conflicting_revisions_are_not_silently_deduplicated(self):
        result=information_context(SuppliedCalendar([EVENT,{**EVENT,'forecast':3.0}]),as_of=NOW)
        self.assertEqual(result['data_status'],'DATA_UNAVAILABLE')
        self.assertEqual(result['events'],[])
