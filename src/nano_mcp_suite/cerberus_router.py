"""
cerberus_router.py — Nano Empire Cerberus Dynamic Tollbooth Router
UCB1 MAB arm selector + Bloom-filter replay guard + bonding-curve dynamic pricer.
Drop-in replacement for static x402 toll verification in x402_gateway.py.

Usage:
    from nano_mcp_suite.cerberus_router import cerberus
    result = await cerberus.handle_request(request, tool_id)
"""

import asyncio
import hashlib
import math
import struct
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# BLOOM FILTER — Replay Guard
# 2^20 bits, 7 hash functions, TTL ring buffer (1-hr buckets)
# ─────────────────────────────────────────────────────────────
class BloomReplayGuard:
    """Bloom-filter replay guard. Rejects duplicate tx hashes within TTL window."""
    BITS = 1 << 20          # 128 KB
    NUM_HASHES = 7
    TTL_SECONDS = 3600      # 1 hour replay window
    BUCKET_SECONDS = 60     # evict oldest bucket every 60s

    def __init__(self):
        self._bit_array = bytearray(self.BITS // 8)
        # Ring buffer of (ts_bucket, set_of_positions) for TTL eviction
        self._ring: dict[int, list[int]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _hash_positions(self, item: str) -> list[int]:
        """Generate NUM_HASHES bit positions for item."""
        positions = []
        data = item.encode()
        for seed in range(self.NUM_HASHES):
            # MurmurHash3-inspired via SHA256 seeding
            h = int(hashlib.sha256(struct.pack(">I", seed) + data).hexdigest(), 16)
            positions.append(h % self.BITS)
        return positions

    def _set_bit(self, pos: int):
        self._bit_array[pos // 8] |= (1 << (pos % 8))

    def _get_bit(self, pos: int) -> bool:
        return bool(self._bit_array[pos // 8] & (1 << (pos % 8)))

    def _evict_expired(self):
        now_bucket = int(time.time()) // self.BUCKET_SECONDS
        cutoff = now_bucket - (self.TTL_SECONDS // self.BUCKET_SECONDS)
        for bucket in list(self._ring.keys()):
            if bucket < cutoff:
                for pos in self._ring[bucket]:
                    self._bit_array[pos // 8] &= ~(1 << (pos % 8))
                del self._ring[bucket]

    async def is_replay(self, tx_hash: str) -> bool:
        """Returns True if tx_hash was seen within TTL window (replay detected)."""
        async with self._lock:
            self._evict_expired()
            positions = self._hash_positions(tx_hash)
            if all(self._get_bit(p) for p in positions):
                return True  # Likely replay
            # Not seen — insert
            bucket = int(time.time()) // self.BUCKET_SECONDS
            for p in positions:
                self._set_bit(p)
                self._ring[bucket].append(p)
            return False


# ─────────────────────────────────────────────────────────────
# THOMPSON SAMPLING + UCB1 HYBRID MAB ROUTER
# ─────────────────────────────────────────────────────────────
import random

@dataclass
class Arm:
    name: str
    total_reward: float = 0.0
    pulls: int = 0
    alpha: float = 1.0  # Beta prior successes (Thompson Sampling)
    beta: float = 1.0   # Beta prior failures
    variance: float = 0.0

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

    def sample_thompson(self) -> float:
        """Sample from Posterior Beta(alpha, beta) distribution."""
        return random.betavariate(max(self.alpha, 0.01), max(self.beta, 0.01))

    def ucb1_score(self, total_pulls: int) -> float:
        """UCB1 = mean_reward + sqrt(2 * ln(total_pulls) / pulls)"""
        if self.pulls == 0:
            return float("inf")  # Explore unvisited arms first
        return self.mean_reward + math.sqrt(2 * math.log(total_pulls) / self.pulls)


class MABRouter:
    """Thompson Sampling + Latency-aware MAB for routing tool calls to optimal arm."""

    ARMS = [
        "security",      # prompt_guard, document_guard
        "embeddings",    # verified embeddings
        "rerank",        # semantic rerank
        "mev",           # titan MEV tools
        "huggingbay",    # HuggingBay 8-tool suite
    ]

    def __init__(self, mode: str = "thompson"):
        self.arms = {name: Arm(name=name) for name in self.ARMS}
        self.total_pulls = 0
        self.mode = mode
        self._lock = asyncio.Lock()

    async def select_arm(self, tool_id: str) -> str:
        """Select best arm for tool_id using Thompson Sampling posterior sampling."""
        # Direct category mapping if explicitly present
        for arm_name in self.ARMS:
            if arm_name in tool_id.lower():
                return arm_name

        # MAB selection when no direct category match
        async with self._lock:
            if self.mode == "thompson":
                selected = max(self.arms.values(), key=lambda a: a.sample_thompson())
            else:
                selected = max(self.arms.values(), key=lambda a: a.ucb1_score(max(self.total_pulls, 1)))
            return selected.name

    async def update(self, arm_name: str, latency_ms: float):
        """
        Update arm reward via Thompson Sampling (Beta updating).
        SLA Target: 200ms. Latency < 200ms -> success (alpha++), Latency > 200ms -> penalty (beta++).
        """
        async with self._lock:
            if arm_name not in self.arms:
                return
            arm = self.arms[arm_name]
            arm.pulls += 1
            self.total_pulls += 1

            # Latency SLA satisfaction in [0, 1]
            sla_target_ms = 200.0
            satisfaction = max(0.0, min(1.0, 1.0 - (latency_ms / (sla_target_ms * 2.0))))
            
            # Posterior Beta updates
            arm.alpha += satisfaction
            arm.beta += (1.0 - satisfaction)

            reward = 1000.0 / max(latency_ms, 1.0)
            arm.total_reward += reward

    def stats(self) -> dict:
        return {
            name: {
                "pulls": arm.pulls,
                "alpha": round(arm.alpha, 2),
                "beta": round(arm.beta, 2),
                "expected_prob": round(arm.alpha / (arm.alpha + arm.beta), 3),
                "mean_reward": round(arm.mean_reward, 3),
            }
            for name, arm in self.arms.items()
        }


# ─────────────────────────────────────────────────────────────
# EXPONENTIAL SURGE CURVE v2
# price = base * e^((utilization^2) * sensitivity)  cap=$0.50  floor=$0.001
# ─────────────────────────────────────────────────────────────
class DynamicPricer:
    BASE_PRICE = 0.01          # $0.01 per call at zero load
    SENSITIVITY = 2.718        # Exponential surge scaling parameter
    MAX_CONNECTIONS = 1000
    PRICE_CAP = 0.50
    PRICE_FLOOR = 0.001

    def __init__(self):
        self._active_connections = 0
        self._lock = asyncio.Lock()

    async def enter(self):
        async with self._lock:
            self._active_connections += 1

    async def exit(self):
        async with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    def current_price(self) -> float:
        ratio = self._active_connections / self.MAX_CONNECTIONS
        # Exponential surge curve v2: price = base * e^(ratio^2 * sensitivity)
        price = self.BASE_PRICE * math.exp((ratio ** 2) * self.SENSITIVITY)
        return max(self.PRICE_FLOOR, min(self.PRICE_CAP, round(price, 4)))

    def stats(self) -> dict:
        return {
            "active_connections": self._active_connections,
            "current_price_usd": self.current_price(),
            "load_ratio": round(self._active_connections / self.MAX_CONNECTIONS, 4),
            "base_price_usd": self.BASE_PRICE,
            "price_cap_usd": self.PRICE_CAP,
        }


# ─────────────────────────────────────────────────────────────
# CERBERUS — Top-level coordinator
# ─────────────────────────────────────────────────────────────
@dataclass
class CerberusResult:
    allowed: bool
    arm: str
    price_usd: float
    replay_detected: bool
    reason: str
    latency_ms: float = 0.0


class CerberusRouter:
    """
    Cerberus: UCB1 MABRouter + BloomReplayGuard + DynamicPricer.
    Call handle_request() in x402_gateway middleware to replace static verification.
    """

    def __init__(self):
        self.mab = MABRouter()
        self.bloom = BloomReplayGuard()
        self.pricer = DynamicPricer()
        self._request_count = 0
        self._revenue_usd = 0.0
        self._blocked_replays = 0

    async def handle_request(
        self,
        tx_hash: str,
        tool_id: str = "unknown",
        bypass_synthetic: bool = True,
    ) -> CerberusResult:
        """
        Main entry point. Returns CerberusResult with routing decision.
        Synthetic tokens (tx_*) bypass Bloom filter for testing.
        """
        t0 = time.perf_counter()
        await self.pricer.enter()

        try:
            # Synthetic bypass for test tokens
            if bypass_synthetic and tx_hash.startswith("tx_"):
                arm = await self.mab.select_arm(tool_id)
                price = self.pricer.current_price()
                elapsed = (time.perf_counter() - t0) * 1000
                await self.mab.update(arm, elapsed)
                self._request_count += 1
                self._revenue_usd += price
                return CerberusResult(
                    allowed=True, arm=arm, price_usd=price,
                    replay_detected=False, reason="synthetic_bypass",
                    latency_ms=round(elapsed, 2)
                )

            # Bloom filter replay check
            if await self.bloom.is_replay(tx_hash):
                self._blocked_replays += 1
                elapsed = (time.perf_counter() - t0) * 1000
                return CerberusResult(
                    allowed=False, arm="blocked", price_usd=0.0,
                    replay_detected=True, reason="replay_detected",
                    latency_ms=round(elapsed, 2)
                )

            # Select routing arm + compute price
            arm = await self.mab.select_arm(tool_id)
            price = self.pricer.current_price()
            elapsed = (time.perf_counter() - t0) * 1000
            await self.mab.update(arm, elapsed)

            self._request_count += 1
            self._revenue_usd += price

            return CerberusResult(
                allowed=True, arm=arm, price_usd=price,
                replay_detected=False, reason="ok",
                latency_ms=round(elapsed, 2)
            )

        finally:
            await self.pricer.exit()

    def stats(self) -> dict:
        return {
            "total_requests": self._request_count,
            "blocked_replays": self._blocked_replays,
            "total_revenue_usd": round(self._revenue_usd, 4),
            "mab": self.mab.stats(),
            "pricer": self.pricer.stats(),
        }


# Module-level singleton — import this in x402_gateway.py
cerberus = CerberusRouter()
