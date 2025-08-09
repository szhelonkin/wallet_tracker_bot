from web3 import Web3, HTTPProvider
import json, requests
from decimal import Decimal

RPC  = "https://eth-mainnet.g.alchemy.com/v2/4T2FGg31ChPTZ2bQML9iW"
w3   = Web3(HTTPProvider(RPC))

ACCOUNT_LENS = w3.to_checksum_address("0x94B9D29721f0477402162C93d95B3b4e52425844")
EVC          = w3.to_checksum_address("0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383")
VLENS_ADDR   = w3.to_checksum_address("0x079FA5cdE9c9647D26E79F3520Fbdf9dbCC0E45e")

# ✅ КАЧАЕМ АКТУАЛЬНОЕ JSON-ABI
url  = ("https://github.com/euler-xyz/euler-interfaces/raw/refs/heads/master/abis/AccountLens.json")
ABI  = requests.get(url, timeout=10).json()

url_vlens  = ("https://github.com/euler-xyz/euler-interfaces/raw/refs/heads/master/abis/VaultLens.json")
ABI_VLENS  = requests.get(url_vlens, timeout=10).json()

url_pers  = ("https://github.com/euler-xyz/euler-interfaces/raw/refs/heads/master/abis/EscrowedCollateralPerspective.json")

#print(ABI)

lens = w3.eth.contract(address=ACCOUNT_LENS, abi=ABI)
vault_lens = w3.eth.contract(address=VLENS_ADDR, abi=ABI_VLENS)
#print(lens)

def single_vault_position(user, vault):
    evcInfo, vInfo, _ = lens.functions.getAccountInfo(
        w3.to_checksum_address(user),
        w3.to_checksum_address(vault)
    ).call()
    assets = w3.from_wei(vInfo[6], "ether")
    return assets


#if __name__ == "__main__":
#    print(single_vault_position("0x8357b66F74363E926de4186A449f365707c7fbad", "0xD8b27CF359b7D15710a5BE299AF6e7Bf904984C2"))
    