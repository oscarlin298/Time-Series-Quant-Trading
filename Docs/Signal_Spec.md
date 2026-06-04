# Signal Spec: 12-Month Time Series Momentum (TSMOM)

 **Source:** Moskowitz, Ooi, Pedersen (2012).

This is the build spec for the phase-one reproduction. It must be precise enough that Oscar never has to guess. Anything marked **[DECIDE]** is a judgement call Shoron fills in before handing over. Everything else is confirmed from the paper.

---

## 1. Purpose and scope

Reproduce the core diversified TSMOM strategy on a reduced universe of liquid instruments, matching the paper's **gross** performance first. Costs are layered on separately (Section 8) to produce an honest net figure. We are not inventing anything here; we are proving the engine and signal are correct.

## 2. Data requirements

**Daily in, monthly out.** This is critical: do not pull monthly data only.

- **Raw input:** daily settlement/closing prices per instrument, as a continuous (roll-adjusted) series for futures.
- **Daily excess returns:** compute daily returns, in excess of the risk-free rate where applicable.
- **Monthly returns:** compound daily excess returns up to monthly for the signal.
- **Roll adjustment [DECIDED]:** Fixed-schedule roll **3 trading days before expiry** (roll out of the front contract while it's still liquid). **Returns are chained within each contract** — we never compute a return that spans a roll day, which matches the paper's approach and sidesteps the roll-gap problem entirely. For any continuous price series used for volatility estimation or display, use **ratio (proportional) back-adjustment** (scales rather than shifts, so no negative-price artefacts and correct in return terms). State this explicitly in code comments; it quietly drives a large part of the result.
- **Universe [DECIDED]:** 13 instruments, optimised for **diversification across distinct macro drivers** (across asset classes matters more than breadth within one) and for **long histories** (early start dates give a genuine out-of-sample). This is the **target set**; if clean daily data is unavailable for any, substitute while preserving the principle: keep all four asset classes represented and do not let the set collapse into mostly commodities.

  | Class | Instruments | Start dates |
  |---|---|---|
  | FX (4) | AUD/USD, EUR/USD (DEM spliced to EUR), JPY/USD, GBP/USD | ~1971–72 |
  | Equity index (3) | S&P 500, FTSE 100, TOPIX | 1965 / 1975 / 1976 |
  | Bonds/rates (3) | 10-year US, 10-year UK, 10-year Germany (Euro Bund) | ~1979 |
  | Commodities (3) | Crude, Gold, Copper | 1983 / 1969 / 1977 |

  Rationale: all four classes represented; three distinct commodity complexes (energy / precious / industrial) rather than three correlated grains; mostly pre-1985 starts so the 1985+ reproduction window still leaves earlier data for out-of-sample; FX carries no roll issue and financials carry small roll gaps, so only the three commodities make the roll method bite hard.
- **Sample window:** 1985 onward (cleaner breadth/liquidity), per the paper.

## 3. The signal

For each instrument `s` and each month `t`:

- Compute the trailing **12-month** excess return, `r^s_{t-12, t}`.
- **Direction = sign of that return.** Positive: go long. Negative: go short.
- Hold for **1 month**, then re-form next month off a fresh 12-month signal.

No other lookback, no reversal trading. (Reversal beyond 12 months is evidence, not a position. See notes file.)

## 4. Ex ante volatility estimator (paper eq. 1)

Used for position sizing. Estimated from **daily** returns.

```
σ²_t = 261 · Σ_{i=0}^∞ (1−δ)·δ^i · (r_{t-1-i} − r̄_t)²
```

- `261` = trading days per year (annualises the variance).
- Weights `(1−δ)·δ^i` decay geometrically and sum to one.
- `r̄_t` = exponentially weighted mean return (same weighting scheme).
- **δ ≈ 0.983**, set so the centre of mass = δ/(1−δ) = **60 days**.
- **Same model for all instruments, all dates.**
- **No look-ahead:** use the estimate computed through `t−1` to size the position held over `t`. Implement as a clear one-step lag; Oscar to confirm the lag is correct in code.

## 5. Position sizing

Per instrument, size to a constant **40% ex ante annualised volatility**:

```
position size_s = 40% / σ^s_{t-1}
```

The single-instrument TSMOM return is therefore:

```
r^{TSMOM,s}_{t,t+1} = sign(r^s_{t-12,t}) · (40% / σ^s_{t-1}) · r^s_{t,t+1}
```

Note: the 40% constant is **inconsequential to the Sharpe** (it only scales P&L). Do not tune it.

## 6. Portfolio aggregation

Diversified TSMOM = equal-weighted average across all `S_t` instruments available at time `t`:

```
r^{TSMOM}_{t,t+1} = (1 / S_t) · Σ_{s=1}^{S_t} sign(r^s_{t-12,t}) · (40% / σ^s_{t-1}) · r^s_{t,t+1}
```

Also produce per-asset-class TSMOM (FX, rates, equity, commodity) the same way, for diagnostics.

## 7. Rebalancing

- Monthly. Recompute signal and vol-scaled sizes each month.
- Single time series of monthly returns, **no overlapping observations** (since holding period = 1 month, this is straightforward).

## 8. Cost model (layered separately — OURS to build)

The paper reports **gross**. This section is our contribution and the realism the paper left out. **Stay pessimistic: a backtest that survives pessimistic costs is trustworthy; one that only survives optimistic costs is fiction.** Numbers below are conservative estimates for retail execution on liquid contracts, to be replaced with real broker figures later (see notes).

Costs expressed in **basis points of notional traded**, so they scale with position size.

| Class | Spread + commission (bps/trade) | Slippage (bps) | Roll | Notes |
|---|---|---|---|---|
| FX (AUD, EUR, JPY, GBP) | 2 | 1 | negligible | cheapest; forwards roll cheaply |
| Equity index (S&P, FTSE, TOPIX) | 3 | 1 | quarterly, small | very liquid |
| Bonds/rates (10y US, UK, DE) | 4 | 1 | quarterly, small | liquid, tight |
| Commodities (crude, gold, copper) | 10 | 1 | monthly, material | widest spreads; lean high |

**Application rules (important):**
1. **Cost the CHANGE in position, not the gross position.** Each month, if the signal stays the same and vol-scaling barely changes size, we only trade the small delta and only pay cost on that delta. This is what makes our low-turnover strategy cheap. Engine must cost the position *delta*, not the full position.
2. **Model roll as explicit extra trades.** Each roll = close front contract + open next = one round-trip of spread cost, added on the roll schedule (3 trading days before expiry). Material for commodities (monthly roll), negligible for FX.
3. **Slippage is a 1 bp humility buffer** on top of spread for everything. At our size real slippage is near zero, but it costs nothing to be conservative and it matters if we scale.

**Honesty notes:**
- These are **estimates pending real broker data**. Once the IBKR account exists, replace them with (a) IBKR's **published commission schedule** per contract, and (b) the **observed bid-ask spread** read live off the platform for each specific contract we trade. "Observed broker spread + published commissions" is far more accurate and defensible than an estimate. **Follow-up task for phase two.**
- **Always report gross and net side by side**, never net alone, so we can see exactly how much costs eat.

## 9. Required outputs / diagnostics

- Equity curve (log scale), gross and net.
- Annualised return, annualised volatility, **Sharpe ratio** (gross and net).
- Maximum drawdown.
- Turnover.
- Per-instrument and per-asset-class breakdowns.
- All computed separately for the in-sample and the held-out out-of-sample windows.

## 10. Reproduction success criteria (LOCKED — do not change)

**Locked before any results exist. The point is that it is fixed in advance.**

Reproduction succeeds if all three hold on the in-sample window (1985+):

1. **Headline:** the diversified portfolio's **gross** annualised Sharpe lands in **0.8 to 1.2**. (Paper achieved >1 gross on the full 58-instrument universe; our reduced 13-instrument set should land near it, allowing for fewer independent bets and data differences. Below ~0.8 or well above ~1.2 signals a problem to investigate, e.g. a bug or look-ahead inflating it.)
2. **Sign condition:** each asset class (FX, equity, rates, commodities) shows a **positive** gross Sharpe on its own. The paper's thesis is the effect appears in every class; a negative class is a flag.
3. **Sanity condition:** drawdowns and the equity curve look plausible, with no single month or instrument dominating the result.

**How to treat a miss (critical discipline):**
- A miss is a **diagnostic tripwire**, not a project failure. It means *stop and investigate*.
- **Investigate the ENGINE:** look-ahead bugs, roll errors, costing the gross position instead of the delta, data problems. Fix and rerun. This is healthy iteration.
- **Do NOT tweak the strategy to hit the number** (changing lookback, dropping instruments that hurt, adjusting the vol window *because* it lifts in-sample Sharpe). That is overfitting disguised as iteration, and it is how backtests lie.
- The **out-of-sample window stays sealed** until we genuinely believe we're done. It is the final honest test and the thing that lets us iterate freely on the engine without fooling ourselves.

**Locked on:** [DATE — fill when committed]. Do not edit after this date.

## 11. Architecture reminder (for Oscar)

Build this **signal-agnostic** (one brain, three harnesses): the signal logic must not know whether it's fed historical, paper, or live data. The backtester is just the first harness. See the main plan document.

---

## Checklist before handing to Oscar

- [x] Universe chosen and listed (Section 2)
- [x] Roll method decided (Section 2)
- [x] Cost assumptions filled (Section 8)
- [x] Success criteria locked and dated (Section 10)