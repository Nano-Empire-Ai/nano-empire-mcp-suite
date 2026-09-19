"""
Lifetime Value (LTV) & CAC Estimation Heuristics
Calculates cohort value, net contribution margins, and expected agent value.
"""
from typing import Dict, List, Any

DEFAULT_AGENT_CHURN_RATE = 0.15  # 15% monthly decay
DEFAULT_CALL_MARGIN = 0.85       # 85% gross margin after RPC/compute fees

def calculate_agent_ltv(agent_events: List[Dict[str, Any]], churn_rate: float = DEFAULT_AGENT_CHURN_RATE) -> float:
    if not agent_events:
        return 0.0
    
    total_spend = sum(e.get("usd_value", 0.0) for e in agent_events)
    order_count = len(agent_events)
    aov = total_spend / order_count if order_count else 0.0
    
    # Expected lifetime interactions = 1 / churn_rate
    expected_lifetime_orders = 1.0 / max(churn_rate, 0.01)
    projected_ltv = aov * expected_lifetime_orders * DEFAULT_CALL_MARGIN
    return round(projected_ltv, 2)

def calculate_channel_metrics(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    channels: Dict[str, Dict[str, Any]] = {}
    
    for ev in events:
        ch = ev.get("source", "direct")
        if ch not in channels:
            channels[ch] = {
                "total_revenue": 0.0,
                "conversions": 0,
                "unique_agents": set(),
                "tools_used": set()
            }
        channels[ch]["total_revenue"] += ev.get("usd_value", 0.0)
        channels[ch]["conversions"] += 1
        channels[ch]["unique_agents"].add(ev.get("agent_id"))
        channels[ch]["tools_used"].add(ev.get("tool_id"))
        
    summary = {}
    for ch, data in channels.items():
        unique_cnt = len(data["unique_agents"])
        rev = data["total_revenue"]
        arpu = rev / unique_cnt if unique_cnt else 0.0
        summary[ch] = {
            "channel": ch,
            "total_revenue": round(rev, 2),
            "conversions": data["conversions"],
            "unique_agents": unique_cnt,
            "arpu": round(arpu, 2),
            "estimated_ltv": round(arpu * 4.5, 2)  # 4.5x multiplier on initial ARPU
        }
    return summary
