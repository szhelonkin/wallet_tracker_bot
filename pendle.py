import requests
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

rpc = "https://api-v2.pendle.finance/core/v1/dashboard/positions/database/"

def fetch_pendle_position(addr):
    """Fetch Pendle position with proper error handling and retry logic."""
    max_retries = 3
    timeout = 10
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(f"{rpc}{addr}", timeout=timeout)
            resp.raise_for_status()  # Raise exception for HTTP errors
            
            data = resp.json()
            total_pos = Decimal(0)
            
            # Check if positions exist in response
            if "positions" not in data:
                logger.warning(f"No positions found for address {addr}")
                return total_pos
            
            for pos in data["positions"]:
                if pos is None: 
                    continue
                if "openPositions" not in pos:
                    continue
                    
                for open_pos in pos["openPositions"]:
                    if "lp" not in open_pos or "valuation" not in open_pos["lp"]:
                        continue
                    pos_val = open_pos["lp"]["valuation"]
                    total_pos += Decimal(str(pos_val))
            
            return total_pos
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching Pendle position for {addr} (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch Pendle position for {addr} after {max_retries} attempts")
                return Decimal(0)
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error fetching Pendle position for {addr}: {e} (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch Pendle position for {addr} after {max_retries} attempts")
                return Decimal(0)
                
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP error fetching Pendle position for {addr}: {e} (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch Pendle position for {addr} after {max_retries} attempts")
                return Decimal(0)
                
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Data parsing error for Pendle position {addr}: {e}")
            return Decimal(0)
            
        except Exception as e:
            logger.error(f"Unexpected error fetching Pendle position for {addr}: {e}")
            return Decimal(0)
    
    return Decimal(0)

#result = fetch_pendle_position("0x0C8eb038c58E0a9d8D66Bf5805A6eC0dfDaE6c4c")
#print(result)
