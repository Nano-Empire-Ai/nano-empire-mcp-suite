"""
Core Attribution Logic
Parses x402 and attribution headers, attributes revenue, and logs events.
"""
from typing import Dict, Any, Optional
from empire.analytics.attribution_db import insert_event, fetch_all_events

def parse_attribution_header(attribution_str: Optional[str]) -> Dict[str, str]:
    if not attribution_str:
        return {"source": "direct", "medium": "none", "campaign": "organic"}
    
    parts = {}
    for pair in attribution_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            parts[k.strip().lower()] = v.strip()
            
    return {
        "source": parts.get("source", "direct"),
        "medium": parts.get("medium", "none"),
        "campaign": parts.get("campaign", "organic")
    }

def record_attribution(receipt_hash: str, agent_id: str, tool_id: str, usd_value: float, attribution_header: Optional[str], db_path: Optional[str] = None) -> bool:
    attr = parse_attribution_header(attribution_header)
    kwargs = {"db_path": db_path} if db_path else {}
    ok = insert_event(
        receipt_hash=receipt_hash,
        agent_id=agent_id,
        tool_id=tool_id,
        usd_value=usd_value,
        source=attr["source"],
        medium=attr["medium"],
        campaign=attr["campaign"],
        **kwargs
    )
    return ok
