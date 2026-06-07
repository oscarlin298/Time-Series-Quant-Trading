"""Trading cost model: per-instrument costs charged on position turnover.

Costs are in basis points per unit of position change (the spec's cost table).
Charged on the CHANGE in position, not the gross position — that is what keeps
a low-turnover strategy cheap. Placeholder estimates pending real IBKR figures
(see signal-spec Section 8).
"""
import pandas as pd

# Per-class cost in basis points per unit of position change.
# (Names are post-INVERT, i.e. as they appear in the price/position tables.)
COST_BPS = {
    "AUDUSD": 2, "EURUSD": 2, "JPYUSD": 2, "GBPUSD": 2,   # FX
    "SP500": 3, "FTSE100": 3, "NIKKEI": 3,                # equity index
    "UST10Y": 4,                                          # bond
    "CRUDE": 10, "GOLD": 10, "COPPER": 10,                # commodities
}


def trading_costs(position, cost_bps=COST_BPS):
    """Cost per instrument per month, charged on the change in position.

    position : the (already lagged) position grid, months x instruments.
    cost_bps : per-instrument cost in basis points (defaults to COST_BPS).
    Returns  : a grid of costs, same shape as position, to subtract from
               gross returns.
    """
    # Convert costs from basis points to decimals (1 bp = 1/10,000), as a
    # labelled Series so it aligns with the position columns by instrument name.
    cost_decimal = pd.Series({k: v / 1e4 for k, v in cost_bps.items()})

    # How much each position changed month-on-month (turnover). abs() because
    # trading in either direction costs the same. Zero change -> zero cost.
    turnover = position.diff().abs()

    # Cost = how much you traded x the per-instrument rate. Pandas aligns the
    # rate to each instrument column automatically by label.
    return turnover * cost_decimal