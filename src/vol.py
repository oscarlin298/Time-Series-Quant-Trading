"""Ex ante volatility estimator (Moskowitz-Ooi-Pedersen eq. 1).

Exponentially weighted annualised volatility from DAILY returns, used to
size each position to a constant target vol. The EWMA weights (1-delta)*delta^i
have a center of mass of 60 days (the paper's delta ~ 0.983). Annualised by 261.
"""
import numpy as np

TRADING_DAYS = 261
COM = 60  # center of mass of the EWMA weights, in days: delta/(1-delta) = 60


def ex_ante_vol(daily, com=COM, trading_days=TRADING_DAYS, min_periods=60):
    """Annualised ex ante volatility per instrument, from daily returns.

    sigma^2_t = 261 * EWMA[(r - rbar)^2], where rbar is the EWMA mean of returns
    under the same weighting. Returns annualised volatility (sigma), not variance.

    NOTE on look-ahead: this returns the estimate using data through each day
    inclusive. The one-step lag (size month t using the vol known *before* t)
    is applied at the combination step, so ALL lagging lives in one place —
    same discipline as the signal module.
    """
    ewm_mean = daily.ewm(com=com, min_periods=min_periods).mean()
    sq_dev = (daily - ewm_mean) ** 2
    ewm_var = sq_dev.ewm(com=com, min_periods=min_periods).mean()
    return np.sqrt(trading_days * ewm_var)


def monthly_vol(daily):
    """Sample the daily ex ante vol at each month-end -> monthly sizing input."""
    vol = ex_ante_vol(daily)
    return vol.resample("ME").last()


if __name__ == "__main__":
    from data import load_prices, daily_returns

    daily = daily_returns(load_prices())
    vol = monthly_vol(daily)

    print("Monthly vol table:", vol.shape, "(months x instruments)")
    print("\nMost recent annualised vol estimates (0.15 = 15%):")
    print(vol.tail(3).round(3))