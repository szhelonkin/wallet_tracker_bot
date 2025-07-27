import asyncio
import datetime
import json, sqlite3, time
from web3 import Web3
from compound import fetch_comet_position
from db import init_db_sync, add_address, remove_address, list_addresses, filter_btc_addresses, filter_eth_addresses, list_addresses_all

COMET    = Web3.to_checksum_address("0x3Afdc9BCA9213A35503b077a6072F3D0d5AB0840")

async def main() -> None:
    addrs = await list_addresses_all()
    eth_addrs = filter_eth_addresses(addrs)
    result = {
        "addresses": {},
        "time": f"{datetime.datetime.now()}"
    }
    for addr in eth_addrs:
        base_symbol, supplied, borrowed, positions = fetch_comet_position(COMET, Web3.to_checksum_address(addr))
        payload = {
            "ts": int(time.time()),
            "base_symbol": str(base_symbol),
            "supplied": str(supplied),       # str, чтобы избежать проблем с Decimal
            "borrowed": str(borrowed),
            "collats": [(sym, str(amt)) for sym, amt in positions],
        }
        result["addresses"][addr] = payload

    with open("./cache_compound.json", "w") as f:
        json.dump(result, f)

if __name__ == "__main__":
    asyncio.run(main())
