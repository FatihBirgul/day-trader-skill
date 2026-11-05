# Historical research validation

The existing `strategy_backtest` and Time Machine `first_exit` are reused. Entries use only prefix candles before next-bar open; BUY/SELL executable prices use explicit bid/mid basis, fixed spread, adverse stop gaps, slippage/commission and stop-first same-bar ambiguity. A position closes once. Independent strategy comparisons remain separate simulations, rather than counting overlapping tags as independent performance.

V5 adds dataset content hash, explicit strategy version/cost units, R equity curve, closure/type checks, boundary-crossing label disclosure and development metrics limited to outcomes completed before holdout. Legacy entry-partition development/holdout fields remain available; development entries that exit in holdout must not be used as isolated training labels. The raw dataset hash proves content equality, not source/license/finality authenticity.

Rolling evaluation now starts each fold flat at its evaluation boundary. Training-prefix open positions cannot change which test trades are admitted. A regression compares every fold with an independent simulation beginning at that boundary. Existing future-extension invariance, chronological multi-trade, BUY/SELL cost and gap tests remain. Fold metrics are separate; no continuous OOS equity is fabricated.

Seeded trade-return bootstrap now also reports drawdown and losing-streak quantiles, plus small-sample warnings. Empty samples have null distributions. Bootstrap percentiles are empirical resampling, not success probabilities or a profitability guarantee.

Important limits: this public path is fixed-rule rolling evaluation, not train/select/freeze/test optimization or general purged CV. Private OOS research was inspected and its original isolated tests passed; its market/product/ledger contracts prevent direct Forex reuse. It was not rewritten or bypassed. Full FX OOS integration, broker risk-percent account equity, point-in-time rules/fees, intrabar spread and verified historical FX datasets/licenses remain PARTIAL/BLOCKED. No synthetic fixture result is presented as market performance.

Commands: `python -m unittest discover -s tests -p test_research.py -q` and full Python 3.10/3.12 suite. Separate original private tests run only with socket/DNS denial and temporary-root SQLite access.
