import time
import random
from typing import List, Optional
from web3 import Web3, HTTPProvider
from web3.exceptions import Web3Exception
import requests
import logging

logger = logging.getLogger(__name__)

class RPCManager:
    """Manages multiple RPC endpoints with automatic failover and rate limiting handling."""
    
    def __init__(self):
        # List of RPC endpoints with fallbacks
        self.rpc_endpoints = [
            "https://eth-mainnet.g.alchemy.com/v2/4T2FGg31ChPTZ2bQML9iW",  # Primary Alchemy
            "https://ethereum.publicnode.com",  # Public node (no auth required)
            "https://eth.llamarpc.com",  # LlamaRPC (no auth required)
            "https://ethereum.blockpi.network/v1/rpc/public",  # BlockPI (no auth required)
            "https://eth-mainnet.public.blastapi.io",  # BlastAPI (no auth required)
            "https://rpc.ankr.com/eth",  # Ankr public RPC (may require auth)
            "https://eth-mainnet.g.alchemy.com/v2/demo",  # Alchemy demo (rate limited but free)
        ]
        
        self.current_endpoint_index = 0
        self.rate_limited_endpoints = set()
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimum 100ms between requests
        
    def _get_current_endpoint(self) -> str:
        """Get the current active RPC endpoint."""
        return self.rpc_endpoints[self.current_endpoint_index]
    
    def _switch_to_next_endpoint(self):
        """Switch to the next available RPC endpoint."""
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.rpc_endpoints)
        logger.info(f"Switched to RPC endpoint: {self._get_current_endpoint()}")
    
    def _is_endpoint_available(self, endpoint: str) -> bool:
        """Check if an endpoint is available (not rate limited)."""
        return endpoint not in self.rate_limited_endpoints
    
    def _mark_endpoint_rate_limited(self, endpoint: str):
        """Mark an endpoint as rate limited."""
        self.rate_limited_endpoints.add(endpoint)
        logger.warning(f"Marked endpoint as rate limited: {endpoint}")
        
        # Remove from rate limited set after 5 minutes
        def remove_from_rate_limited():
            time.sleep(300)  # 5 minutes
            self.rate_limited_endpoints.discard(endpoint)
            logger.info(f"Removed rate limit from endpoint: {endpoint}")
        
        import threading
        threading.Thread(target=remove_from_rate_limited, daemon=True).start()
    
    def _rate_limit_delay(self):
        """Add delay to respect rate limits."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request_with_retry(self, func, *args, max_retries=3, **kwargs):
        """Make a request with automatic retry and endpoint switching."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Rate limiting delay
                self._rate_limit_delay()
                
                # Try current endpoint
                current_endpoint = self._get_current_endpoint()
                if not self._is_endpoint_available(current_endpoint):
                    self._switch_to_next_endpoint()
                    continue
                
                # Make the request
                result = func(*args, **kwargs)
                return result
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    logger.warning(f"Rate limited on endpoint {current_endpoint}: {e}")
                    self._mark_endpoint_rate_limited(current_endpoint)
                    self._switch_to_next_endpoint()
                    last_exception = e
                    continue
                elif e.response.status_code in [401, 403]:  # Unauthorized/Forbidden
                    logger.warning(f"Unauthorized access to endpoint {current_endpoint}: {e}")
                    self._mark_endpoint_rate_limited(current_endpoint)
                    self._switch_to_next_endpoint()
                    last_exception = e
                    continue
                else:
                    logger.error(f"HTTP error on endpoint {current_endpoint}: {e}")
                    self._switch_to_next_endpoint()
                    last_exception = e
                    continue
                    
            except (Web3Exception, requests.exceptions.RequestException, Exception) as e:
                logger.error(f"Request failed on endpoint {current_endpoint}: {e}")
                self._switch_to_next_endpoint()
                last_exception = e
                continue
        
        # If all retries failed, raise the last exception
        raise last_exception or Exception("All RPC endpoints failed")
    
    def get_web3_instance(self) -> Web3:
        """Get a Web3 instance with the current endpoint."""
        current_endpoint = self._get_current_endpoint()
        return Web3(HTTPProvider(current_endpoint))
    
    def call_contract_function(self, contract_func, *args, **kwargs):
        """Call a contract function with automatic retry and endpoint switching."""
        def _call():
            w3 = self.get_web3_instance()
            # Recreate the contract with the new Web3 instance
            contract = w3.eth.contract(
                address=contract_func.contract.address,
                abi=contract_func.contract.abi
            )
            # Get the function from the new contract
            new_func = getattr(contract.functions, contract_func.fn_name)
            return new_func(*args).call(**kwargs)
        
        return self._make_request_with_retry(_call)
    
    def get_balance(self, address: str):
        """Get ETH balance with automatic retry and endpoint switching."""
        def _get_balance():
            w3 = self.get_web3_instance()
            return w3.eth.get_balance(address)
        
        return self._make_request_with_retry(_get_balance)
    
    def get_chain_id(self):
        """Get chain ID with automatic retry and endpoint switching."""
        def _get_chain_id():
            w3 = self.get_web3_instance()
            return w3.eth.chain_id
        
        return self._make_request_with_retry(_get_chain_id)

# Global RPC manager instance
rpc_manager = RPCManager()

def get_web3() -> Web3:
    """Get a Web3 instance with automatic failover."""
    return rpc_manager.get_web3_instance()

def call_contract_with_retry(contract_func, *args, **kwargs):
    """Call a contract function with automatic retry and endpoint switching."""
    return rpc_manager.call_contract_function(contract_func, *args, **kwargs)

def get_balance_with_retry(address: str):
    """Get ETH balance with automatic retry and endpoint switching."""
    return rpc_manager.get_balance(address)
