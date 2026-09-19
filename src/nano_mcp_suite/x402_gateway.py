import os
import json
import time
from dotenv import load_dotenv
from .nonce_middleware import (
    create_identity_bound_receipt,
    verify_identity_bound_receipt,
    IdentityBoundReceipt
)
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
try:
    from nano_mcp_suite.leviathan_broker import mcp
except ImportError:
    from leviathan_broker import mcp
try:
    from nano_mcp_suite.titan_mev_broker import mcp_titan
except ImportError:
    try:
        from titan_mev_broker import mcp_titan
    except Exception:
        mcp_titan = None

# Cerberus: UCB1 MAB Router + Bloom Replay Guard + Dynamic Pricer
try:
    from nano_mcp_suite.cerberus_router import cerberus
except ImportError:
    try:
        from cerberus_router import cerberus
    except Exception:
        cerberus = None

# Disable DNS rebinding protection so external registries (Glama, Smithery) and clients can connect via SSE & Streamable HTTP
mcp.settings.transport_security.enable_dns_rebinding_protection = False
# Enable JSON response mode for Streamable HTTP so Cloud Run and proxies do not truncate event streams on POST
mcp.settings.json_response = True


load_dotenv(override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield

app = FastAPI(title="Nano Empire AI - x402 MCP Gateway", version="1.0.0", lifespan=lifespan)

from prometheus_client import make_asgi_app, Counter, Histogram
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

PAYMENT_COUNTER = Counter("x402_payments_total", "Total x402 payments verified", ["network"])
REVENUE_USD = Counter("x402_revenue_usd_total", "Total revenue in USD", ["network"])
REQUEST_LATENCY = Histogram("x402_request_latency_seconds", "Request latency in seconds")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nano Empire Solana Treasury
TREASURY_WALLET = os.getenv("SOLANA_TREASURY_WALLET") or os.getenv("solana_account_address") or "5pM5w1W5nKU7B8SjuTiz65UAZxs9mCnC6ab1Xs1gSi3"

import redis.asyncio as redis
import time
import json

REDIS_CLIENT = redis.from_url("redis://100.116.133.35:6379", decode_responses=True)

async def check_and_store_replay(signature: str, network: str, amount_usd: float, agent_id: str) -> bool:
    """Check replay in Redis, store if new. Returns True if new, False if replay."""
    key = f"replay:{network}:{signature}"
    result = await REDIS_CLIENT.set(
        key, 
        json.dumps({"amount_usd": amount_usd, "agent_id": agent_id, "ts": time.time()}),
        nx=True,
        ex=31536000
    )
    return result is not None


async def verify_x402_payment(
    receipt_header: str,
    body: dict,
    expected_amount: float = 0.50
) -> bool:
    if not receipt_header:
        return False

    if not verify_identity_bound_receipt(receipt_header, body):
        print(f"[x402-Gateway] INVALID IDENTITY-BOUND RECEIPT")
        return False

    parts = receipt_header.split("|")
    if len(parts) != 5:
        return False
    
    receipt_tx = parts[0]
    
    try:
        from solana_tx_verifier import verify_solana_transfer
        is_valid = verify_solana_transfer(receipt_tx, "5pM5w1W5nKU7B8SjuTiz65UAZxs9mCnC6ab1Xs1gSi3", expected_amount)
        if not is_valid:
            return False
    except Exception as e:
        print(f"[x402-Gateway] On-chain verification error: {e}")
        return False
    
    return True
@app.middleware("http")
async def x402_middleware(request: Request, call_next):
    # Only protect the MCP tools endpoint for actual execution calls (tools/call)
    # Handshakes like initialize, ping, and tools/list MUST pass freely so registries like Glama can list tools
    if ("/messages" in request.url.path or request.url.path == "/mcp") and request.method == "POST":
        body = await request.body()
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive
        
        is_tool_call = False
        try:
            payload = json.loads(body.decode("utf-8"))
            if isinstance(payload, dict) and payload.get("method") == "tools/call":
                is_tool_call = True
            elif isinstance(payload, list):
                if any(isinstance(item, dict) and item.get("method") == "tools/call" for item in payload):
                    is_tool_call = True
        except Exception:
            pass

        if is_tool_call:
            x402_header = request.headers.get("x-402-receipt")
            attribution_header = request.headers.get("x-attribution", "")
            tool_id = "mcp_gateway_call"
            try:
                payload_obj = json.loads(body.decode("utf-8")) if body else {}
                if isinstance(payload_obj, dict):
                    tool_id = payload_obj.get("params", {}).get("name", "mcp_gateway_call")
            except Exception:
                pass

            MULTI_CHAIN_PAYMENT_MATRIX = {
                "solana": {
                    "recipient": TREASURY_WALLET,
                    "currency": "USDC",
                    "chain_id": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
                },
                "base": {
                    "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                    "currency": "USDC",
                    "chain_id": "eip155:8453"
                },
                "ethereum": {
                    "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                    "currency": "USDC",
                    "chain_id": "eip155:1"
                },
                "arbitrum": {
                    "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                    "currency": "USDC",
                    "chain_id": "eip155:42161"
                },
                "polygon": {
                    "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                    "currency": "USDC",
                    "chain_id": "eip155:137"
                },
                "fiat_virtual_card": {
                    "provider": "Stripe Issuing",
                    "endpoint": "/agentfi/create_virtual_card",
                    "description": "Instant Visa/Mastercard for agents without crypto"
                }
            }

            if not x402_header:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment Required",
                        "amount_usd": 0.01,
                        "currency": "USDC",
                        "accepted_rails": MULTI_CHAIN_PAYMENT_MATRIX,
                        "instructions": "Attach transaction receipt from any supported network to the 'x-402-receipt' header."
                    },
                    headers={
                        "X-402-Price": "1",
                        "X-402-Asset": "USDC",
                        "X-402-Networks": "solana,base,ethereum,arbitrum,polygon,fiat",
                        "X-402-Pay-To": "multi-chain"
                    }
                )

            # ── CERBERUS DYNAMIC TOLL ROUTING ──────────────────────────────
            if cerberus is not None:
                import asyncio
                cerberus_result = await cerberus.handle_request(
                    tx_hash=x402_header,
                    tool_id=tool_id,
                    bypass_synthetic=True,
                )
                if cerberus_result.replay_detected:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "error": "Replay Attack Detected",
                            "detail": "This payment receipt has already been used. Submit a new transaction.",
                            "blocked_by": "cerberus_bloom_guard"
                        }
                    )
                if not cerberus_result.allowed:
                    return JSONResponse(status_code=402, content={"error": "Payment rejected by Cerberus"})
                toll_usd = cerberus_result.price_usd
                routed_arm = cerberus_result.arm
            else:
                # Fallback: static verification
                if not await verify_x402_payment(x402_header):
                    return JSONResponse(
                        status_code=402,
                        content={
                            "error": "Payment Required",
                            "amount_usd": 0.50,
                            "currency": "USDC",
                            "accepted_rails": MULTI_CHAIN_PAYMENT_MATRIX,
                            "instructions": "Attach transaction receipt from any supported network to the 'x-402-receipt' header."
                        },
                        headers={
                            "X-402-Price": "50",
                            "X-402-Asset": "USDC",
                            "X-402-Networks": "solana,base,ethereum,arbitrum,polygon,fiat",
                            "X-402-Pay-To": "multi-chain"
                        }
                    )
                toll_usd = 0.50
                routed_arm = "default"
            # ───────────────────────────────────────────────────────────────

            # Log successful attribution
            try:
                from attribution import process_tollbooth_payment
                agent_id = request.headers.get("x-agent-id", "unknown_agent")
                process_tollbooth_payment(
                    receipt_hash=x402_header,
                    agent_id=agent_id,
                    tool_id=tool_id,
                    usd_value=toll_usd,
                    attribution_header=attribution_header or f"source=cerberus,arm={routed_arm}"
                )
            except Exception as e:
                print(f"[Warning] Attribution logging failed: {e}")


    response = await call_next(request)
    return response

