# Unified V5 API contract

New routes: `POST /api/v5/analysis` and `GET /api/v5/information`. All 18 existing V1 paths are retained, including typed legacy analysis/signals and research. POST is an analytical calculation, with no persistence or broker execution side effect. No frontend files changed.

Request example:

```json
{"symbol":"XAUUSD","timeframe":"M15","confirmations":["H4"],"require_private":false,"balance":10000,"risk_pct":1,"commission_per_lot":5,"slippage_price":0.1,"records":[]}
```

Symbol/timeframe are bounded enums. Confirmation frames must be unique, equal/higher, and at most three. Risk<=5%, positive optional balance, finite/nonnegative costs, bounded manual records; unknown fields (including execution requests) are rejected. Commission is round-trip account currency per lot; slippage is an adverse stop price allowance. Manual records are caller declarations, not a reconciled broker ledger.

Response is `UnifiedAnalysis`, schema `forex-analysis-5`, engine `forex-unified-5.1`. It includes analysis/snapshot hashes, source/algorithm versions, public source content fingerprint, identity/as-of, market/data/eligibility states, technical/structure/pattern/confluence/MTF context, candidates/conflicts/reasons, optional valid levels/sizing, missing capabilities, information and research status. It does not invent statistical success probabilities. The public source fingerprint identifies packaged source content, not an authenticated Git commit; deployment should additionally record its reviewed commit.

| V5 final_decision | Legacy mapping | Plan / interpretation |
|---|---|---|
| BUY_CANDIDATE / SELL_CANDIDATE | BUY / SELL | Existing approved analytical geometry; verified lot only if account sizing/policy passed |
| WAIT | WAIT | Healthy observations but no aligned candidate or conflicting strategies; levels null |
| NO_TRADE | WAIT | Risk/session/required private integration veto; levels null |
| INSUFFICIENT_DATA | WAIT | Invalid/missing/unclosed observations; levels null |
| MARKET_CLOSED | WAIT | Broker closed/disabled; levels null |
| STALE_DATA | WAIT | Out-of-date/future quote or stale candles; levels null |
| PROVIDER_UNAVAILABLE | WAIT | Provider read failed; levels null |

`data_status`, `market_status`, and `trading_eligibility` are separate. Unknown broker hours block plans. A technically valid but unsized candidate has NOT_EVALUATED account eligibility, null lot/risk amount and a missing account_risk_policy capability. ELIGIBLE means the supplied policy inputs passed; it never grants execution permission or verifies the caller's records. Risk refusal must not be confused with unhealthy candles.

Integration states: PUBLIC_CORE_ONLY with explicit unavailable warning; PRIVATE_PARTIAL with only actual available context; PRIVATE_AVAILABLE only when complete configured extension reports AVAILABLE and passes ABI validation. `require_private=true` rejects both absent and partial integration. This source does not ship a private implementation or claim full four-family Forex integration. Scores/context are not success probabilities.

Normally the V5 endpoint returns HTTP200 with structured analytical refusal states. Request shape/validation failures use HTTP422; before any provider object can be created, the retained provider factory can return HTTP503 with legacy `detail.status/reason`. No synthetic replacement prices are returned. Error paths and old/new examples are covered by TestClient tests. Full OpenAPI comes from `/openapi.json`; `docs/UNIFIED_API_EXAMPLES.json` contains actual synthetic public-core examples.

Data acquisition is explicit: snapshot capture reads metadata, quote and each frame once. Optional account sizing can additionally invoke the provider's read-only broker profit calculation; broker state is not a historical immutable contract archive. No MT5 order method, private product service, AI override, network source fallback or external alert delivery is connected.
