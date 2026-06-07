"""Load monthly short-rate data for FX carry using the FRED API.

First-pass carry data uses FRED/OECD 3-month interbank rates as a proxy for
currency carry. This is not as clean as forward points, but it is free,
consistent across currencies, and good enough for a v1 carry sleeve.
"""

import os
from pathlib import Path

import pandas as pd
import requests


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"

FRED_RATES = {
    "AUD": "IR3TIB01AUM156N",
    "EUR": "IR3TIB01EZM156N",
    "JPY": "IR3TIB01JPM156N",
    "GBP": "IR3TIB01GBM156N",
    "USD": "IR3TIB01USM156N",
}

OUT = Path(__file__).resolve().parent.parent / "data" / "rates"
OUT.mkdir(parents=True, exist_ok=True)


def get_fred_api_key():
    """Read the FRED API key from the environment."""
    api_key = os.environ.get("FRED_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing FRED_API_KEY.\n"
            "In PowerShell, run:\n"
            '$env:FRED_API_KEY="your_real_key_here"'
        )

    return api_key


def fetch_fred_series(series_id, api_key, start="1994-01-01"):
    """Fetch one FRED series and return it as a pandas Series."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    }

    response = requests.get(FRED_OBSERVATIONS_URL, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()

    if "observations" not in payload:
        raise RuntimeError(f"Unexpected FRED response for {series_id}: {payload}")

    data = pd.DataFrame(payload["observations"])

    if data.empty:
        return pd.Series(dtype=float, name=series_id)

    values = pd.to_numeric(data["value"].replace(".", pd.NA), errors="coerce")

    series = pd.Series(
        data=values.to_numpy(),
        index=pd.to_datetime(data["date"]),
        name=series_id,
    )

    return series


def fetch_fred_rates(start="1994-01-01"):
    """Fetch monthly 3-month interbank rates from FRED.

    Returns rates in decimal form, e.g. 5% becomes 0.05.
    """
    api_key = get_fred_api_key()

    series_list = []

    for currency, series_id in FRED_RATES.items():
        series = fetch_fred_series(series_id, api_key, start=start)
        series.name = currency
        series_list.append(series)

    rates = pd.concat(series_list, axis=1).sort_index()

    # FRED gives rates as percentages, so convert 5.0 -> 0.05
    rates = rates / 100.0

    return rates


def save_rates(path=OUT / "fred_rates.csv"):
    """Fetch FRED rates and save them locally."""
    rates = fetch_fred_rates()
    rates.to_csv(path)

    print(f"Saved rates to {path}")
    print(rates.tail())

    return rates


def load_rates(path=OUT / "fred_rates.csv"):
    """Load saved FRED rates from CSV."""
    return pd.read_csv(path, index_col=0, parse_dates=True)


if __name__ == "__main__":
    save_rates()