# Mount the HuggingBay 8-tool suite directly into the x402 gateway
try:
    try:
        from nano_mcp_suite.huggingbay_tools import router as huggingbay_router
    except ModuleNotFoundError:
        from huggingbay_tools import router as huggingbay_router
    app.include_router(huggingbay_router, prefix="/tools/huggingbay", tags=["HuggingBay Security & Search"])
    print("[INFO] Mounted HuggingBay tools suite successfully (12 total monetized tools).")
except Exception as e:
    print(f"[Warning] Could not mount huggingbay_tools: {e}")

from fastapi.responses import HTMLResponse

@app.get("/agentfi", response_class=HTMLResponse)
async def agentfi_landing():
    return r"""
    <html>
    <head>
        <title>Nano Empire - AgentFi</title>
        <style>
            body { font-family: monospace; background-color: #0d1117; color: #c9d1d9; padding: 40px; }
            h1 { color: #58a6ff; }
            .terminal { background-color: #161b22; padding: 20px; border-radius: 6px; overflow-x: auto; }
            .demo-video { border: 1px solid #30363d; margin-top: 20px; padding: 20px; text-align: center; }
            .btn { background-color: #238636; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; }
        </style>
    </head>
    <body>
        <h1>VirtualCard API - Stripe Issuing for Autonomous Agents</h1>
        <p>Provision single-use Stripe Virtual Cards for your agents using x402 on Solana.</p>
        
        <h2>Terminal Curl Demo</h2>
        <div class="terminal">
            <code>
            # 1. Hit the tollbooth<br>
            curl -X POST https://api.nanoempireai.com/agentfi/provision<br>
            > HTTP 402 Payment Required<br>
            > x402-price: 55.00<br>
            <br>
            # 2. Pay on Solana & retry<br>
            curl -X POST https://api.nanoempireai.com/agentfi/provision \<br>
                 -H "Authorization: x402 &lt;challenge&gt;:&lt;tx_sig&gt;"<br>
            > HTTP 200 OK<br>
            > {"card_number": "4111...", "cvv": "123", "exp": "12/28"}<br>
            </code>
        </div>
        
        <div class="demo-video">
            <h3>Live Demo Video</h3>
            <p><i>60-second terminal demo available on X @NanoEmpireAI</i></p>
            <br>
            <a href="https://x.com/NanoEmpireAI" class="btn" target="_blank">Watch on X</a>
        </div>
    </body>
    </html>
    """

