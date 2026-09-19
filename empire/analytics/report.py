"""
Attribution & Revenue Reporting Generator
Generates executive briefings and formatted markdown reports.
"""
from empire.analytics.rebalance import compute_rebalance

def generate_report(db_path: str = None) -> str:
    data = compute_rebalance(daily_budget_usd=50.0, db_path=db_path)
    alloc = data["allocations"]
    metrics = data["metrics"]
    
    total_rev = sum(m.get("total_revenue", 0.0) for m in metrics.values())
    total_conv = sum(m.get("conversions", 0) for m in metrics.values())
    
    lines = [
        "# [REPORT] NANO EMPIRE - REVENUE ATTRIBUTION REPORT",
        f"**Total Attributed Revenue:** ${total_rev:.2f} | **Total Paid Calls:** {total_conv}",
        "",
        "## [METRICS] Channel Performance",
        "| Channel | Revenue | Conversions | Unique Agents | Est. LTV |",
        "|---|---|---|---|---|"
    ]
    
    for ch, m in metrics.items():
        lines.append(f"| `{ch}` | ${m['total_revenue']:.2f} | {m['conversions']} | {m['unique_agents']} | ${m['estimated_ltv']:.2f} |")
        
    lines.extend([
        "",
        "## [REBALANCE] Next 24H Resource & Budget Rebalance",
        "| Channel | Allocated Budget | Share (%) |",
        "|---|---|---|"
    ])
    
    for ch, a in alloc.items():
        lines.append(f"| `{ch}` | ${a['allocated_usd']:.2f} | {a['target_share_pct']}% |")
        
    lines.append("")
    return "\n".join(lines)
