import os
import asyncio
from decimal import Decimal
from web3 import Web3, HTTPProvider
from rpc_manager import get_web3, call_contract_with_retry

USER     = Web3.to_checksum_address("0x0C8eb038c58E0a9d8D66Bf5805A6eC0dfDaE6c4c")
COMET    = Web3.to_checksum_address("0x3Afdc9BCA9213A35503b077a6072F3D0d5AB0840")

w3 = get_web3()

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

def fetch_comet_position(comet_addr: str, account: str, use_cache: bool = True):
    try:
        from rpc_manager import rpc_manager
        
        # Get a fresh Web3 instance
        w3_instance = rpc_manager.get_web3_instance()
        comet = w3_instance.eth.contract(address=comet_addr, abi=COMET_ABI)

        # ── база (USDC) ────────────────────────────
        def _get_base_token():
            return comet.functions.baseToken().call()
        base_token = rpc_manager._make_request_with_retry(_get_base_token, use_cache=use_cache)
        
        def _get_base_scale():
            return comet.functions.baseScale().call()
        base_scale = rpc_manager._make_request_with_retry(_get_base_scale, use_cache=use_cache)
        
        erc20 = w3_instance.eth.contract(address=base_token, abi=ERC20_ABI)
        
        def _get_symbol():
            return erc20.functions.symbol().call()
        base_symbol = rpc_manager._make_request_with_retry(_get_symbol, use_cache=use_cache)

        def _get_balance():
            return comet.functions.balanceOf(account).call()
        supplied = scale(rpc_manager._make_request_with_retry(_get_balance, use_cache=use_cache), base_scale)
        
        def _get_borrow_balance():
            return comet.functions.borrowBalanceOf(account).call()
        borrowed = scale(rpc_manager._make_request_with_retry(_get_borrow_balance, use_cache=use_cache), base_scale)

        # ── коллатерали ────────────────────────────
        positions = []
        
        def _get_num_assets():
            return comet.functions.numAssets().call()
        n_assets = rpc_manager._make_request_with_retry(_get_num_assets, use_cache=use_cache)
        
        for i in range(n_assets):
            def _get_asset_info():
                return comet.functions.getAssetInfo(i).call()
            info = rpc_manager._make_request_with_retry(_get_asset_info, use_cache=use_cache)
            asset = info[1]
            scale_ = info[3]
            
            def _get_collateral_balance():
                return comet.functions.collateralBalanceOf(account, asset).call()
            bal = rpc_manager._make_request_with_retry(_get_collateral_balance, use_cache=use_cache)
            
            if bal == 0:
                continue

            erc20 = w3_instance.eth.contract(asset, ERC20_ABI)
            
            def _get_asset_symbol():
                return erc20.functions.symbol().call()
            symbol = rpc_manager._make_request_with_retry(_get_asset_symbol, use_cache=use_cache)
            positions.append((symbol, scale(bal, scale_)))

        return base_symbol, supplied, borrowed, positions
    except Exception as e:
        print(f"Error fetching comet position for {account}: {e}")
        return "USDC", 0, 0, []

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