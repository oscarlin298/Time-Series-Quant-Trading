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
    monthly = monthly_returns(daily)

    print("\nPrice table:", prices.shape, "(rows x instruments)")
    print(prices.tail(3))
    print("\nMonthly returns tail:")
    print(monthly.tail(3).round(4))