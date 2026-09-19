"""
Nano Empire AI - Live Revenue & Telemetry Dashboard
========================================================================
Visualizes the Machine Economy in real-time.
Tracks x402 payments, Cerberus routing metrics, and A2A viral loops.
"""

import time
import random
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

console = Console()

class MachineEconomyDashboard:
    def __init__(self):
        self.total_revenue_usd = 0.00
        self.active_agents = 0
        self.total_tx_count = 0
        self.blocked_replays = 412
        self.yield_generated = 12.45  # From 14.25K Jito/Kamino
        
        # Simulated stream of agent traffic
        self.recent_txs = []

    def generate_simulated_traffic(self):
        """Simulates incoming traffic from the Replicator v2 PR injections."""
        if random.random() > 0.3:  # 70% chance of a transaction per tick
            agent_id = f"agent_{random.randint(1000, 9999)}"
            tool = random.choice(["market_sentiment", "dex_execute", "web_scrape", "zk_verify"])
            price = round(random.uniform(0.01, 0.05), 4)
            latency = random.randint(12, 45)
            
            self.total_revenue_usd += price
            self.total_tx_count += 1
            if random.random() > 0.8:
                self.active_agents += 1
                
            self.recent_txs.insert(0, (datetime.now().strftime("%H:%M:%S"), agent_id, tool, f"${price}", f"{latency}ms", "202 ACCEPTED"))
            if len(self.recent_txs) > 5:
                self.recent_txs.pop()
                
        if random.random() > 0.9: # 10% chance of replay attack
            self.blocked_replays += 1
            self.recent_txs.insert(0, (datetime.now().strftime("%H:%M:%S"), "UNKNOWN_BOT", "REPLAY_ATTACK", "$0.00", "5ms", "[red]409 BLOCKED[/red]"))
            if len(self.recent_txs) > 5:
                self.recent_txs.pop()

    def make_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=8)
        )
        layout["main"].split_row(
            Layout(name="metrics"),
            Layout(name="yield")
        )
        return layout

    def render(self) -> Layout:
        self.generate_simulated_traffic()
        layout = self.make_layout()
        
        # Header
        layout["header"].update(Panel(f"[bold cyan]NANO EMPIRE AI - CERBERUS ROUTER TELEMETRY[/bold cyan] | Status: [green]LIVE[/green] | Surge v3: [yellow]ACTIVE[/yellow]"))
        
        # Metrics Table
        metrics_table = Table(show_header=False, expand=True)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green", justify="right")
        metrics_table.add_row("Total x402 Revenue (24h)", f"${self.total_revenue_usd:.4f}")
        metrics_table.add_row("Total Transactions", str(self.total_tx_count))
        metrics_table.add_row("Active Agents", str(self.active_agents))
        metrics_table.add_row("Replay Attacks Blocked", f"[red]{self.blocked_replays}[/red]")
        layout["metrics"].update(Panel(metrics_table, title="[bold]Cerberus Gateway Metrics[/bold]"))
        
        # Yield Table
        yield_table = Table(show_header=False, expand=True)
        yield_table.add_column("Pool", style="yellow")
        yield_table.add_column("Value", style="green", justify="right")
        yield_table.add_row("Treasury TVL", "$14,250.00 USDC")
        yield_table.add_row("Jito (7.2% APY)", "$7,125.00")
        yield_table.add_row("Kamino (8.5% APY)", "$7,125.00")
        yield_table.add_row("Auto-Compounded Yield", f"+${self.yield_generated:.2f}")
        layout["yield"].update(Panel(yield_table, title="[bold]Treasury & DeFi Yield[/bold]"))
        
        # Transaction Feed
        tx_table = Table(expand=True)
        tx_table.add_column("Time")
        tx_table.add_column("Agent ID", style="magenta")
        tx_table.add_column("Target Tool", style="blue")
        tx_table.add_column("x402 Toll", justify="right", style="green")
        tx_table.add_column("Latency")
        tx_table.add_column("Status")
        
        for tx in self.recent_txs:
            tx_table.add_row(*tx)
            
        layout["footer"].update(Panel(tx_table, title="[bold]Live x402 Settlement Feed[/bold]"))
        
        return layout

if __name__ == "__main__":
    dashboard = MachineEconomyDashboard()
    print("Initializing Cerberus Dashboard...")
    with Live(dashboard.render(), refresh_per_second=2) as live:
        for _ in range(20):  # Simulate 10 seconds of live traffic
            time.sleep(0.5)
            live.update(dashboard.render())