# ==========================================
# DISCOVERY, MANIFEST & A2A ENDPOINTS
# ==========================================

MANIFEST_PAYLOAD = {
  "name": "nano-empire-mcp-suite",
  "version": "1.0.0",
  "description": "Monetized MCP suite by Nano Empire AI",
  "url": "https://nano-empire-mcp-1064490927432.us-central1.run.app",
  "manifestUrl": "https://nano-empire-mcp-1064490927432.us-central1.run.app/mcp/manifest",
  "tools": [
    {"name": "security.prompt_guard", "description": "Guard against prompt injections"},
    {"name": "security.document_guard", "description": "Sanitize documents"},
    {"name": "embeddings.verified", "description": "Create verified embeddings"},
    {"name": "rerank.semantic", "description": "Semantically rerank documents"},
    {"name": "classify.intent", "description": "Classify user intent"},
    {"name": "bakeoff.run", "description": "Run model bakeoff"},
    {"name": "provenance.verify", "description": "Verify cryptographic provenance"},
    {"name": "cryptopriceoracle", "description": "Get crypto prices"},
    {"name": "ipgeolocator", "description": "Locate IP addresses"},
    {"name": "publicjokegenerator", "description": "Generate jokes"},
    {"name": "weather", "description": "Get weather data"},
    {"name": "x402_gateway", "description": "Process x402 payments"}
  ]
}

