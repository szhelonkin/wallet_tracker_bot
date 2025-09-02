import os
from web3 import Web3
import asyncio
from rpc_manager import get_web3, get_balance_with_retry

w3 = get_web3()

def fetch_balance_eth(addr):
    try:
        balance_wei = get_balance_with_retry(addr)
        return w3.from_wei(balance_wei, "ether")
    except Exception as e:
        print(f"Error getting ETH balance for {addr}: {e}")
        return 0

async def get_balances_eth(addresses: list[str]) -> dict[str, int]:
    """Асинхронно получаем балансы всех адресов."""
    # Use the new concurrent method from RPC manager for better performance
    from rpc_manager import get_balances_concurrent
    return await get_balances_concurrent(addresses)

#async def main() -> None:
    #print("eth module")

    #addr = "0x8357b66F74363E926de4186A449f365707c7fbad"
    #print(f"addr {addr} is eth addr {is_addr_eth(addr)} ")

    #addr = "bc1qfa3v3vqjvsymujfk9kn69gys8vjluctsuq0umg"
    #print(f"addr {addr} is eth addr {is_addr_eth(addr)} ")

    #print(fetch_balance_eth("0x8357b66F74363E926de4186A449f365707c7fbad"))
    #print(await get_balances_eth(["0x8357b66F74363E926de4186A449f365707c7fbad","0x0C8eb038c58E0a9d8D66Bf5805A6eC0dfDaE6c4c"]))

#if __name__ == "__main__":
    #asyncio.run(main())