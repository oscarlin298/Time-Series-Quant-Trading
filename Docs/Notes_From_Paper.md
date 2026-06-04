# Notes from the paper: Time Series Momentum (Moskowitz, Ooi, Pedersen, 2012)

Running notes as I read. Goal: understand the mechanics well enough to write a precise signal spec, cost assumptions, and reproduction success criteria. Move these into the GitHub repo once it exists (this is also good first Git practice: one commit per chunk).

---

## 1. Two separate time axes (do not confuse these)

- **Lookback:** how far back the signal looks to decide direction. Their signal = the sign of the past **12-month** return.
- **Holding period:** how long you hold after deciding. Headline strategy holds **1 month**, then re-forms.

These are different parameters. Confusing them breaks everything downstream.

## 2. The core finding on horizons

Regressing each month's return on its own return lagged h months (h = 1 ... 60):

- **Lags 1 to 12 months: positive.** Past positive return predicts future positive return. This is the trend/continuation. This is where the profit lives.
- **Lags beyond ~12 months (years 2 to 5): negative.** Returns from 2 to 5 years ago predict the opposite direction now. This is the reversal, strongest in the year right after the momentum year.

Strategy works best when both lookback and holding period are **12 months or less**. 12-month lookback is the sweet spot.

## 3. Do we trade the reversal beyond 12 months? No.

- The reversal is documented as **evidence**, not as a strategy to trade. It supports the behavioural story: initial under-reaction (trend), then partial over-reaction/correction (reversal).
- We don't build an opposite/contrarian position because:
  1. The reversal is **weaker and noisier** than the momentum (smaller, less consistent coefficients).
  2. We **re-form monthly** off a fresh 12-month signal, so we never hold a stale position long enough to ride it into the reversal zone. If a trend dies or flips, next month's signal reflects it and we exit/reverse naturally.
- Where the reversal DOES bite: if you use too **long a lookback** (e.g. 36 months), part of the window sits in the reversal zone, so the signal becomes part-trend, part-contrarian, they fight, performance degrades. This is why long lookbacks underperform and why we keep the lookback short.
- **Takeaway:** the reversal is the *reason we keep the lookback at 12 months*, not something we trade.

## 4. The three-component decomposition (why momentum exists, mechanically)

Momentum profit decomposes into three possible sources:

- **Autocovariance (own-serial dependence):** an asset's own past return predicts its own future return. "True" trending within each series.
- **Serial cross-correlations (lead-lag between assets):** one asset's past return predicts a *different* asset's future return. Cross-asset spillover.
- **Variation in mean returns (cross-sectional dispersion in averages):** some assets just have higher long-run averages; a strategy tilted toward them looks profitable even with zero predictability. A static effect, not real momentum.

**Finding:** positive **own-autocovariance** drives almost everything. The other two are small. (Lead-lag is actually the "wrong" sign for explaining time-series momentum.)

Why this matters for us:
- Validates the **time-series** approach: we trade each instrument on its *own* trailing return, which is exactly the mechanism that does the work.
- Confirms the effect is genuine **predictability**, not a relabelled long bias (which is what it would be if the mean-dispersion term dominated).

## 5. Why lower-frequency (monthly) data

- It's a defence against **market microstructure contamination**. Daily/weekly predictability in equities is partly fake, an artefact of stale prices and bid-ask bounce, not real tradeable predictability.
- Their move: use **liquid futures** (not individual stocks) and **lower-frequency monthly** data to mitigate this. So the trend they measure is real economic predictability, not a measurement artefact.

## 6. CRITICAL data nuance: daily-in, monthly-out

Two frequencies for two jobs:

- **Signal and returns: monthly.** 12-month lookback return, 1-month hold, monthly rebalance.
- **Volatility estimate: built from DAILY data.** Position sizing scales by each instrument's ex ante volatility, estimated from daily returns (exponentially weighted, ~60-day centre of mass). Uses the vol estimate from the prior day to size the current position (no look-ahead).

**Implication for Oscar's data pipeline:** we need **daily prices** as the raw input, then compound up to monthly returns for the signal. Do NOT just pull monthly data, or the vol sizing will be wrong.

---

## 7. Phase-two evaluation: the factor regression (not needed in phase one)

The regression `r_TSMOM = a + b1·MKT + b2·BOND + b3·GSCI + s·SMB + h·HML + m·UMD + e` is **not part of the strategy**. It's an evaluation tool, run *after* we have a return stream, to answer: is our return just repackaged exposure to things already known, or is there something left over?

