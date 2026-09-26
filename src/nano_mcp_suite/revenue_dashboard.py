"""
Nano Empire AI - LIVE Revenue & Telemetry Dashboard
========================================================================
Connects to PRODUCTION Cerberus + Attribution DB + Treasury Yield.
NO SIMULATION - Real data only.
"""

import asyncio
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.columns import Columns
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

BASE_URL = "https://nano-empire-mcp-1064490927432.us-central1.run.app"
DB_PATH = Path(__file__).parent / "attribution.db"


class LiveDataFetcher:
    """Fetches real-time data from production endpoints and local DB."""

    def __init__(self):
        self.cerberus_stats: Dict = {}
        self.attribution_data: List[Dict] = []
        self.treasury_yield: Dict = {}
        self.channel_metrics: Dict = {}
        self.last_update: Optional[datetime] = None
        self.error: Optional[str] = None

    async def fetch_all(self):
        """Fetch all data sources concurrently."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            cerberus_task = self._fetch_cerberus(client)
            treasury_task = self._fetch_treasury(client)
            await asyncio.gather(cerberus_task, treasury_task)

        self._fetch_attribution()
        self._compute_channel_metrics()
        self.last_update = datetime.now()

    async def _fetch_cerberus(self, client: httpx.AsyncClient):
        try:
            r = await client.get(f"{BASE_URL}/cerberus/stats")
            if r.status_code == 200:
                self.cerberus_stats = r.json()
            else:
                self.error = f"Cerberus: HTTP {r.status_code}"
        except Exception as e:
            self.error = f"Cerberus fetch failed: {e}"

    async def _fetch_treasury(self, client: httpx.AsyncClient):
        try:
            r = await client.get(f"{BASE_URL}/api/v1/treasury/yield")
            if r.status_code == 200:
                self.treasury_yield = r.json()
        except Exception as e:
            self.treasury_yield = {"error": str(e)}

    def _fetch_attribution(self):
        """Read from local SQLite attribution database."""
        if not DB_PATH.exists():
            self.attribution_data = []
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT timestamp, receipt_hash, agent_id, tool_id, usd_value, source, medium, campaign
                    FROM attribution_events
                    ORDER BY timestamp DESC
                    LIMIT 500
                """)
                self.attribution_data = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.error = f"Attribution DB error: {e}"

    def _compute_channel_metrics(self):
        """Compute revenue attribution by channel."""
        self.channel_metrics = {}
        cutoff = datetime.now() - timedelta(days=7)  # 7-day window

        for event in self.attribution_data:
            try:
                ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                if ts < cutoff:
                    continue
            except Exception:
                continue

            source = event.get("source", "direct")
            usd = float(event.get("usd_value", 0))

            if source not in self.channel_metrics:
                self.channel_metrics[source] = {
                    "revenue": 0.0,
                    "transactions": 0,
                    "agents": set(),
                    "tools": set(),
                }

            m = self.channel_metrics[source]
            m["revenue"] += usd
            m["transactions"] += 1
            m["agents"].add(event.get("agent_id", "unknown"))
            m["tools"].add(event.get("tool_id", "unknown"))

        # Convert sets to counts
        for m in self.channel_metrics.values():
            m["unique_agents"] = len(m["agents"])
            m["unique_tools"] = len(m["tools"])
            del m["agents"]
            del m["tools"]


