"""
Attribution Database Layer
Handles SQLite local caching and Turso Edge DB synchronization.
"""
import sqlite3
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "attribution.db")

def _get_turso_bridge():
    try:
        empire_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if empire_root not in sys.path:
            sys.path.insert(0, empire_root)
        from intelligence.turso_edge_bridge import TursoEdgeBridge
        bridge = TursoEdgeBridge()
        if bridge.is_configured():
            return bridge
    except Exception:
        pass
    return None

def init_db(db_path: str = DB_PATH):
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attribution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                receipt_hash TEXT NOT NULL UNIQUE,
                agent_id TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                usd_value REAL NOT NULL,
                source TEXT NOT NULL,
                medium TEXT NOT NULL,
                campaign TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaign_metrics (
                campaign TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                total_spend REAL DEFAULT 0.0,
                total_revenue REAL DEFAULT 0.0,
                conversions INTEGER DEFAULT 0,
                ltv_estimate REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budget_allocations (
                channel TEXT PRIMARY KEY,
                allocated_usd REAL NOT NULL,
                target_share REAL NOT NULL,
                status TEXT DEFAULT 'active',
                updated_at TEXT NOT NULL
            );
        """)
        conn.commit()

def insert_event(receipt_hash: str, agent_id: str, tool_id: str, usd_value: float, source: str, medium: str, campaign: str, db_path: str = DB_PATH) -> bool:
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO attribution_events
                (timestamp, receipt_hash, agent_id, tool_id, usd_value, source, medium, campaign)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, receipt_hash, agent_id, tool_id, usd_value, source, medium, campaign))
            conn.commit()
    except Exception as e:
        print(f"[AttributionDB] SQLite insert error: {e}")
        return False

    # Sync to Turso Edge DB
    bridge = _get_turso_bridge()
    if bridge:
        try:
            bridge.record_receipt(
                receipt_id=receipt_hash,
                agent_id=agent_id,
                tool_id=tool_id,
                usd_value=usd_value,
                source=source,
                raw_attr=f"source={source},medium={medium},campaign={campaign}"
            )
        except Exception as e:
            print(f"[AttributionDB] Turso sync warning: {e}")

    return True

def fetch_all_events(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM attribution_events ORDER BY timestamp DESC")
        return [dict(row) for row in cur.fetchall()]

def fetch_events_by_channel(db_path: str = DB_PATH) -> Dict[str, List[Dict[str, Any]]]:
    events = fetch_all_events(db_path)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        ch = ev.get("source", "direct")
        grouped.setdefault(ch, []).append(ev)
    return grouped
