# Systematic Macro Project: Plan, Setup and Overview

 this is the full plan for what we're building and how. Read it end to end. The short version: we're building a systematic macro trading system, learning each other's discipline as we go, with the explicit end goal of running it live on real capital after it has earned the right.

## What we are building, and why

A systematic macro research-and-trading project. Cross-asset, low frequency, on liquid instruments we can both access: G10 FX and a handful of liquid futures (rates, equity index, maybe one commodity). Two signal families to start, no more: **trend** (time-series momentum) and **carry**.

Three priorities, in order:

1. **Learning.** Each of us learning the other's half. learns to build and read the code; learns the macro and the economics behind the signals.
2. **A portable track record.** A research rig and a documented live process we could show a quant or a trading desk without being embarrassed.
3. **Money.** Real but small. Trend and carry are documented risk premia with genuine positive expected return, so net-positive P&L over a long horizon is realistic. Month to month it is noise. We optimise for the first two and let money be downstream.

The end goal is a system that **trades live, on real capital, for a sustained period.** Everything below is designed backwards from that.

## Roles

- owns the engine: data pipeline, backtester, live executor, risk layer, plumbing. But walk  through it so he can read it and eventually modify it.
- owns the signals: defining trend and carry precisely, the macro logic, the regime thinking, the cost and roll assumptions. But he explains them until Oscar can argue the economics back.

## The toolchain: what to install

Standard quant research stack. Nothing exotic.

**Editor**
- VS Code (both of us). Free.
- Extensions: Python (Microsoft), Jupyter, GitLens, Ruff for linting and formatting.

**Language and environment**
- Python 3.11+.
- A virtual environment committed to the repo so we have identical setups. Built-in `venv` plus `requirements.txt` is the reliable baseline; `uv` (Astral) if you'd rather, it's faster and cleaner. Your call, you own the engine.
- Core libraries: `pandas`, `numpy`, `matplotlib`, `scipy`, `statsmodels`, `jupyter`. Add only when actually needed.

**Broker and live API (relevant from day one, see architecture below)**
- Interactive Brokers. One account covers G10 FX and our futures under a single API.
- Python access via `ib_insync` (clean async wrapper) or the native `ibapi`.
- Critical property: the **paper account and live account use the identical API**. We develop and rehearse against paper, then flip one config line to go live. Same code path, simulated money versus real money.

**Version control and code sharing (how we share code)**
- Git for version control, GitHub for hosting. **Private** repo.
- This replaces emailing files or shared drives. Every change tracked, both of us work without overwriting each other, full history is the record.
- Workflow:
  - `git clone` once.
  - Branch per piece of work: `git checkout -b carry-signal`.
  - Commit as you go: `git add`, `git commit -m "message"`.
  - Push: `git push`.
  - Open a Pull Request on GitHub so the other reviews before it merges to `main`. The review is part of the cross-learning.
-  set up the repo and workflow, then walk through it on a call. Him being clumsy with Git for the first fortnight is expected.

**Repo structure**
- `/data` raw and cleaned data (do not commit large or licensed data; use `.gitignore`).
- `/notebooks` Jupyter exploration.
- `/src` the engine as proper `.py` modules: data, signals, backtester, costs, **executor**, **risk**.
- `README.md` how to run it.
- Rule: exploration in notebooks, anything reusable moves into `/src`. Notebooks rot; modules are the asset.

**Tracking the work**
- GitHub Issues. One issue per task. Keep it light.

## Architecture principle (read this twice)

Because the end goal is live trading, the system has to be built for it from the first commit, not retrofitted.

**One brain, three harnesses.** The signal logic is a single module that does not know or care whether it is being fed historical data (backtest), simulated live data (paper), or real live data (live). The backtester, the paper executor and the live executor are just different harnesses wrapped around the same signal brain.

Why this matters: if we end up with one codebase for backtesting and a separate one for live, they drift, and the live system quietly stops matching the thing we validated. Build it signal-agnostic and going live becomes a config change, not a rebuild. This is the single most important design decision in the project.

**A hard risk layer between the signal and the broker.** A separate component that sits in front of the executor and can refuse to send any order that breaches a position limit or a loss limit, independent of what the signal says. This stands between us and a bug emptying the account while we're asleep. It is non-negotiable and it gets built before any real money is involved.

## Phase 1: build the research rig and reproduce a known result

