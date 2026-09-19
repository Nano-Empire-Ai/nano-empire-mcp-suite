"""
Unit Tests for Attribution Engine
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from empire.analytics.attribution_db import insert_event, fetch_all_events
from empire.analytics.attribution import parse_attribution_header, record_attribution
from empire.analytics.ltv import calculate_channel_metrics
from empire.analytics.rebalance import compute_rebalance

def test_parse_attribution_header():
    raw = "source=x_radar,medium=outbound,campaign=bounty_123"
    attr = parse_attribution_header(raw)
    assert attr["source"] == "x_radar"
    assert attr["medium"] == "outbound"
    assert attr["campaign"] == "bounty_123"

def test_attribution_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name
    try:
        ok = record_attribution(
            receipt_hash="tx_sample_test_receipt",
            agent_id="agent_apex",
            tool_id="sybil_scan",
            usd_value=0.50,
            attribution_header="source=x_radar,medium=dm,campaign=pumpfun_scan",
            db_path=tmp_db
        )
        assert ok is True
        
        events = fetch_all_events(db_path=tmp_db)
        assert len(events) == 1
        assert events[0]["usd_value"] == 0.50
        assert events[0]["source"] == "x_radar"
        
        metrics = calculate_channel_metrics(events)
        assert "x_radar" in metrics
        assert metrics["x_radar"]["total_revenue"] == 0.50
        
        reb = compute_rebalance(daily_budget_usd=100.0, db_path=tmp_db)
        assert "x_radar" in reb["allocations"]
    finally:
        import gc
        gc.collect()
        try:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)
        except Exception:
            pass

if __name__ == "__main__":
    test_parse_attribution_header()
    test_attribution_lifecycle()
    print("All attribution tests PASSED successfully!")
