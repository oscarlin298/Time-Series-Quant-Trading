"""TSMOM signal: direction from the trailing 12-month return.

This is the signal 'brain' — it takes monthly returns and outputs a
position direction per instrument. It knows nothing about data sources,
sizing, or costs (one brain, three harnesses).
"""
import numpy as np


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


if __name__ == "__main__":
    from data import load_prices, daily_returns, monthly_returns

    monthly = monthly_returns(daily_returns(load_prices()))
    signal = momentum_signal(monthly)

    print("Signal table:", signal.shape, "(months x instruments)")
    print("\nMost recent signals (+1 long, -1 short):")
    print(signal.tail(3))