We invent nothing in phase one. First deliverable is a backtester we trust, proven by reproducing a published result. If we cannot match something known, we cannot believe anything novel later.

**Target to reproduce:** time-series momentum (trend) on a basket of liquid futures. Reference: Moskowitz, Ooi and Pedersen (2012), "Time Series Momentum," *Journal of Financial Economics*.

**Instruments:** roughly 10 to 15. G10 FX crosses plus a few liquid futures (a rates future, an equity index future, one commodity). Enough for diversification, few enough to stay legible.

**Data:** daily settlement prices. Start cheap (Stooq, Yahoo, or a low-cost vendor). The hard part is continuous-contract roll adjustment for futures: how you stitch expiring contracts together quietly determines a large part of the backtest result. Wrestling with this is part of the learning.

**First signal (deliberately simple):**
- 12-month time-series momentum. For each instrument, trailing 12-month return: positive go long, negative go short.
- Volatility-scaled sizing: size each position inversely to its recent realised vol (e.g. trailing 60-day), scaled so each targets the same annualised vol (say 10%). Stops one volatile instrument dominating.
- Rebalance monthly. Low frequency keeps costs survivable and keeps live operations tractable.

**Backtester requirements (non-negotiable):**
- Position sizing and volatility targeting.
- Transaction costs modelled pessimistically from day one (spread, commission, slippage, roll). Edge that only exists at zero cost is not edge.
- A held-out out-of-sample period we do not look at until the end.
- Outputs: equity curve, annualised return, annualised vol, Sharpe, max drawdown, turnover.
- Built signal-agnostic per the architecture principle above.

**Success criteria, defined in advance:**
- Before looking at any results, we write down numerically what "reproduced" means: roughly a positive Sharpe in the region the literature reports for diversified TSMOM, net of our cost model, in-sample, with sensible drawdowns.
- Writing this first stops us moving the goalposts. Adjusting the target after seeing results is the tell that we're fooling ourselves.

## The four-stage ladder to live

We go live one rung at a time. Each rung validates a different thing. We do not climb to the next until the current one has proven its thing, including something going wrong and being handled correctly.

**Rung 1: Backtest.** Validates the *idea*. Does the signal have edge on historical data, net of pessimistic costs, out-of-sample?
- *Passed when:* reproduction meets the pre-written success criteria, and the strategy survives out-of-sample net of costs.

**Rung 2: Paper.** Validates the *system*. The actual machinery, running live against a paper account. Same code, simulated money.
- *Passed when:* it has run cleanly through several monthly rebalances and at least one contract roll, the data feed has held up, AND the risk layer has correctly refused a deliberately bad test order. Run long enough to span real market events, not just long enough to see green. A few cycles minimum, ideally through some stress.

**Rung 3: Live, tiny.** Validates *reality*. Real fills, real slippage, real money, in an amount where total loss is genuinely irrelevant.
- *Passed when:* live execution confirms the edge survives real fills, and we can see and explain exactly how much worse live is than paper.

**Rung 4: Live, scaled.** Only if rung 3 confirms the edge survives contact with real execution. Scale as a function of *measured edge and volatility*, never conviction or how much we're willing to lose.

## Week 1 tasks


- Create the private GitHub repo with the structure above and a working Python environment.
- Stand up the backtester skeleton built signal-agnostic: load daily prices, compute returns, apply a placeholder signal, output an equity curve. Just the rails.
- Get one clean futures data series working end to end, including a first pass at roll adjustment.
- Walk through the Git workflow and repo structure on a call.


- Write the precise spec for the 12-month TSMOM signal and the vol-targeting maths, clear enough to implement without guessing.
- Write the cost model assumptions per instrument (spread, commission, slippage, roll) and why.
- Define the numerical reproduction success criteria, in writing, before we run anything.
- Start learning enough Git and Python to read and eventually edit the repo.

## Rules we do not break

1. **Out-of-sample stays untouched** until the end. No peeking.
2. **Costs modelled pessimistically** from day one.
3. **Evaluation criteria set before we look at results.**
4. **One brain, three harnesses.** Signal logic never forks between backtest and live.
5. **Risk layer ships before real money.** It can always veto the signal.
6. **We climb the ladder one rung at a time.** Each rung earns the next, including handling a failure.
7. **We judge the project by process quality and what we learned, not the equity curve.** The moment "we built it to learn" becomes "the backtest says size up," we've lost the plot.
8. **Size is a function of demonstrated edge, not of how much we're willing to lose.**