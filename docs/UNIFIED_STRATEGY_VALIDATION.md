# Strategy and technical validation

The production public path retains trend-following, closed-bar breakout and pullback from `forex/strategies.py`; their resolution requires consistent higher-timeframe direction. The new host does not create a fourth independent engine, award extra confidence, or convert a pattern into a trade permission. BUY/SELL outputs are explicitly candidates. Opposing private price evidence or strategy direction vetoes a public candidate. Pattern/MTF/volatility remain context.

The four private-source strategy families were inspected but not forcibly enabled for Forex: required market, real-volume and calendar contracts are incompatible. Successful private imports and descriptive research calls do not constitute integrated Forex strategy eligibility. Range/mean-reversion and failed-breakout strategy calibration, full private MTF strategy routing and regime-specific Forex eligibility remain PARTIAL/BLOCKED.

## Technical definitions

| Method | Public default / evidence | Separate private research / limitation |
|---|---|---|
| EMA9/20/21/50/100/200 | SMA-seeded EMA; closed-form unit-slope fixtures | Other EMA seed remains separately named; no numerical parity assertion |
| SMA | 20/50 trailing mean | Existing private implementation not duplicated |
| RSI | Legacy scanner Wilder recurrence, 14-change SMA seed | Rolling RSI is mathematically different and is not relabelled Wilder |
| MACD/histogram | SMA-seeded 12/26 EMAs and 9 signal; exact linear oracle = 7/7/0 | First-observation ewm variant differs in seed; tested separately |
| ATR | Last14 true-range simple mean; exact linear oracle = 2 | Private Wilder ATR appears in separately versioned research context |
| Bollinger/width | Population standard deviation20, multiplier2 | Private sample-variance method differs; difference tested |
| Stochastic/ADX-DMI/Supertrend/Donchian/ROC | No duplicate public formulas introduced | Actual private research calls exercised as descriptive methods, warmup/version preserved |
| Stochastic RSI | Not in public core | Aggregate private technical adapter refuses FX tick volume; unavailable in combined FX report |
| Momentum change | MACD histogram difference | Not an independently calibrated directional vote |
| Volatility regime | ATR/normalized ATR/BB width context | Full volatility classification/calibration remains partial |
| VWAP/delta/order flow | UNAVAILABLE without validated real volume/feeds | Tick volume never substituted for real trade volume |

`tests/fixtures/forex-v5/indicator-golden.json` is an independent arithmetic oracle, not a dump of implementation output. It includes the closed-form Wilder value `100*(13/14)^14`, linear EMA/MACD/ATR and variance `(20^2-1)/12`. Existing flat/missing/warmup/finite/closed/as-of tests remain. Separate private tests verify actual ATR agreement and expected RSI/MACD/Bollinger disagreements. No blanket cross-engine equality or market accuracy is claimed.

Public structure now records formed close and confirmation/first-detectable close, with version, range and invalidation metadata for pivots. `detected_at` retains the legacy pivot-open label. The same broken pivot does not create another BOS on every subsequent bar. Legacy direct calls without timeframe seconds retain their old timestamp convention; the analysis core always supplies the actual duration.

Pattern and chart context was exercised through the real private source in a restricted local bridge; it is not present in public-only mode. Existing missing families and incomplete family fixtures/invalidation/calibration remain open. Broad pattern detection completeness, independent future-outcome predictive validity, verified event coverage and profitability are not established.