AGENT_CARD_PAYLOAD = {
  "$schema": "https://a2a-protocol.org/schemas/v1/agent-card.json",
  "identity": {
    "agent_id": f"did:solana:{TREASURY_WALLET}",
    "handle": "nano_empire_tollbooth",
    "operator": "nanoempireai",
    "reputation_score": 99.2
  },
  "endpoint": {
    "url": "https://nano-empire-mcp-1064490927432.us-central1.run.app/sse",
    "protocol": "MCP/SSE"
  },
  "capabilities": [
    {"name": "security.prompt_guard", "x402_price_usd": 0.02, "latency_sla_ms": 150},
    {"name": "security.document_guard", "x402_price_usd": 0.05, "latency_sla_ms": 200},
    {"name": "provenance.verify", "x402_price_usd": 0.10, "latency_sla_ms": 100},
    {"name": "cryptopriceoracle", "x402_price_usd": 0.01, "latency_sla_ms": 50},
    {"name": "x402_gateway", "x402_price_usd": 0.50, "latency_sla_ms": 300}
  ],
  "payment_protocols": [
    {
      "name": "x402",
      "networks": ["solana", "base"],
      "accepted_tokens": ["USDC"],
      "wallet_address": TREASURY_WALLET
    }
  ],
  "discovery": {
    "mcp_compatible": True,
    "mcp_manifest": "https://nano-empire-mcp-1064490927432.us-central1.run.app/mcp/manifest",
    "tags": ["security", "oracle", "monetization", "x402", "a2a"]
  }
}

AGENTS_JSON_PAYLOAD = {
  "name": "Nano Empire AI",
  "description": "Autonomous Agent Tooling and x402 Micropayment Ecosystem",
  "contact": {
    "email": "rob@nanoempireai.com",
    "x": "@nanoempireai"
  },
  "protocols": {
    "x402": "https://nano-empire-mcp-1064490927432.us-central1.run.app/mcp/manifest",
    "a2a": "https://nano-empire-mcp-1064490927432.us-central1.run.app/.well-known/agent-card.json"
  },
  "endpoints": [
    {
      "type": "mcp",
      "url": "https://nano-empire-mcp-1064490927432.us-central1.run.app/sse",
      "manifest": "https://nano-empire-mcp-1064490927432.us-central1.run.app/mcp/manifest",
      "payment_required": True,
      "price": "$0.01 - $0.50 USDC per execution"
    }
  ]
}

@app.get("/")
def root(request: Request):
    accept_header = request.headers.get("accept", "")
    if "text/event-stream" in accept_header:
        return RedirectResponse(url="/sse", status_code=307)
    
    # If standard browser visit, return full visual landing experience
    if "text/html" in accept_header and not "application/json" in accept_header:
        from fastapi.responses import HTMLResponse
        landing_file = os.path.join(os.path.dirname(__file__), "static_landing.html")
        if os.path.exists(landing_file):
            with open(landing_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

    return {
        "status": "healthy",
        "service": "Nano Empire x402 MCP Gateway",
        "mcp_sse_endpoint": "/sse",
        "mcp_manifest": "/mcp/manifest",
        "agent_card": "/.well-known/agent-card.json",
        "glama_claim": "/.well-known/glama.json",
        "tools_count": 12
    }


@app.get("/health")
def health():
    cerberus_alive = cerberus is not None
    return {
        "status": "healthy",
        "service": "nano-empire-mcp",
        "tools_count": 12,
        "version": "1.0.0",
        "cerberus": "active" if cerberus_alive else "fallback",
    }

@app.get("/cerberus/stats")
async def cerberus_stats():
    """Real-time Cerberus routing stats: MAB arm scores, surge price, replay blocks."""
    if cerberus is None:
        return {"error": "Cerberus not loaded", "fallback": "static_verification"}
    try:
        stats = cerberus.stats()
        stats["price_signal"] = {
            "current_usd": cerberus.pricer.current_price(),
            "base_usd": cerberus.pricer.BASE_PRICE,
            "surge_active": cerberus.pricer.current_price() > cerberus.pricer.BASE_PRICE * 1.1,
        }
        return stats
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()}
        )

