# Unified Forex orchestration

The implementation wraps `forex.core.analyze`; it does not introduce another strategy/indicator engine. `contracts.capture` reads each provider resource once, normalizes and validates closed candles, owns an immutable snapshot and cuts higher frames at primary close. `SnapshotProvider` lets the retained V4 engine use this same data without fetching again. `unified.unified_analyze` adds provenance, optional extension context, conflict veto, manual risk-policy checks and a versioned report.

Pipeline: provider → identity/normalization/QC → explicit broker session → existing V4 indicators/structure/strategies/MTF → optional private observations → conservative evidence conflict check → existing plan/risk policy → unified DTO. Risk can only remove a candidate. Information is descriptive and cannot change direction. No stock execution, private product service, AI direction override, database or hidden provider request is attached.

Snapshot gaps are allowed only when the configured broker schedule is CLOSED throughout each missing interval, sampled on its minute policy grid; OPEN/UNKNOWN/DISABLED gaps fail closed. This is a bounded engineering schedule check, not a verified exchange holiday service. D1 uses the existing fixed 86400-second duration; broker DST daily bars need dedicated Windows verification.

Algorithm identities distinguish SMA-seeded EMA/MACD, Wilder RSI, SMA true-range ATR and population-standard-deviation Bollinger bands. Other definitions are separate extension methods. Pattern/MTF/volatility context does not become extra independent directional votes. The public reducer reports conflicts without weights, confidence bonuses or success probabilities; it is not a replacement for the private confluence engine.

The complete private strategy integration remains PARTIAL/BLOCKED where source market, real-volume, session and CFD contracts are incompatible. Availability of a private import is not evidence of Forex strategy eligibility or profitability.
