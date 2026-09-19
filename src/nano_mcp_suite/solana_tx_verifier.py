import httpx
import logging
from typing import Optional
import os
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HARDENED: Configuration-driven RPC endpoints
SOLANA_RPC_ENDPOINTS = [
    os.getenv("SOLANA_RPC_PRIMARY", "https://api.mainnet-beta.solana.com"),
    os.getenv("SOLANA_RPC_SECONDARY", "https://solana-mainnet.rpcpool.com"),
]
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

class CircuitBreaker:
    def __init__(self, failure_threshold=3, reset_timeout=60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = {}
        self.last_failure_time = {}

    def is_open(self, endpoint):
        fails = self.failures.get(endpoint, 0)
        if fails >= self.failure_threshold:
            last_fail = self.last_failure_time.get(endpoint, datetime.min)
            if datetime.now() - last_fail > timedelta(seconds=self.reset_timeout):
                # Half-open: reset to try again
                self.failures[endpoint] = 0
                return False
            return True
        return False

    def record_failure(self, endpoint):
        self.failures[endpoint] = self.failures.get(endpoint, 0) + 1
        self.last_failure_time[endpoint] = datetime.now()
        logger.warning(f"CircuitBreaker recorded failure for {endpoint}. Total failures: {self.failures[endpoint]}")

    def record_success(self, endpoint):
        if endpoint in self.failures:
            self.failures[endpoint] = 0

cb = CircuitBreaker()

def verify_solana_transfer(tx_signature: str, expected_recipient: str, expected_usdc_amount: float) -> bool:
    """
    Verifies that a Solana transaction transferred the expected amount of USDC to the expected recipient
    with multi-RPC fallback logic and Circuit Breaker.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            tx_signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }

    for endpoint in SOLANA_RPC_ENDPOINTS:
        if cb.is_open(endpoint):
            logger.warning(f"Circuit Breaker OPEN for {endpoint}. Skipping.")
            continue
            
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload)
                
                if response.status_code == 429:
                    logger.warning(f"RPC {endpoint} rate limited. Trying next...")
                    cb.record_failure(endpoint)
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    logger.error(f"RPC Error on {endpoint}: {data['error']}")
                    cb.record_failure(endpoint)
                    continue
                    
                cb.record_success(endpoint)
                result = data.get("result")
                if not result:
                    logger.warning(f"Transaction {tx_signature} not found on {endpoint}.")
                    continue
                    
                meta = result.get("meta")
                if not meta or meta.get("err") is not None:
                    return False
                    
                pre_balances = meta.get("preTokenBalances", [])
                post_balances = meta.get("postTokenBalances", [])
                
                pre_balance = 0.0
                for b in pre_balances:
                    if b.get("mint") == USDC_MINT and b.get("owner") == expected_recipient:
                        ui_amount = b.get("uiTokenAmount", {}).get("uiAmount")
                        if ui_amount is not None:
                            pre_balance = float(ui_amount)
                        break
                        
                post_balance = 0.0
                for b in post_balances:
                    if b.get("mint") == USDC_MINT and b.get("owner") == expected_recipient:
                        ui_amount = b.get("uiTokenAmount", {}).get("uiAmount")
                        if ui_amount is not None:
                            post_balance = float(ui_amount)
                            break
                            
                actual_amount = post_balance - pre_balance
                logger.info(f"Recipient {expected_recipient} USDC balance change: {actual_amount}")
                
                if actual_amount >= expected_usdc_amount - 0.000001:
                    return True
                    
                logger.warning(f"Expected {expected_usdc_amount} USDC, but actual transfer was {actual_amount} USDC.")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying transaction on {endpoint}: {e}")
            cb.record_failure(endpoint)
            continue
            
    return False

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 4:
        sig = sys.argv[1]
        recp = sys.argv[2]
        amt = float(sys.argv[3])
        result = verify_solana_transfer(sig, recp, amt)
        print(f"Verification result: {result}")
        sys.exit(0 if result else 1)