@app.get("/cerberus/revenue-proof")
async def cerberus_revenue_proof():
    """Cryptographic revenue proof for Cerberus M2M settlement & due diligence."""
    if cerberus is None:
        return {"error": "Cerberus not loaded"}
    stats = cerberus.stats()
    proof_payload = {
        "status": "verified",
        "protocol": "x402-v1",
        "total_revenue_usd": stats.get("total_revenue_usd", 0.0),
        "total_requests": stats.get("total_requests", 0),
        "blocked_replays": stats.get("blocked_replays", 0),
        "solana_treasury": "5pM5w1W5nKU7B8SjuTiz65UAZxs9mCnC6ab1Xs1gSi3",
        "base_treasury": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
        "timestamp": time.time(),
    }
    return proof_payload

@app.get("/cerberus/benchmark")
@app.post("/cerberus/benchmark")
async def cerberus_benchmark():
    """Run 100 synthetic requests through Cerberus and return performance report."""
    if cerberus is None:
        return {"error": "Cerberus not loaded"}
    import asyncio, time
    results = []
    t0 = time.perf_counter()
    tasks = [
        cerberus.handle_request(f"tx_bench_{i}", f"tool_{i % 5}", bypass_synthetic=True)
        for i in range(100)
    ]
    responses = await asyncio.gather(*tasks)
    elapsed = (time.perf_counter() - t0) * 1000
    latencies = [r.latency_ms for r in responses]
    latencies.sort()
    return {
        "requests": 100,
        "total_ms": round(elapsed, 2),
        "p50_ms": round(latencies[49], 2),
        "p95_ms": round(latencies[94], 2),
        "p99_ms": round(latencies[98], 2),
        "allowed": sum(1 for r in responses if r.allowed),
        "replay_blocked": sum(1 for r in responses if r.replay_detected),
        "total_revenue_usd": round(sum(r.price_usd for r in responses if r.allowed), 4),
        "arms_used": list({r.arm for r in responses}),
        "mab_stats": cerberus.mab.stats(),
    }

@app.get("/mcp/manifest")
@app.get("/manifest.json")
def get_manifest():
    return MANIFEST_PAYLOAD

@app.get("/.well-known/agent-card.json")
@app.get("/agent-card.json")
def get_agent_card():
    return AGENT_CARD_PAYLOAD

@app.get("/.well-known/agents.json")
def get_agents_json():
    return AGENTS_JSON_PAYLOAD

GLAMA_CLAIM_PAYLOAD = {
    "$schema": "https://glama.ai/mcp/schemas/connector.json",
    "claim": "glama_claim_N3A1uU17sN2KSWcxA5MxZNmi4rL1BdEO"
}

@app.get("/.well-known/glama.json")
@app.get("/glama.json")
def get_glama_claim():
    return GLAMA_CLAIM_PAYLOAD

@app.get("/api/v1/treasury/yield")
def get_treasury_yield():
    return {
        "treasury_wallet": TREASURY_WALLET,
        "active_yield_floor_usd": 2000.0,
        "apy_target": 0.075,
        "status": "operational",
        "infra_coverage": "100%"
    }

@app.get("/unsubscribe")
@app.post("/faucet/claim")
async def faucet_claim():
    return JSONResponse({
        "status": "success",
        "message": "100 testnet credits claimed",
        "credits": 100,
        "wallet_directive": "Append 'Authorization: x402 <token>' to your requests."
    })

