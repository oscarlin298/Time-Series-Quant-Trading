"""TSMOM signal: direction from the trailing 12-month return.

This is the signal 'brain' — it takes monthly returns and outputs a
position direction per instrument. It knows nothing about data sources,
sizing, or costs (one brain, three harnesses).
"""
import numpy as np
import pandas as pd


def trailing_12m_return(monthly):
    """Compound the last 12 monthly returns into a trailing 1-year return.

    Needs a full 12 months of history; earlier months are NaN (warm-up).
    """
    return (1 + monthly).rolling(window=12, min_periods=12).apply(np.prod, raw=True) - 1


def momentum_signal(monthly):
    """+1 (long) if trailing 12m return > 0, -1 (short) if < 0, NaN during warm-up.

    The signal at month t is formed from returns *up to and including* month t,
    and is meant to size the position held over month t+1. The one-month lag
    (no look-ahead) is applied later, when we combine signal x size x next return.
    """
    trailing = trailing_12m_return(monthly)
    return np.sign(trailing)

def carry_signal(rates, instruments, base="USD"):
    """FX carry direction: long higher-yielding currency, short lower.

    For a pair quoted FOREIGN/USD (e.g. AUDUSD), the carry of being long is
    the foreign rate minus the USD rate: you earn the foreign rate and fund
    at the USD rate. Positive differential -> long (+1), negative -> short (-1).

    rates       : monthly rate table, columns = currency codes (AUD, EUR, ...),
                  values in decimal (0.04 = 4%).
    instruments : the FX instrument names as they appear in the returns table,
                  e.g. ["AUDUSD", "EURUSD", "GBPUSD", "JPYUSD"].
    base        : the funding currency (USD), subtracted from each rate.

    Returns +1 / -1 per instrument per month, NaN where a rate is missing.
    """

    # --- TRAP 1: date alignment --------------------------------------------
    # FRED dates rates to the 1st of the month; our returns are month-END.
    # Resample to month-end so the rate table lines up with the return table.
    # ('ME' = month-end; .last() takes that month's value.)
    rates = rates.resample("ME").last()

    base_rate = rates[base]

    signals = {}
    for inst in instruments:
        # --- TRAP 2: quote-convention sign ---------------------------------
        # Each instrument name starts with the foreign currency code, e.g.
        # "AUDUSD" -> "AUD", "JPYUSD" -> "JPY". We extract that, then the
        # carry differential is (foreign rate - base/USD rate). The sign of
        # this differential is the long/short direction, and because the pair
        # is quoted FOREIGN/USD, a positive differential correctly means
        # "go long the pair" (long the higher-yielder).
        foreign = inst[:3]            # first 3 letters = foreign currency code
        differential = rates[foreign] - base_rate
        signals[inst] = np.sign(differential)

    return pd.DataFrame(signals)

if __name__ == "__main__":
    from data import load_prices, daily_returns, monthly_returns

    monthly = monthly_returns(daily_returns(load_prices()))
    signal = momentum_signal(monthly)

    print("Signal table:", signal.shape, "(months x instruments)")
    print("\nMost recent signals (+1 long, -1 short):")
    print(signal.tail(3))

    from rates import load_rates   # use your actual rates filename

    rates = load_rates()
    fx = ["AUDUSD", "EURUSD", "GBPUSD", "JPYUSD"]
    carry = carry_signal(rates, fx)
    print("Carry signal tail:\n", carry.tail())