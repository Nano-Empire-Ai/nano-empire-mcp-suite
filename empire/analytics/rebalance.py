"""
Daily Dynamic Capital & Resource Rebalancing
Shifts compute, API budget, and outreach volume to highest-yield channels.
"""
from typing import Dict, Any
from empire.analytics.attribution_db import fetch_all_events
from empire.analytics.ltv import calculate_channel_metrics

BASE_CHANNELS = ["x_radar", "github_bounty", "agentmail_outbound", "smithery_inbound"]

def compute_rebalance(daily_budget_usd: float = 50.0, db_path: str = None) -> Dict[str, Any]:
    kwargs = {"db_path": db_path} if db_path else {}
    events = fetch_all_events(**kwargs)
    metrics = calculate_channel_metrics(events)
    
    # Baseline allocation weights
    weights = {ch: 1.0 for ch in BASE_CHANNELS}
    
    # Weight booster based on revenue generation
    for ch, m in metrics.items():
        if ch in weights:
            weights[ch] += m.get("total_revenue", 0.0) * 2.0
            
    total_weight = sum(weights.values())
    allocations = {}
    
    for ch, w in weights.items():
        share = w / total_weight
        allocations[ch] = {
            "allocated_usd": round(daily_budget_usd * share, 2),
            "target_share_pct": round(share * 100, 1),
            "observed_revenue": metrics.get(ch, {}).get("total_revenue", 0.0)
        }
        
    return {
        "daily_budget_usd": daily_budget_usd,
        "allocations": allocations,
        "metrics": metrics
    }
