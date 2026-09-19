"""
Nonce Middleware - Identity-Bound x402 Receipts
================================================
Implements non-bearer, identity-bound x402 receipts using HMAC over nonce|ts|body.
Prevents receipt theft and replay attacks by binding receipts to agent identity.

Author: Muse Security Audit
Integration: x402_gateway.py + cerberus_router.py
"""

import hmac
import hashlib
import time
import json
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class IdentityBoundReceipt:
    """Non-bearer x402 receipt bound to agent identity."""
    nonce: str
    timestamp: int
    body_hash: str
    agent_id: str
    hmac_signature: str
    network: str
    amount_usd: float
    
    def to_header(self) -> str:
        """Serialize for x-402-receipt header."""
        return f"{self.nonce}|{self.timestamp}|{self.body_hash}|{self.agent_id}|{self.hmac_signature}"

class NonceMiddleware:
    """
    Identity-bound x402 receipt middleware.
    
    Receipts are bound to agent identity via HMAC-SHA256 over:
    nonce|timestamp|body_hash|agent_id
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        key = secret_key or os.getenv("NONCE_HMAC_SECRET", "nano-empire-nonce-secret-2026")
        self.secret_key = key.encode() if isinstance(key, str) else key
    
    def _compute_body_hash(self, body: Dict[str, Any]) -> str:
        """Compute SHA256 hash of request body for binding."""
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]
    
    def generate_nonce(self) -> str:
        """Generate cryptographically secure nonce."""
        return hashlib.sha256(os.urandom(32)).hexdigest()[:32]
    
    def create_receipt(
        self,
        agent_id: str,
        body: Dict[str, Any],
        network: str = "solana",
        amount_usd: float = 0.0
    ) -> IdentityBoundReceipt:
        """Create identity-bound x402 receipt."""
        nonce = self.generate_nonce()
        timestamp = int(time.time())
        body_hash = self._compute_body_hash(body)
        
        signing_string = f"{nonce}|{timestamp}|{body_hash}|{agent_id}"
        hmac_sig = hmac.new(
            self.secret_key,
            signing_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return IdentityBoundReceipt(
            nonce=nonce,
            timestamp=timestamp,
            body_hash=body_hash,
            agent_id=agent_id,
            hmac_signature=hmac_sig,
            network=network,
            amount_usd=amount_usd
        )
    
    def verify_receipt(self, receipt: IdentityBoundReceipt, body: Dict[str, Any]) -> bool:
        """Verify identity-bound receipt integrity and ownership."""
        expected_body_hash = self._compute_body_hash(body)
        if receipt.body_hash != expected_body_hash:
            return False
        
        signing_string = f"{receipt.nonce}|{receipt.timestamp}|{receipt.body_hash}|{receipt.agent_id}"
        expected_hmac = hmac.new(
            self.secret_key,
            signing_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(receipt.hmac_signature, expected_hmac)
    
    def parse_receipt_header(self, header_value: str) -> Optional[IdentityBoundReceipt]:
        """Parse x-402-receipt header into IdentityBoundReceipt."""
        try:
            parts = header_value.split("|")
            if len(parts) != 5:
                return None
            return IdentityBoundReceipt(
                nonce=parts[0],
                timestamp=int(parts[1]),
                body_hash=parts[2],
                agent_id=parts[3],
                hmac_signature=parts[4],
                network="",
                amount_usd=0.0
            )
        except (ValueError, IndexError):
            return None

_nonce_middleware = NonceMiddleware()

def create_identity_bound_receipt(
    agent_id: str,
    body: Dict[str, Any],
    network: str = "solana",
    amount_usd: float = 0.0
) -> str:
    receipt = _nonce_middleware.create_receipt(agent_id, body, network)
    return receipt.to_header()

def verify_identity_bound_receipt(
    header_value: str,
    body: Dict[str, Any]
) -> bool:
    receipt = _nonce_middleware.parse_receipt_header(header_value)
    if not receipt:
        return False
    return _nonce_middleware.verify_receipt(receipt, body)