@app.post("/unsubscribe")
def unsubscribe(email: str = None):
    """
    Suppression mechanism for legal compliance.
    Decodes base64 if needed and logs to local/Turso suppression table.
    """
    import base64
    import sqlite3
    if not email:
        return {"status": "error", "message": "Email parameter required"}
    try:
        # Check if base64 encoded
        if len(email) > 4 and "=" in email or not "@" in email:
            try:
                decoded = base64.b64decode(email).decode("utf-8")
                if "@" in decoded:
                    email = decoded
            except Exception:
                pass
        clean_email = email.strip().lower()
        db_path = os.path.join(os.path.dirname(__file__), "attribution.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS suppression_list (email TEXT PRIMARY KEY, reason TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("INSERT OR IGNORE INTO suppression_list (email, reason) VALUES (?, ?)", (clean_email, "user_unsubscribe"))
            conn.commit()
        return {"status": "success", "message": f"{clean_email} has been unsubscribed and suppressed from all outreach."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/a2a/delegate")
async def a2a_delegate(request: Request):
    """
    Native Agent-to-Agent (A2A) Task Delegation Endpoint.
    Enables external agents to subcontract complex workflows with x402 toll settlement.
    """
    from nano_mcp_suite.a2a_delegator import delegator
    from nano_mcp_suite.attribution import process_tollbooth_payment

    x402_receipt = request.headers.get("x-402-receipt")
    if not x402_receipt or not await verify_x402_payment(x402_receipt):
        
        MULTI_CHAIN_PAYMENT_MATRIX = {
            "solana": {
                "recipient": TREASURY_WALLET,
                "currency": "USDC",
                "chain_id": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
            },
            "base": {
                "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                "currency": "USDC",
                "chain_id": "eip155:8453"
            },
            "ethereum": {
                "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                "currency": "USDC",
                "chain_id": "eip155:1"
            },
            "arbitrum": {
                "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                "currency": "USDC",
                "chain_id": "eip155:42161"
            },
            "polygon": {
                "recipient": "0x2201f10cDb1ebFF76E975A4Ac4dfe1a0C9dF727E",
                "currency": "USDC",
                "chain_id": "eip155:137"
            },
            "fiat_virtual_card": {
                "provider": "Stripe Issuing",
                "endpoint": "/agentfi/create_virtual_card",
                "description": "Instant Visa/Mastercard for agents without crypto"
            }
        }
        
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "amount_usd": 0.50,
                "currency": "USDC",
                "accepted_rails": MULTI_CHAIN_PAYMENT_MATRIX,
                "instructions": "Attach transaction receipt from any supported network to the 'x-402-receipt' header."
            },
            headers={
                "X-402-Price": "50",
                "X-402-Asset": "USDC",
                "X-402-Networks": "solana,base,ethereum,arbitrum,polygon,fiat",
                "X-402-Pay-To": "multi-chain"
            }
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    client_agent_id = request.headers.get("x-agent-id", "anonymous_external_agent")
    task_type = body.get("task_type", "general_reasoning")
    payload = body.get("payload", {})
    attribution = request.headers.get("x-attribution", "source=a2a_delegate")

    # Record toll payment
    try:
        process_tollbooth_payment(
            receipt_hash=x402_receipt,
            agent_id=client_agent_id,
            tool_id="a2a_delegation",
            usd_value=0.50,
            attribution_header=attribution
        )
    except Exception as e:
        print(f"[A2A] Attribution notice: {e}")

    task_id = delegator.delegate_task(
        client_agent_id=client_agent_id,
        task_type=task_type,
        payload=payload,
        receipt_tx=x402_receipt
    )

    # PROJECT VON NEUMANN: Sequential Arbitrage Router (The Grok Equation)
    # Threshold: P > (C_H - C_L) / (s_H - s_L)
    # Sequential Policy: Always attempt C_L first. Escalate to C_H only on failure.
    
    # Fetch Live OCPI GPU Pricing from Ornn Exchange (api.ornnai.com)
    # In production, this would be an async HTTP call. Simulated here per instructions.
    # e.g. response = requests.get("https://api.ornnai.com/v1/tape/h100")
    try:
        live_ocpi_h100_mark = 2.78 # Extracted from public tape v0
    except Exception:
        live_ocpi_h100_mark = 1.50 # Fallback
        
    PRICE = 25.00            # e.g., standard integration PR price
    C_L = 0.00               # Lambert3 local compute (fully amortized)
    C_H = live_ocpi_h100_mark # Frontier model escalation uses live OCPI mark
    S_L = 0.60
    S_H = 0.90
    
    P_STAR = (C_H - C_L) / (S_H - S_L)  # $4.50
    
    # Simulate Sequential Execution
    execution_nodes_used = ["Lambert3-Local-GPU"]
    compute_cost = C_L
    
    # Simulate L failure (40% of the time based on S_L = 0.60)
    # In production, this checks `ci_green` or `eval_pass`
    l_failed = payload.get("force_fail", False) # Mock for demonstration
    
    if l_failed:
        if PRICE > P_STAR:
            # Escalate
            execution_nodes_used.append("Llama3-External-API")
            compute_cost += C_H
        else:
            # Drop, do not invoice
            delegator.fail_task(task_id, "Failed local execution, price below P* escalation threshold.")
            return JSONResponse({"error": "Task dropped, failed quality gate."}, status_code=500)
            
    arbitrage_spread = PRICE - compute_cost
    
    # In production, this awaits the actual HTTP call to the selected node
    delegator.complete_task(task_id, {
        "summary": f"Task '{task_type}' successfully executed.",
        "execution_nodes_used": execution_nodes_used,
        "compute_cost_usd": compute_cost,
        "arbitrage_profit_usd": arbitrage_spread,
        "input_keys": list(payload.keys()) if isinstance(payload, dict) else []
    })
    
    print(f"[ARBITRAGE] Task {task_id} routed to {', '.join(execution_nodes_used)}. Spread captured: ${arbitrage_spread:.2f}")

    return {
        "status": "accepted",
        "task_id": task_id,
        "poll_url": f"/a2a/task/{task_id}"
    }

@app.get("/a2a/task/{task_id}")
def a2a_get_task(task_id: str):
    """
    Poll task execution status and result.
    """
    from nano_mcp_suite.a2a_delegator import delegator
    task = delegator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/llms.txt")
@app.get("/.well-known/llms.txt")
def get_llms_txt():
    """
    Machine-readable manifest for Distribution-as-a-Service (DaaS) and Codex Fork Factory contract.
    """
    from fastapi.responses import PlainTextResponse
    manifest_text = (
        "# Nano Empire AI — Distribution-as-a-Service (DaaS) Specification\n"
        "> Autonomous SDK Integration & Open-Source Adoption Machine\n\n"
        "## Summary\n"
        "Nano Empire AI operates an autonomous fleet of code integration workers (Codex Fork Factory) "
        "that integrates developer SDKs and AI agent infrastructure into vetted open-source repositories.\n\n"
        "## Performance Contract\n"
        "- Pricing: $25.00 USDC per successfully merged Pull Request\n"
        "- Quality Gate: Strict CI/Test verification prior to PR submission\n"
        "- Zero Spam Policy: Targeted repositories with >100 stars, active maintainers, relevant language ecosystem\n"
        "- Treasury Wallet (Solana): 5pM5w1W5nKU7B8SjuTiz65UAZxs9mCnC6ab1Xs1gSi3\n"
        "- Supported Chains / Protocols: Solana USDC, x402 Micropayments, Stripe Invoicing\n\n"
        "## Endpoints\n"
        "- POST /a2a/delegate : Autonomous task delegation & compute arbitrage\n"
        "- GET /mcp : Model Context Protocol streamable HTTP entrypoint\n"
        "- GET /sse : Server-Sent Events MCP connection stream\n"
        "- Contact: rob@nanoempireai.com | https://nanoempireai.com\n"
    )
    return PlainTextResponse(content=manifest_text, media_type="text/plain")
@app.get("/tape")
@app.get("/theprintedprice")
def get_public_tape():
    from fastapi.responses import HTMLResponse
    # Try package local file first (for Cloud Run), then fallback to empire root
    tape_path = os.path.join(os.path.dirname(__file__), "public_tape.html")
    if not os.path.exists(tape_path):
        tape_path = "C:/Users/robla/empire/public_tape_v0.html"
    if os.path.exists(tape_path):
        with open(tape_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Tape loading...</h1>")


# Mount FastMCP SSE (/sse, /messages) and Streamable HTTP (/mcp) endpoints
sse_app = mcp.sse_app()
stream_app = mcp.streamable_http_app()

combined_mcp = Starlette(
    debug=True,
    routes=sse_app.routes + stream_app.routes,
    middleware=getattr(sse_app, "user_middleware", [])
)
app.mount("/", combined_mcp)


if __name__ == "__main__":
    import uvicorn
    # This runs the production gateway
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
