"""Minimal IBKR connection test.

Requires TWS paper trading or IB Gateway to be running locally with API enabled.
This script only connects and prints account summary info. It does not place orders.
"""

from ib_insync import IB


HOST = "127.0.0.1"
PORT = 7497      # TWS paper default
CLIENT_ID = 1


def main():
    ib = IB()

    print(f"Connecting to IBKR at {HOST}:{PORT} with clientId={CLIENT_ID}...")

    ib.connect(HOST, PORT, clientId=CLIENT_ID)

    try:
        print("Connected:", ib.isConnected())

        accounts = ib.managedAccounts()
        print("Managed accounts:", accounts)

        summary = ib.accountSummary()

        print("\nAccount summary:")
        for row in summary:
            if row.tag in {"NetLiquidation", "TotalCashValue", "AvailableFunds", "BuyingPower"}:
                print(f"{row.tag}: {row.value} {row.currency}")

    finally:
        ib.disconnect()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()