Read it as a sentence: regress our monthly strategy return on a list of known return sources (stock market, bond market, commodities, and the Fama-French size/value/momentum factors).

What we read from the output:
- **Betas:** how much of our return is explained by each known factor. A big UMD beta would mean we're basically just cross-sectional momentum in disguise. Small betas = not simply a known exposure.
- **Alpha (the intercept):** the average return left over *after* the known factors take their share. A large, significant alpha = genuine return the standard factors don't explain. This is what makes TSMOM interesting rather than a rebrand.

Its job is to stop us fooling ourselves: the difference between "we made money" and "we made money for a reason that isn't already on the menu."

When we run it:
- **Phase one: NO.** Phase one is about whether the return *exists* (Sharpe, drawdown, equity curve, net of costs), not whether it's *explained*. Don't bolt this on early.
- **Phase two: YES, a simplified version.** Once we have a clean return stream, regress against a few benchmarks (even just the equity market plus one or two factors) to check we're not secretly just long equities or just the momentum factor. Factor data (SMB, HML, UMD) is free from Ken French's website.
- **Track record:** being able to show "our return has alpha to the standard factors, it's not disguised beta" is exactly the rigour that beats a pretty backtest in a macro interview.

**Honest caveat:** a significant alpha means "not explained by *these* factors," NOT "definitely real free money." It could still be a risk premium for something the factors don't capture. Stay careful about this, as the paper does. But it's a far stronger result than no test at all.

## Project horizon note

This is a durable, multi-phase project, not a weekend experiment. Implications:
- Build for longevity: the signal-agnostic engine and the four-stage ladder exist precisely because we intend to run this live for a sustained period.
- It's fine for phases to take months. Doing each rung properly (especially paper trading through real market events) is the point, not speed.
- Capture understanding as we go (this file). The notes compound; by the time we write the formal spec and run phase-two evaluation, we're assembling things we already understand rather than starting cold.

## Confirmed spec inputs (from the paper)

### 1. Ex ante volatility estimator (Section 2.4, eq. 1)
- Annualised variance: `σ²_t = 261 · Σ_i (1−δ)·δ^i · (r_{t−1−i} − r̄_t)²`, summed over past days i.
- `261` annualises (trading days/year). Weights `(1−δ)·δ^i` decay geometrically into the past and sum to one (recent days weighted more). `r̄_t` is the exponentially weighted mean return.
- Parameter: δ chosen so the centre of mass of the weights = δ/(1−δ) = **60 days**. Solving gives **δ ≈ 0.983**.
- Design choices to replicate: **same vol model for all assets at all times**; use the **t−1 estimate applied to time-t returns** (no look-ahead).

### 2. Position-sizing constant (Section 4.1)
- Each position sized to **40% ex ante annualised volatility**: position size = **40% / σ_{t−1}**.
- Reasoning (theirs): the 40% is **inconsequential** (it just scales everything, doesn't change the Sharpe); chosen because it's ~the risk of an average single stock, and equal-weighting across securities then gives the TSMOM factor ~**12% annualised vol**, comparable to other common factors.
- Takeaway for us: don't agonise over the constant. It scales P&L, not Sharpe.

### 3. Instrument universe and sample (Table 1 + Appendix A)
- Full universe: **24 commodities, 12 cross-currency pairs (9 underlying currencies), 9 developed equity indexes, 13 developed government bond futures**. Full sample **Jan 1965 – Dec 2009**.
- Main evaluation uses the sample from **1985 onward** (better breadth and liquidity), even though some series start in 1965. **Use 1985+ as the cleaner reproduction window.**
- Table 1 lists each instrument's individual start date. **Pick our reduced reproduction set from instruments with early start dates** (long histories).

### 4. Cost treatment — IMPORTANT GAP
- The paper reports **GROSS returns**. There is **no detailed transaction-cost model** in the headline results. Closest they come: noting modest margin use, arguing implementability at scale, and focusing on liquid instruments to keep costs low.
- Implications for us:
  1. Their published Sharpe figures are **gross**, so our **gross** numbers should roughly match theirs. Then we subtract **our own cost model** to get an honest net figure.
  2. The cost assumptions are **entirely our contribution to make** — the realism the paper left out. Build them conservatively. This is the most "ours" part of the project.