import asyncio
from decimal import Decimal
import requests

API_URL = "https://blockstream.info/api/address/{addr}"  # нужный префикс /api/! :contentReference[oaicite:0]{index=0}

def satoshi_to_btc(value: int) -> str:
    """Красиво конвертируем сатоши → BTC c 8 знаками."""
    return f"{Decimal(value) / Decimal(1e8):.8f} BTC"

def fetch_balance_btc(addr: str) -> int:
    """Запрашиваем баланс адреса в сатоши."""
    resp = requests.get(API_URL.format(addr=addr), timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Документация: поля funded_txo_sum / spent_txo_sum в объектах chain_stats и mempool_stats
    # баланс = получено − потрачено (и в mempool тоже)  :contentReference[oaicite:1]{index=1}
    chain = data["chain_stats"]
    mempool = data["mempool_stats"]

    confirmed = chain["funded_txo_sum"] - chain["spent_txo_sum"]
    unconfirmed = mempool["funded_txo_sum"] - mempool["spent_txo_sum"]

    return confirmed + unconfirmed

async def get_balances_btc(addresses: list[str]) -> dict[str, int]:
    """Асинхронно получаем балансы всех адресов."""
    tasks = [asyncio.to_thread(fetch_balance_btc, a) for a in addresses]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(addresses, results))