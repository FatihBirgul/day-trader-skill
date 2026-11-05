# Forex financial validation

Existing V4 BUY ask / SELL bid entries, broker tick rounding, executable bid/ask research conversion, stop-first ambiguity and broker lot-grid controls are retained. The sizing function rejects a positive/zero broker stop result both at its minimum-lot sample and at the final proposed lot. A large commission must not disguise a positive final broker profit as a loss.

New optional risk allowances: `commission_per_lot` is total round-trip commission in account currency per lot; `slippage_price` is adverse stop execution price movement. Both default to zero for compatibility and must be finite/nonnegative. BUY loss uses stop minus allowance; SELL uses stop plus allowance. These are assumptions, not verified historical commissions. Spread is already present in executable entry/exit prices and is not added again.

Independent cost oracle: $100 loss per lot for a $1 movement of a 100oz XAU contract, $10 adverse stop allowance and $5 commission = $115 per lot. A $100 budget with 0.01 grid allows 0.86 lot/$98.90. BUY/SELL tests verify the same result and the actual broker calculation price. Other regression tests reject minimum-lot over-budget, wrong currency, nonfinite/negative costs and inconsistent broker profit signs.

Contract-size/tick-value variants remain provider supplied. Unknown contract metadata or account currency cannot be used to invent a lot. Margin, leverage, swap, true intrabar spread and gap loss beyond the allowance remain unverified; missing fields stay explicit. No margin/execution permission is inferred from sizing. Gap losses can exceed planned risk in historical simulations.

Commands: `python -m unittest discover -s tests -p test_financial_v5.py -v`; existing financial tests in test_forex, test_microstructure and test_policy remain in the full suite. Real Windows MT5/account/contract validation: UNVERIFIED.
