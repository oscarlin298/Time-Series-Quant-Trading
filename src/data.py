"""Pull daily prices for the TSMOM universe, save CSVs, and build returns.

Daily in, monthly out: daily returns feed the volatility estimator,
monthly returns feed the 12-month momentum signal.
"""
import yfinance as yf
import pandas as pd
from pathlib import Path

# name -> Yahoo ticker. Bonds (UK/DE) omitted: no clean free source yet.
UNIVERSE = {
    "AUDUSD": "AUDUSD=X",
    "EURUSD": "EURUSD=X",
    "USDJPY": "JPY=X",      # USD/JPY — inverted to JPY/USD in load_prices()
    "GBPUSD": "GBPUSD=X",
    "SP500":  "^GSPC",
    "FTSE100": "^FTSE",
    "NIKKEI": "^N225",      # TOPIX proxy
    "UST10Y": "ZN=F",
    "CRUDE":  "CL=F",
    "GOLD":   "GC=F",
    "COPPER": "HG=F",
}

# Instruments whose price needs inverting to match the spec's quote convention.
INVERT = {"USDJPY": "JPYUSD"}  # Yahoo gives USD/JPY; spec wants JPY/USD

# Futures columns only — these are the ones with roll gaps to clean.
# (FX and equity indices are spot/index series with no roll.)
# Names here are post-INVERT, i.e. as they appear in the price table.
FUTURES = ["UST10Y", "CRUDE", "GOLD", "COPPER"]

OUT = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)


def fetch(name, ticker, start="1980-01-01"):
    """Download one instrument's daily history and save a clean CSV."""
    df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    if df.empty:
        print(f"  WARNING: no data for {name} ({ticker})")
        return
    # Flatten yfinance's multi-level columns -> plain Open/High/Low/Close/Volume
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "Date"
    df.to_csv(OUT / f"{name}.csv")
    print(f"  {name}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")


def load_prices():
    """Read every CSV in data/raw and return one aligned daily Close-price table."""
    series = {}
    for path in sorted(OUT.glob("*.csv")):
        name = path.stem
        df = pd.read_csv(path, index_col="Date", parse_dates=True)
        close = df["Close"]
        # Mask non-positive prices (e.g. WTI crude went to -$37 on 2020-04-20):
        # such prices are unrepresentable for returns/momentum, so treat as missing.
        close = close.where(close > 0).dropna()
        if name in INVERT:          # USD/JPY -> JPY/USD
            close = 1.0 / close
            name = INVERT[name]
        series[name] = close
    # Outer-join on dates: union of all trading days, NaN where an instrument has no data.
    prices = pd.DataFrame(series).sort_index()
    return prices


def daily_returns(prices):
    """Simple daily returns. NaNs are kept, not filled (no fake flat days)."""
    return prices.pct_change()


def remove_roll_jumps(daily, futures=FUTURES, n_sigma=5, window=60):
    """Blank out suspected futures roll gaps.

    A roll gap shows up as a one-day return far larger than the instrument's
    normal daily move. We flag any daily return more than n_sigma rolling
    standard deviations from zero and treat it as missing (NaN) rather than a
    real return. Auto-scales per instrument via each one's own volatility.

    APPROXIMATION (documented deviation from spec): the spec wants returns
    chained within individual contracts. Yahoo only gives a pre-stitched
    continuous series, so we cannot do that here. This jump-removal is a
    cheap first-pass substitute. Proper fix = individual-contract data via a
    real vendor / IBKR feed in phase two.

    Only applied to the FUTURES columns — FX and equities have no roll, and
    cleaning them would risk deleting genuine large market moves.
    """
    cleaned = daily.copy()
    cols = [c for c in futures if c in cleaned.columns]
    rolling_std = cleaned[cols].rolling(window, min_periods=20).std()
    print("rolling_std non-NaN counts:\n", rolling_std.notna().sum())
    print("daily non-NaN counts:\n", cleaned[cols].notna().sum())
    too_big = cleaned[cols].abs() > (n_sigma * rolling_std)
    cleaned[cols] = cleaned[cols].mask(too_big)
    # Report how many days were flagged per instrument (sanity check on n_sigma:
    # a few per decade = good; dozens = threshold too low, eating real moves).
    flagged = too_big.sum()
    print("\nRoll-jump days flagged (futures only):")
    print(flagged.to_string())
    return cleaned


def monthly_returns(daily):
    """Compound daily returns up to month-end. TODO: make excess of risk-free rate."""
    return (1 + daily).resample("ME").prod() - 1


if __name__ == "__main__":
    # Comment out this loop once the CSVs exist, to skip re-downloading.
    for name, ticker in UNIVERSE.items():
        print(f"Fetching {name}...")
        fetch(name, ticker)

    prices = load_prices()
    daily = daily_returns(prices)
    daily = remove_roll_jumps(daily_returns(prices)) # clean roll gaps before compounding
    monthly = monthly_returns(daily)

    print("\nPrice table:", prices.shape, "(rows x instruments)")
    print(prices.tail(3))
    print("\nMonthly returns tail:")
    print(monthly.tail(3).round(4))