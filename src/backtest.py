"""The backtest engine: combine signal x size, apply the no-look-ahead lag,
multiply by next month's returns, subtract costs, produce the return stream.

This is the integration layer ("one brain, three harnesses" — this is the
backtest harness). It imports the ingredient modules and wires them together.
The single most important line is the .shift(1) lag (step 3): it is what
prevents look-ahead. signals.py and vol.py deliberately left the lag out and
pointed here, so ALL lagging lives in this one place.
"""
import numpy as np
import pandas as pd

from data import load_prices, daily_returns, monthly_returns, remove_roll_jumps
from signals import momentum_signal
from vol import monthly_vol
from costs import trading_costs

TARGET_VOL = 0.40  # size each position to 40% ex ante annual vol (spec Section 5)


def run_backtest(monthly_rets, signal, vol, target_vol=TARGET_VOL):
    """Run the diversified TSMOM backtest and return a results DataFrame.

    Inputs (all monthly, same index = months, same columns = instruments):
      monthly_rets : actual realised monthly returns per instrument
      signal       : +1 / -1 / 0 direction per instrument per month
      vol          : annualised ex ante vol per instrument per month
    """

    # --- Step 1+2: turn the signal into a vol-scaled position --------------
    # direction * (target_vol / vol). High-vol instruments get smaller
    # positions so every position carries the same ex ante risk.
    position = signal * (target_vol / vol)

    # --- Step 3: THE LAG (no look-ahead) -----------------------------------
    # The position we HOLD over month t was decided using information known
    # only at the end of month t-1. shift(1) moves each position forward one
    # month so it lines up with the return it earns. Without this line the
    # backtest silently uses the future to predict the future. Most important
    # line in the file.
    position = position.shift(1)

    # --- Step 4: gross return per instrument -------------------------------
    # Lagged position times the month's actual return.
    gross_per_instrument = position * monthly_rets

    # --- Step 5: costs (now lives in costs.py) -----------------------------
    # trading_costs charges on the CHANGE in position, not the gross position.
    cost_per_instrument = trading_costs(position)
    net_per_instrument = gross_per_instrument - cost_per_instrument

    # --- Step 6: average across instruments to get the portfolio -----------
    # Equal-weighted across whatever instruments are active that month. mean()
    # skips NaNs, so different start dates and the 12-month warm-up are handled
    # automatically.
    gross = gross_per_instrument.mean(axis=1)
    net = net_per_instrument.mean(axis=1)

    return pd.DataFrame({"gross": gross, "net": net}).dropna()


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
def sharpe(returns, periods_per_year=12):
    """Annualised Sharpe ratio of a monthly return series."""
    return np.sqrt(periods_per_year) * returns.mean() / returns.std()


def max_drawdown(returns):
    """Largest peak-to-trough fall of the cumulative return (as a fraction)."""
    equity = (1 + returns).cumprod()
    running_peak = equity.cummax()
    drawdown = equity / running_peak - 1
    return drawdown.min()


def summarise(results):
    """Print the headline diagnostics, gross and net."""
    for col in ["gross", "net"]:
        r = results[col]
        print(f"  {col:5s}  Sharpe {sharpe(r):5.2f}   "
              f"ann.return {(r.mean() * 12):7.2%}   "
              f"ann.vol {(r.std() * np.sqrt(12)):6.2%}   "
              f"maxDD {max_drawdown(r):7.2%}")


if __name__ == "__main__":
    # Build the inputs from the ingredient modules.
    prices = load_prices()
    daily = remove_roll_jumps(daily_returns(prices))
    monthly_rets = monthly_returns(daily)

    signal = momentum_signal(monthly_rets)
    vol = monthly_vol(daily)

    # Align everything to the same monthly index/columns before combining.
    vol = vol.reindex_like(monthly_rets)
    signal = signal.reindex_like(monthly_rets)

    results = run_backtest(monthly_rets, signal, vol)

    print("\nDiversified TSMOM — diagnostics:")
    summarise(results)
    print(f"\nReturn stream: {len(results)} months, "
          f"{results.index.min().date()} -> {results.index.max().date()}")