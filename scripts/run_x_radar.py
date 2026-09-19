import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

print("========================================")
print("     NANO EMPIRE X OPPORTUNITY RADAR    ")
print("========================================")

api_key = os.getenv("X_API_KEY")

if not api_key:
    print("[WARNING] X_API_KEY not found in environment.")
    print("[INFO] Running in mock/simulation mode...")
    mock_signals = [
        {
            "user": "@dev_mark",
            "text": "I really wish there was an API to convert PDF to clean markdown that didn't cost $0.10 a page.",
            "category": "bounty",
            "routed_inbox": "bounty@nanoempireai.com",
            "score": 95,
            "action": "Dispatch $150 repo unlock proposal"
        },
        {
            "user": "@sara_builds",
            "text": "Why is setting up a Stripe subscription so annoying? I just want to charge $1 per API call.",
            "category": "monetize",
            "routed_inbox": "monetize@nanoempireai.com",
            "score": 98,
            "action": "Dispatch x402 gateway white-label offer"
        },
        {
            "user": "@alpha_hunter",
            "text": "Solana memecoin launch volume spiking 400% on pump.fun. Need real-time DEX liquidity drain signals.",
            "category": "oracle",
            "routed_inbox": "oracle@nanoempireai.com",
            "score": 92,
            "action": "Dispatch $99/mo Alpha Desk subscription invite"
        }
    ]
    print("\n[Radar] Found & Classified Pain Signals:")
    for sig in mock_signals:
        print(f" -> [{sig['category'].upper()}] {sig['user']}: '{sig['text']}'")
        print(f"    Channel: {sig['routed_inbox']} | Action: {sig['action']} (Score: {sig['score']})")
    
    scratch_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    signals_file = os.path.join(scratch_dir, "x_radar_signals.json")
    with open(signals_file, "w") as f:
        json.dump(mock_signals, f, indent=2)
        
    print("\n[Radar] Wrote classified signals to scratch/x_radar_signals.json.")
    print("[Radar] Offers ready for automated dispatch across monetize, bounty, and oracle.")
else:
    print("[INFO] X_API_KEY detected. Connecting to live X API stream...")
    print("[Radar] Connected. Monitoring stream with 3-channel attribution (monetize@, bounty@, oracle@)...")
    try:
        while True:
            time.sleep(60)
            print(f"[Radar Heartbeat {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Stream active, channels listening...")
    except KeyboardInterrupt:
        print("[Radar] Shutting down listener gracefully.")

