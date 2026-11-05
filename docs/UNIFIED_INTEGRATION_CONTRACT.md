# Public analytical extension contract

Version: `forex-extension-1`; snapshot: `forex-snapshot-1`.

Only the generic protocol in `forex/extensions.py` is distributed publicly. A separately deployed, access-controlled implementation provides `source_sha` and `evaluate(snapshot, context_json=...)`. There is no dynamic module loader, network fetch, order permission, paper-ledger binding or private dependency in public CI.

The input is an owned immutable JSON snapshot: canonical/broker symbol, market/contract identity, venue/provider, bid price basis, volume kind, timeframe, exclusive UTC candle close, analysis as-of, primary decision close, metadata, quote and QC flags. Higher timeframes are cut at the primary close. Primary unfinished/future observations are rejected. Returned payload copies cannot alter the saved snapshot. All existing public technical calculations use the V4 220-bar window from this snapshot.

The result has ABI version, 40-character source SHA, bridge version, matching snapshot hash, AVAILABLE/PARTIAL/UNAVAILABLE, and bounded JSON data. The result SHA must match the configured extension. The host verifies fields, finite values, candidate/evidence schemas and snapshot binding. Exceptions become a generic unavailable result without a private traceback. A hash binds data; it is not source authentication. Deployment must pin and trust the extension package separately.

Supported output sections: regime, technical methods, price-action context, candle/chart patterns, confluence context, versioned algorithms, missing capabilities, evidence and analytical strategy candidates. Unknown fields fail closed. Confirmed price evidence can veto conflicting candidates. Pattern, MTF and volatility remain context. A private candidate cannot create a public plan that the existing Forex core has not approved.

No extension: explicit PUBLIC_CORE_ONLY and private_v2_analysis missing. `require_private=true` blocks plans unless complete integration reports AVAILABLE. A PARTIAL private extension never satisfies that requirement. Default mode can expose existing V4 analytical candidates with an explicit integration warning, without claiming V2 analysis.

Private deployments must additionally verify package commit/content, dependency isolation, source license, import side effects, read-only permissions and supported instrument/volume/session contracts. Actual integration artifacts and confidential source inventories remain outside this public repository. No private implementation is embedded in fixtures.
