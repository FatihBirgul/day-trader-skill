# Frontend handoff (backend only)

Use POST /api/v5/analysis for the versioned report; existing V1 consumers can continue unchanged. New consumers should display final_decision, data_status, market_status, trading_eligibility and integration_status separately. The legacy_signal field maps all refusals to WAIT for old three-state displays.

Never render unavailable plan levels as zero. Show missing capabilities, source/as-of/version and reasons. PUBLIC_CORE_ONLY is existing Forex analysis, not private V2 analysis. PRIVATE_PARTIAL is not complete strategy integration. Without an account balance/passed policy there is no verified lot. Source-declared macro events do not establish complete or protective calendar coverage.

Indicators with different seeds/smoothing/variance are separately versioned. Pattern, regime, chart and confluence fields may be absent/unavailable and are descriptive. No statistical win probability is supplied. Synthetic fixture examples must retain their test-only provider label. Do not enable execution from a candidate or ELIGIBLE analytical status.

PWA/Windows UI were not edited. Hosting, HTTPS, authentication and remote access are separate work. With the PC/MT5 terminal offline there is no promised live MT5 data. The API may explicitly refuse analysis; do not replace that state with an old price labelled live.
