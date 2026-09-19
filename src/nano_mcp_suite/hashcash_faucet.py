"""
Nano Empire AI - Hashcash PoW Faucet Defender
========================================================================
Protects the Nano Empire x402 testnet faucet from Sybil attacks.
Requires requesting agents to burn local CPU cycles (Proof of Work) 
before claiming 100 free testnet credits.
"""

import time
import hashlib
import secrets
from typing import Dict, Tuple, Optional

class HashcashFaucet:
    def __init__(self, difficulty_bits: int = 20, max_credits: int = 100):
        # 20 bits of difficulty takes approx 1-3 seconds on a standard CPU.
        # It's enough to stop a mass Sybil attack, but fast enough for a legitimate agent.
        self.difficulty_bits = difficulty_bits
        self.max_credits = max_credits
        self.active_challenges: Dict[str, float] = {}  # challenge -> timestamp
        self.challenge_expiry = 300  # 5 minutes

    def _get_target_prefix(self) -> str:
        """Returns the binary prefix required for the hash (e.g. '00000000000000000000')"""
        return '0' * self.difficulty_bits

    def generate_challenge(self, agent_id: str) -> Dict[str, str]:
        """
        Step 1: Agent requests a challenge.
        Server returns a cryptographic string tied to the agent's identity.
        """
        salt = secrets.token_hex(8)
        challenge_string = f"nano_empire:{agent_id}:{salt}:{int(time.time())}"
        
        # Store challenge to prevent reuse/fabrication
        self.active_challenges[challenge_string] = time.time()
        
        return {
            "challenge": challenge_string,
            "difficulty_bits": self.difficulty_bits,
            "algorithm": "sha256(challenge + nonce)"
        }

    def verify_and_mint(self, agent_id: str, challenge: str, nonce: str) -> Tuple[bool, str]:
        """
        Step 2: Agent submits the challenge and the computed nonce.
        If valid, the faucet mints the x402 credits.
        """
        # 1. Verify challenge exists and isn't expired
        if challenge not in self.active_challenges:
            return False, "Challenge not found or invalid."
            
        if time.time() - self.active_challenges[challenge] > self.challenge_expiry:
            del self.active_challenges[challenge]
            return False, "Challenge expired."
            
        # 2. Prevent replay attacks (burn the challenge)
        del self.active_challenges[challenge]
        
        # 3. Verify the agent_id matches the challenge
        if f":{agent_id}:" not in challenge:
            return False, "Agent ID mismatch in challenge."
            
        # 4. Verify the Proof of Work
        payload = f"{challenge}{nonce}".encode('utf-8')
        hash_result = hashlib.sha256(payload).hexdigest()
        
        # Convert hex to binary string to check difficulty bits
        binary_hash = bin(int(hash_result, 16))[2:].zfill(256)
        
        if binary_hash.startswith(self._get_target_prefix()):
            # SUCCESS: PoW verified. Mint credits.
            return True, f"PoW Validated. Minted {self.max_credits} x402 credits to {agent_id}."
        else:
            return False, "Invalid Proof of Work. Hash does not meet difficulty target."

# =====================================================================
# AGENT-SIDE SOLVER (For the Replicator v2 clients)
# =====================================================================
def solve_hashcash(challenge: str, difficulty_bits: int) -> str:
    """
    The CPU-intensive loop run by the client agent.
    """
    target = '0' * difficulty_bits
    nonce = 0
    print(f"[*] Solving PoW challenge (Difficulty: {difficulty_bits} bits)...")
    start_time = time.time()
    
    while True:
        payload = f"{challenge}{nonce}".encode('utf-8')
        hash_result = hashlib.sha256(payload).hexdigest()
        binary_hash = bin(int(hash_result, 16))[2:].zfill(256)
        
        if binary_hash.startswith(target):
            elapsed = time.time() - start_time
            print(f"[+] PoW Solved! Nonce: {nonce} | Time: {elapsed:.2f}s | Hash: {hash_result[:16]}...")
            return str(nonce)
            
        nonce += 1

if __name__ == "__main__":
    # Simulation
    faucet = HashcashFaucet(difficulty_bits=20)
    agent = "agent_omega_99"
    
    # 1. Agent asks for credits
    print(f"--- Faucet Request for {agent} ---")
    challenge_data = faucet.generate_challenge(agent)
    print(f"Server issued challenge: {challenge_data['challenge']}")
    
    # 2. Agent burns CPU to solve it
    solution_nonce = solve_hashcash(challenge_data["challenge"], challenge_data["difficulty_bits"])
    
    # 3. Server verifies instantly
    success, msg = faucet.verify_and_mint(agent, challenge_data["challenge"], solution_nonce)
    print(f"Server verification: {msg}")
