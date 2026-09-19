"""
registry_submitter.py — Nano Empire Registry Auto-Submitter
Submits nano-empire-mcp to AgentOps, mcp.so, LangSmith, and generates Smithery YAML.
Run: python registry_submitter.py
"""

import json
import os
import sys
from pathlib import Path

# Fix Windows cp1252 terminal encoding crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_HTTPX = False

SERVICE_URL = "https://nano-empire-mcp-1064490927432.us-central1.run.app"
MANIFEST_URL = f"{SERVICE_URL}/mcp/manifest"
AGENT_CARD_URL = f"{SERVICE_URL}/.well-known/agent-card.json"
GLAMA_CLAIM = "glama_claim_N3A1uU17sN2KSWcxA5MxZNmi4rL1BdEO"
DESCRIPTION = (
    "Monetized MCP server suite with 12 tools: security, embeddings, rerank, "
    "crypto oracle, A2A delegation, and MEV intelligence. Pay-per-call via x402 "
    "Solana USDC micropayments ($0.01-$0.50/call). No subscription fees."
)
TAGS = ["security", "embeddings", "rerank", "oracle", "x402", "a2a", "monetization", "mcp"]


def _post(url: str, body: dict, headers: dict = None) -> tuple[int, str]:
    """Minimal HTTP POST — works with or without httpx."""
    h = {"Content-Type": "application/json", **(headers or {})}
    data = json.dumps(body).encode()
    if HAS_HTTPX:
        try:
            r = httpx.post(url, content=data, headers=h, timeout=15)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)
    else:
        req = urllib.request.Request(url, data=data, headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()
        except Exception as ex:
            return 0, str(ex)


def submit_agentops():
    print("\n[1] AgentOps Registry...")
    url = "https://api.agentops.ai/v2/mcp-registry"
    api_key = os.environ.get("AGENTOPS_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    status, resp = _post(url, {
        "name": "nano-empire-mcp",
        "url": SERVICE_URL,
        "manifest_url": MANIFEST_URL,
        "description": DESCRIPTION,
        "tags": TAGS,
        "pricing": {"model": "per_call", "min_usd": 0.01, "max_usd": 0.50},
    }, headers)
    if status in (200, 201):
        print(f"  ✅ AgentOps: SUCCESS ({status})")
    else:
        print(f"  ⚠️  AgentOps: {status} — {resp[:120]}")


def submit_mcpso():
    print("\n[2] mcp.so Registry...")
    url = "https://api.mcp.so/submit"
    status, resp = _post(url, {
        "name": "nano-empire-mcp",
        "url": SERVICE_URL,
        "manifest": MANIFEST_URL,
        "description": DESCRIPTION,
        "category": "monetization",
        "tags": TAGS,
    })
    if status in (200, 201, 202):
        print(f"  ✅ mcp.so: SUCCESS ({status})")
    else:
        print(f"  ⚠️  mcp.so: {status} — {resp[:120]} (may need manual submission at mcp.so/submit)")


def submit_langsmith():
    print("\n[3] LangSmith Hub...")
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    if not api_key:
        print("  ⏭  SKIP: LANGSMITH_API_KEY not set in environment")
        return
    url = "https://api.smith.langchain.com/api/v1/repos/"
    status, resp = _post(url, {
        "repo_handle": "nano-empire-mcp",
        "description": DESCRIPTION,
        "is_public": True,
        "tags": TAGS,
    }, {"x-api-key": api_key})
    if status in (200, 201):
        print(f"  ✅ LangSmith: SUCCESS ({status})")
    else:
        print(f"  ⚠️  LangSmith: {status} — {resp[:120]}")


def submit_glama():
    print("\n[4] Glama Verification Check...")
    if HAS_HTTPX:
        try:
            r = httpx.get(f"{SERVICE_URL}/.well-known/glama.json", timeout=10)
            if GLAMA_CLAIM in r.text:
                print(f"  ✅ Glama: claim verified at {SERVICE_URL}/.well-known/glama.json")
            else:
                print(f"  ⚠️  Glama: claim not found in response")
        except Exception as e:
            print(f"  ⚠️  Glama check failed: {e}")
    else:
        print(f"  ℹ️  Glama: verify at https://glama.ai/mcp/servers — claim: {GLAMA_CLAIM}")


def generate_smithery_yaml():
    print("\n[5] Smithery YAML (for manual upload or Hermes API)...")
    yaml_content = f"""# Smithery MCP Server Manifest — Nano Empire AI
name: nano-empire-mcp
version: "1.0.0"
description: "{DESCRIPTION}"
url: "{SERVICE_URL}"
manifest_url: "{MANIFEST_URL}"
agent_card: "{AGENT_CARD_URL}"
transport:
  - type: sse
    url: "{SERVICE_URL}/sse"
  - type: streamable_http
    url: "{SERVICE_URL}/mcp"
pricing:
  model: per_call
  currency: USDC
  network: solana
  min_usd: 0.01
  max_usd: 0.50
  payment_header: x-402-receipt
tags:
{chr(10).join(f'  - {t}' for t in TAGS)}
"""
    output_path = os.path.join(os.path.dirname(__file__), "..", "..", "smithery_manifest.yaml")
    try:
        with open(output_path, "w") as f:
            f.write(yaml_content)
        print(f"  ✅ Written to: {os.path.abspath(output_path)}")
    except Exception:
        pass
    print(yaml_content)


def submit_awesome_mcp_comment():
    print("\n[6] awesome-mcp-servers PR #14413 status...")
    if HAS_HTTPX:
        try:
            r = httpx.get(
                "https://api.github.com/repos/punkpeye/awesome-mcp-servers/pulls/14413",
                headers={"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}"},
                timeout=10,
            )
            data = r.json()
            print(f"  State: {data.get('state')} | Title: {data.get('title', '')[:60]}")
        except Exception as e:
            print(f"  Check manually: https://github.com/punkpeye/awesome-mcp-servers/pull/14413")
    else:
        print(f"  Check manually: https://github.com/punkpeye/awesome-mcp-servers/pull/14413")


if __name__ == "__main__":
    print("=" * 60)
    print("NANO EMPIRE — Registry Auto-Submitter")
    print("=" * 60)
    submit_agentops()
    submit_mcpso()
    submit_langsmith()
    submit_glama()
    generate_smithery_yaml()
    submit_awesome_mcp_comment()
    print("\n" + "=" * 60)
    print("Done. Check results above. Manual steps:")
    print("  mcp.so: https://mcp.so/submit (has $39 paywall)")
    print("  Smithery: Use Hermes API POST /api/mcp/servers with smithery_manifest.yaml")
    print("=" * 60)
