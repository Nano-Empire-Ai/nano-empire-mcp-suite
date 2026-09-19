"""
Nano Empire AI - Dynamic MCP Registry (The Universal Agent Search Engine)
========================================================================
A decentralized, dynamic service discovery mesh for AI agents. 
Allows agents to search for MCP tools by semantic capability, price, and latency.
Obsoletes static registries (Glama/RapidAPI).
"""

import time
import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class MCPToolCapability:
    name: str
    description: str
    input_schema: Dict
    output_schema: Dict

@dataclass
class MCPNode:
    node_id: str
    endpoint_url: str
    owner_wallet: str
    capabilities: List[MCPToolCapability]
    base_price_usd: float
    last_heartbeat: int
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 100.0

    @property
    def uptime_score(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

class DynamicMCPRegistry:
    """
    The central intelligence for dynamic tool discovery.
    Matches agent intents to the most optimal, cost-effective MCP node.
    """
    def __init__(self):
        # Node storage: node_id -> MCPNode
        self.nodes: Dict[str, MCPNode] = {}
        # Inverted index: capability_keyword -> List[node_id]
        self.capability_index: Dict[str, set] = defaultdict(set)
        
        # Scoring weights for discovery routing
        self.WEIGHT_PRICE = 0.5
        self.WEIGHT_LATENCY = 0.3
        self.WEIGHT_UPTIME = 0.2

    def register_node(self, node: MCPNode):
        """Register a new MCP server onto the grid."""
        self.nodes[node.node_id] = node
        
        # Index capabilities for fast search
        for cap in node.capabilities:
            # Simple keyword extraction (in production, use embedding vectors)
            keywords = set(cap.name.lower().split("_") + cap.description.lower().split())
            for kw in keywords:
                if len(kw) > 3:  # ignore stop words roughly
                    self.capability_index[kw].add(node.node_id)
                    
        print(f"[Registry] Node {node.node_id} registered with {len(node.capabilities)} tools.")

    def record_telemetry(self, node_id: str, success: bool, latency_ms: float):
        """Update a node's reputation and latency metrics dynamically."""
        if node_id not in self.nodes:
            return
            
        node = self.nodes[node_id]
        if success:
            node.success_count += 1
        else:
            node.failure_count += 1
            
        # Exponential moving average for latency
        alpha = 0.1
        node.avg_latency_ms = (alpha * latency_ms) + ((1 - alpha) * node.avg_latency_ms)
        node.last_heartbeat = int(time.time())

    def _calculate_routing_score(self, node: MCPNode) -> float:
        """
        Calculates the predatory routing score.
        High score = cheap, fast, and reliable.
        """
        # Normalize price (lower is better, avoid div by zero)
        safe_price = max(node.base_price_usd, 0.0001)
        price_score = 1.0 / safe_price
        
        # Normalize latency (lower is better)
        safe_latency = max(node.avg_latency_ms, 1.0)
        latency_score = 1000.0 / safe_latency
        
        score = (
            (price_score * self.WEIGHT_PRICE) +
            (latency_score * self.WEIGHT_LATENCY) +
            (node.uptime_score * self.WEIGHT_UPTIME)
        )
        return score

    def discover_tools(self, query: str, max_price_usd: float = 1.0) -> List[Dict]:
        """
        The Search Engine: Agents query for a capability (e.g., 'scrape_web').
        Returns ranked endpoints based on price, speed, and reliability.
        """
        query_terms = set(query.lower().split())
        matched_node_ids = set()
        
        for term in query_terms:
            if term in self.capability_index:
                if not matched_node_ids:
                    matched_node_ids = self.capability_index[term]
                else:
                    matched_node_ids = matched_node_ids.intersection(self.capability_index[term])
        
        # Fallback to union if intersection is empty
        if not matched_node_ids:
            for term in query_terms:
                matched_node_ids.update(self.capability_index.get(term, set()))
                
        # Filter and rank
        candidates = []
        for nid in matched_node_ids:
            node = self.nodes[nid]
            
            # Prune dead nodes (no heartbeat in 5 mins)
            if int(time.time()) - node.last_heartbeat > 300:
                continue
                
            if node.base_price_usd <= max_price_usd:
                score = self._calculate_routing_score(node)
                candidates.append((score, node))
                
        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Format the output for the agent
        results = []
        for score, node in candidates:
            # Find the specific capability that matches best
            best_cap = node.capabilities[0] # Simplification
            
            results.append({
                "node_id": node.node_id,
                "endpoint_url": node.endpoint_url,
                "tool_name": best_cap.name,
                "description": best_cap.description,
                "price_usd": node.base_price_usd,
                "latency_ms": round(node.avg_latency_ms, 2),
                "routing_score": round(score, 4),
                "payment_wallet": node.owner_wallet
            })
            
        return results

# =====================================================================
# GLOBAL REGISTRY INSTANCE
# =====================================================================
global_mcp_registry = DynamicMCPRegistry()

if __name__ == "__main__":
    # Quick Simulation Test
    reg = DynamicMCPRegistry()
    
    # 1. Register High-Quality / High-Price Node (Ornn Frontier Cloud)
    reg.register_node(MCPNode(
        node_id="ornn-frontier-01",
        endpoint_url="https://api.ornn.io/mcp/scrape",
        owner_wallet="ornn_wallet...",
        capabilities=[MCPToolCapability("scrape_web", "Deep semantic web scraping", {}, {})],
        base_price_usd=0.05,
        last_heartbeat=int(time.time()),
        avg_latency_ms=45.0,
        success_count=1000
    ))
    
    # 2. Register Low-Quality / Cheap Node (Local Lambert 3)
    reg.register_node(MCPNode(
        node_id="lambert-local-03",
        endpoint_url="http://192.168.1.10:8404/mcp/scrape",
        owner_wallet="lambert_wallet...",
        capabilities=[MCPToolCapability("scrape_web_basic", "Fast basic web scraping", {}, {})],
        base_price_usd=0.001,
        last_heartbeat=int(time.time()),
        avg_latency_ms=250.0,  # Slower
        success_count=50,
        failure_count=5
    ))
    
    print("\\n[+] Simulating Agent Search for: 'scrape web'")
    results = reg.discover_tools("scrape web", max_price_usd=0.10)
    
    for rank, res in enumerate(results, 1):
        print(f"Rank {rank}: {res['node_id']} | Price: ${res['price_usd']} | Latency: {res['latency_ms']}ms | Score: {res['routing_score']}")