class RealRevenueDashboard:
    def __init__(self):
        self.fetcher = LiveDataFetcher()

    def make_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=10)
        )
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        layout["left"].split_column(
            Layout(name="metrics"),
            Layout(name="channels")
        )
        layout["right"].split_column(
            Layout(name="cerberus"),
            Layout(name="treasury")
        )
        return layout

    def render(self) -> Layout:
        layout = self.make_layout()

        # Header
        status_color = "green" if not self.fetcher.error else "red"
        status_text = "LIVE" if not self.fetcher.error else f"ERROR: {self.fetcher.error}"
        surge_status = self.fetcher.cerberus_stats.get("price_signal", {}).get("surge_active", False)
        surge_text = "[yellow]SURGE ACTIVE[/yellow]" if surge_status else "[dim]normal[/dim]"

        layout["header"].update(Panel(
            f"[bold cyan]NANO EMPIRE AI - LIVE REVENUE TELEMETRY[/bold cyan] | "
            f"Status: [{status_color}]{status_text}[/{status_color}] | "
            f"Surge v2: {surge_text} | "
            f"Updated: {self.fetcher.last_update.strftime('%H:%M:%S') if self.fetcher.last_update else 'never'}",
            style="bold"
        ))

        # Main Metrics (from Cerberus)
        cerberus = self.fetcher.cerberus_stats
        total_rev = cerberus.get("total_revenue_usd", 0.0)
        total_req = cerberus.get("total_requests", 0)
        blocked = cerberus.get("blocked_replays", 0)
        mab = cerberus.get("mab", {})
        pricer = cerberus.get("pricer", {})

        metrics_table = Table(show_header=False, expand=True)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green", justify="right")
        metrics_table.add_row("Total x402 Revenue (all-time)", f"${total_rev:.4f}")
        metrics_table.add_row("Total Requests", f"{total_req:,}")
        metrics_table.add_row("Replay Attacks Blocked", f"[red]{blocked:,}[/red]")
        metrics_table.add_row("Current Price/Call", f"${pricer.get('current_price_usd', 0):.4f}")
        metrics_table.add_row("Load Ratio", f"{pricer.get('load_ratio', 0):.1%}")
        metrics_table.add_row("Active Connections", str(pricer.get("active_connections", 0)))
        layout["metrics"].update(Panel(metrics_table, title="[bold]Cerberus Gateway[/bold]"))

        # MAB Arm Performance
        cerberus_table = Table(expand=True)
        cerberus_table.add_column("Arm", style="magenta")
        cerberus_table.add_column("Pulls", justify="right")
        cerberus_table.add_column("Win Rate", justify="right")
        cerberus_table.add_column("Avg Reward", justify="right")
        for name, stats in mab.items():
            cerberus_table.add_row(
                name,
                str(stats.get("pulls", 0)),
                f"{stats.get('expected_prob', 0):.1%}",
                f"{stats.get('mean_reward', 0):.1f}"
            )
        layout["cerberus"].update(Panel(cerberus_table, title="[bold]MAB Router Arms (Thompson Sampling)[/bold]"))

        # Treasury Yield
        ty = self.fetcher.treasury_yield
        treasury_table = Table(show_header=False, expand=True)
        treasury_table.add_column("Pool", style="yellow")
        treasury_table.add_column("Value", style="green", justify="right")
        if "error" not in ty:
            treasury_table.add_row("Treasury Wallet", ty.get("treasury_wallet", "N/A")[:12] + "...")
            treasury_table.add_row("Active Yield Floor", f"${ty.get('active_yield_floor_usd', 0):,.2f}")
            treasury_table.add_row("APY Target", f"{ty.get('apy_target', 0)*100:.1f}%")
            treasury_table.add_row("Status", ty.get("status", "unknown"))
            treasury_table.add_row("Infra Coverage", ty.get("infra_coverage", "N/A"))
        else:
            treasury_table.add_row("Error", ty.get("error", "unknown"))
        layout["treasury"].update(Panel(treasury_table, title="[bold]Treasury Yield[/bold]"))

        # Channel Attribution (24h)
        channel_table = Table(expand=True)
        channel_table.add_column("Channel", style="cyan")
        channel_table.add_column("Revenue (24h)", justify="right", style="green")
        channel_table.add_column("Txns", justify="right")
        channel_table.add_column("Agents", justify="right")
        channel_table.add_column("Tools", justify="right")

        total_24h = 0
        total_txns_24h = 0
        for ch, m in sorted(self.fetcher.channel_metrics.items(), key=lambda x: -x[1]["revenue"]):
            channel_table.add_row(
                ch,
                f"${m['revenue']:.4f}",
                str(m["transactions"]),
                str(m["unique_agents"]),
                str(m["unique_tools"])
            )
            total_24h += m["revenue"]
            total_txns_24h += m["transactions"]

        if not self.fetcher.channel_metrics:
            channel_table.add_row("[dim]No attribution data in last 7 days[/dim]", "", "", "", "")

        channel_table.add_row("[bold]TOTAL[/bold]", f"[bold]${total_24h:.4f}[/bold]", f"[bold]{total_txns_24h}[/bold]", "", "")
        layout["channels"].update(Panel(channel_table, title="[bold]Revenue Attribution (7d)[/bold]"))

        # Recent Transactions Feed
        tx_table = Table(expand=True)
        tx_table.add_column("Time")
        tx_table.add_column("Agent", style="magenta")
        tx_table.add_column("Tool", style="blue")
        tx_table.add_column("Revenue", justify="right", style="green")
        tx_table.add_column("Channel", style="yellow")

        for event in self.fetcher.attribution_data[:10]:
            try:
                ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                time_str = ts.strftime("%H:%M:%S")
            except Exception:
                time_str = event["timestamp"][:8]

            tx_table.add_row(
                time_str,
                event.get("agent_id", "unknown")[:12],
                event.get("tool_id", "unknown")[:18],
                f"${float(event.get('usd_value', 0)):.4f}",
                event.get("source", "direct")
            )

        if not self.fetcher.attribution_data:
            tx_table.add_row("[dim]No transactions recorded[/dim]", "", "", "", "")

        layout["footer"].update(Panel(tx_table, title="[bold]Live Settlement Feed (last 10)[/bold]"))

        return layout

    async def run(self, refresh_seconds: float = 5.0):
        """Run the live dashboard."""
        # Initial fetch
        await self.fetcher.fetch_all()

        with Live(self.render(), refresh_per_second=1/refresh_seconds, console=console) as live:
            while True:
                await asyncio.sleep(refresh_seconds)
                await self.fetcher.fetch_all()
                live.update(self.render())


async def main():
    dashboard = RealRevenueDashboard()
    try:
        await dashboard.run(refresh_seconds=5.0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())