import os
from web3 import Web3
import asyncio

RPC_HTTP = "https://eth-mainnet.g.alchemy.com/v2/4T2FGg31ChPTZ2bQML9iW"
w3 = Web3(Web3.HTTPProvider(RPC_HTTP))

def is_addr_eth(addr):
    return addr.startswith("0x")

def fetch_balance_eth(addr):
    balance_wei = w3.eth.get_balance(addr)
    return w3.from_wei(balance_wei, "ether")

async def get_balances_eth(addresses: list[str]) -> dict[str, int]:
    """Асинхронно получаем балансы всех адресов."""
    tasks = [asyncio.to_thread(fetch_balance_eth, a) for a in addresses]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(addresses, results))

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