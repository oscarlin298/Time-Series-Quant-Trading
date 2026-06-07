"""Load monthly short-rate data for FX carry.

First-pass carry data uses FRED/OECD 3-month interbank rates as a proxy for
currency carry. This is not as clean as forward points, but it is free,
consistent across currencies, and good enough for a v1 carry sleeve.
"""

import pandas as pd
from pandas_datareader import data as web


FRED_RATES = {
    "AUD": "IR3TIB01AUM156N",
    "EUR": "IR3TIB01EZM156N",
    "JPY": "IR3TIB01JPM156N",
    "GBP": "IR3TIB01GBM156N",
    "USD": "IR3TIB01USM156N",
}


def fetch_fred_rates(start="1994-01-01"):
    """Fetch monthly 3-month interbank rates from FRED.

    Returns rates in decimal form, e.g. 5% becomes 0.05.
    """
    frames = []

    for currency, code in FRED_RATES.items():
        series = web.DataReader(code, "fred", start)
        series = series.rename(columns={code: currency})
        frames.append(series)

    rates = pd.concat(frames, axis=1).sort_index()

    # FRED gives rates as percentages, so convert 5.0 -> 0.05
    rates = rates / 100.0

    return rates


def save_rates(path="data/rates/fred_rates.csv"):
    """Fetch FRED rates and save them locally."""
    rates = fetch_fred_rates()
    rates.to_csv(path)
    print(f"Saved rates to {path}")
    print(rates.tail())
    return rates


def load_rates(path="data/rates/fred_rates.csv"):
    """Load saved FRED rates from CSV."""
    return pd.read_csv(path, index_col=0, parse_dates=True)


if __name__ == "__main__":
    save_rates()