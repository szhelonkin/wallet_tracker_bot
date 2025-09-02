from web3 import Web3, HTTPProvider
import json, requests
from decimal import Decimal
from rpc_manager import get_web3, call_contract_with_retry

w3 = get_web3()

ACCOUNT_LENS = w3.to_checksum_address("0x94B9D29721f0477402162C93d95B3b4e52425844")
EVC          = w3.to_checksum_address("0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383")
VLENS_ADDR   = w3.to_checksum_address("0x079FA5cdE9c9647D26E79F3520Fbdf9dbCC0E45e")

# ✅ КАЧАЕМ АКТУАЛЬНОЕ JSON-ABI с обработкой ошибок
def get_abi_with_fallback(url, fallback_abi):
    """Download ABI with fallback to local definition."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not download ABI from {url}: {e}")
        print("Using fallback ABI definition")
        return fallback_abi

# Fallback ABI definitions
ACCOUNT_LENS_ABI = [
    {
        "name": "getAccountInfo",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "vault", "type": "address"}
        ],
        "outputs": [
            {"name": "evcInfo", "type": "tuple"},
            {"name": "vInfo", "type": "tuple"},
            {"name": "perspective", "type": "tuple"}
        ]
    }
]

VAULT_LENS_ABI = [
    {
        "name": "getVaultInfo",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "vault", "type": "address"}
        ],
        "outputs": [
            {"name": "info", "type": "tuple"}
        ]
    }
]

# Try to download ABIs, fallback to local definitions
url = "https://github.com/euler-xyz/euler-interfaces/raw/refs/heads/master/abis/AccountLens.json"
ABI = get_abi_with_fallback(url, ACCOUNT_LENS_ABI)

url_vlens = "https://github.com/euler-xyz/euler-interfaces/raw/refs/heads/master/abis/VaultLens.json"
ABI_VLENS = get_abi_with_fallback(url_vlens, VAULT_LENS_ABI)

#print(ABI)

lens = w3.eth.contract(address=ACCOUNT_LENS, abi=ABI)
vault_lens = w3.eth.contract(address=VLENS_ADDR, abi=ABI_VLENS)
#print(lens)

def single_vault_position(user, vault):
    try:
        # Use the RPC manager's Web3 instance directly
        from rpc_manager import rpc_manager
        
        # Get a fresh Web3 instance
        w3_instance = rpc_manager.get_web3_instance()
        
        # Recreate the contract with the new Web3 instance
        lens_contract = w3_instance.eth.contract(address=ACCOUNT_LENS, abi=ABI)
        
        # Make the call with retry logic
        def _call():
            return lens_contract.functions.getAccountInfo(
                w3_instance.to_checksum_address(user),
                w3_instance.to_checksum_address(vault)
            ).call()
        
        evcInfo, vInfo, _ = rpc_manager._make_request_with_retry(_call)
        assets = w3_instance.from_wei(vInfo[6], "ether")
        return assets
    except Exception as e:
        print(f"Error getting vault position for {user}: {e}")
        return 0


#if __name__ == "__main__":
#    print(single_vault_position("0x8357b66F74363E926de4186A449f365707c7fbad", "0xD8b27CF359b7D15710a5BE299AF6e7Bf904984C2"))
    