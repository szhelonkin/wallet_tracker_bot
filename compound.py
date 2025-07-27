import os
import asyncio
from decimal import Decimal
from web3 import Web3, HTTPProvider

RPC_HTTP = "https://eth-mainnet.g.alchemy.com/v2/4T2FGg31ChPTZ2bQML9iW"
USER     = Web3.to_checksum_address("0x0C8eb038c58E0a9d8D66Bf5805A6eC0dfDaE6c4c")
COMET    = Web3.to_checksum_address("0x3Afdc9BCA9213A35503b077a6072F3D0d5AB0840")

w3 = Web3(Web3.HTTPProvider(RPC_HTTP))

# ─────── ABI-фрагменты ровно под нужные вызовы ───────
COMET_ABI = [
    {"name":"balanceOf","type":"function","stateMutability":"view",
     "inputs":[{"name":"account","type":"address"}],"outputs":[{"type":"uint256"}]},
    {"name":"borrowBalanceOf","type":"function","stateMutability":"view",
     "inputs":[{"name":"account","type":"address"}],"outputs":[{"type":"uint256"}]},
    {"name":"numAssets","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"type":"uint8"}]},
    {   # ← БЫЛО: "uint256"
        "name": "getAssetInfo",
        "type": "function",
        "stateMutability": "view",
        "inputs":  [{"name": "i", "type": "uint8"}],     # 8‑бит!
        "outputs": [{"components": [
            {"name":"offset",                   "type":"uint256"},
            {"name":"asset",                    "type":"address"},
            {"name":"priceFeed",                "type":"address"},
            {"name":"scale",                    "type":"uint64"},
            {"name":"borrowCollateralFactor",   "type":"uint64"},
            {"name":"liquidateCollateralFactor","type":"uint64"},
            {"name":"supplyCap",                "type":"uint128"},
        ], "type": "tuple"}],
    },
    {"name":"collateralBalanceOf","type":"function","stateMutability":"view",
     "inputs":[{"name":"account","type":"address"},{"name":"asset","type":"address"}],
     "outputs":[{"type":"uint128"}]},
    {"name":"baseToken","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"type":"address"}]},
    {"name":"baseScale","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"type":"uint64"}]},
]
ERC20_ABI = [
    {"name":"symbol","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"type":"string"}]},
    {"name":"decimals","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"type":"uint8"}]},
]

def scale(value: int, factor: int) -> Decimal:
    return Decimal(value) / Decimal(factor)

def fetch_comet_position(comet_addr: str, account: str):
    comet = w3.eth.contract(address=comet_addr, abi=COMET_ABI)

    # ── база (USDC) ────────────────────────────
    base_token  = comet.functions.baseToken().call()
    base_scale  = comet.functions.baseScale().call()        # 10**dec
    erc20       = w3.eth.contract(address=base_token, abi=ERC20_ABI)
    base_symbol = erc20.functions.symbol().call()

    supplied   = scale(comet.functions.balanceOf(account).call(), base_scale)
    borrowed   = scale(comet.functions.borrowBalanceOf(account).call(), base_scale)

    # ── коллатерали ────────────────────────────
    positions  = []
    n_assets   = comet.functions.numAssets().call()
    for i in range(n_assets):
        info   = comet.functions.getAssetInfo(i).call()
        asset  = info[1]
        scale_ = info[3]                            # uint64, обычно 10**dec
        bal    = comet.functions.collateralBalanceOf(account, asset).call()
        if bal == 0:
            continue

        erc20  = w3.eth.contract(asset, ERC20_ABI)
        symbol = erc20.functions.symbol().call()
        positions.append((symbol, scale(bal, scale_)))

    return base_symbol, supplied, borrowed, positions

#if __name__ == "__main__":
#    base_sym, supplied, borrowed, collats = fetch_comet_position(COMET, USER)

#    print(f"\n💳  Compound v3 (USDT) позиция аккаунта {USER[:8]}…")
#    print(f"  {base_sym} supplied : {supplied:.6f}")
#    print(f"  {base_sym} borrowed : {borrowed:.6f}")

#    if collats:
#        print("  ─ Collateral ─")
#        for sym, amt in collats:
#            print(f"    {sym:<6} : {amt:.6f}")
#    else:
#        print("  No collateral deposited.")