import requests
from decimal import Decimal

rpc = "https://api-v2.pendle.finance/core/v1/dashboard/positions/database/"

def fetch_pendle_position(addr):
    resp = requests.get(f"{rpc}{addr}")
    total_pos = Decimal(0)
    for pos in resp.json()["positions"]:
        if pos is None: continue
        for open_pos in pos["openPositions"]:
            pos_val = open_pos["lp"]["valuation"]
            total_pos += Decimal(pos_val)
    return total_pos

#result = fetch_pendle_position("0x0C8eb038c58E0a9d8D66Bf5805A6eC0dfDaE6c4c")
#print(result)
