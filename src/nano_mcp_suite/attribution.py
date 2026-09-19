import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "attribution.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attribution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                receipt_hash TEXT,
                agent_id TEXT,
                tool_id TEXT,
                usd_value REAL,
                source TEXT,
                medium TEXT,
                campaign TEXT
            )
        """)
        conn.commit()

def parse_attribution(attribution_str: str):
    """
    Parses 'source=x_radar,medium=outbound,campaign=offer_123'
    """
    if not attribution_str:
        return {"source": "direct", "medium": "none", "campaign": "none"}
        
    parts = {}
    for pair in attribution_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            parts[k.strip()] = v.strip()
    return {
        "source": parts.get("source", "direct"),
        "medium": parts.get("medium", "none"),
        "campaign": parts.get("campaign", "none")
    }

def process_tollbooth_payment(receipt_hash: str, agent_id: str, tool_id: str, usd_value: float, attribution_header: str):
    # Security Validation
    if not isinstance(usd_value, (int, float)):
        try:
            usd_value = float(usd_value)
        except ValueError:
            raise ValueError(f"usd_value must be numeric, got {type(usd_value).__name__}")
            
    if usd_value < 0:
        raise ValueError(f"CRITICAL: Negative revenue detected ({usd_value}). Possible refund exploit attempt.")
        
    if usd_value > 10000.0:  # Arbitrary ceiling for tollbooth payments
        raise ValueError(f"CRITICAL: Anomalous revenue value ({usd_value}). Exceeds $10k per-transaction limit.")

    # Sanitize inputs
    agent_id = str(agent_id).strip()
    if len(agent_id) > 100 or ';' in agent_id or '--' in agent_id:
         # Log anomalous agent ID but strip malicious chars for safety
         agent_id = ''.join(e for e in agent_id if e.isalnum() or e in ['_', '-'])

    init_db()
    attr = parse_attribution(attribution_header)
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO attribution_events 
            (timestamp, receipt_hash, agent_id, tool_id, usd_value, source, medium, campaign)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            receipt_hash,
            agent_id,
            tool_id,
            usd_value,
            attr["source"],
            attr["medium"],
            attr["campaign"]
        ))
        conn.commit()
    
    # Sync to Turso Cloud Edge DB if available
    try:
        import sys
        empire_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if empire_root not in sys.path:
            sys.path.insert(0, empire_root)
        from intelligence.turso_edge_bridge import TursoEdgeBridge
        bridge = TursoEdgeBridge()
        if bridge.is_configured():
            bridge.record_receipt(
                receipt_id=receipt_hash,
                agent_id=agent_id,
                tool_id=tool_id,
                usd_value=usd_value,
                source=attr.get("source", "direct"),
                raw_attr=attribution_header
            )
            print(f"[Attribution] Synced receipt {receipt_hash[:12]} to Turso Edge DB")
    except Exception as e:
        print(f"[Attribution] Turso sync skipped: {e}")

    print(f"[Attribution] Logged ${usd_value} to {attr['source']} / {attr['campaign']}")
    return True
