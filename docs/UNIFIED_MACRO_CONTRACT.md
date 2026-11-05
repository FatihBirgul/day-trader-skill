# Macro context contract

`forex/macro.py` defines source URL, publication/release/retrieval UTC times, currency, event type, importance, actual/forecast/previous and units. It supports Fed/FOMC, CPI, NFP, rates, ECB/BoE/BoJ, GDP, unemployment and gold macro event labels. This is a data model, not a verified source catalogue or forecasting service.

`SuppliedCalendar` validates explicitly supplied records. `information_context` rejects stale retrievals, future publication/retrieval, actual values before release, conflicting duplicate revisions, nonfinite values, naive times and invalid source URLs. It reports DECLARED_SOURCE while event coverage and protective filtering remain unverified. No provider returns DATA_UNAVAILABLE. An empty declared batch does not establish that no important events exist.

There is no default network fetch or direction vote. The unified report and GET /api/v5/information expose this context. Existing RSS parsing/deduplication is preserved. No new live feed is claimed: source permission, reliable release coverage and historical point-in-time snapshots remain open work.
