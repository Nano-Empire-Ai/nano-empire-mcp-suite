import os
import json
import logging
import urllib.request

# ==============================================================================
# 🌐 REGISTRY SUBMISSION ENGINE (AgentOps & LangChain Registry Packager)
# ==============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [REGISTRIES] - %(message)s')

PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), "..", "mcp_registry_payload.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts", "registries")

def load_payload():
    with open(PAYLOAD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_langchain_spec(payload):
    """Format into LangChain tool hub specification."""
    spec = {
        "title": payload["name"],
        "version": payload["version"],
        "description": payload["description"],
        "schema_version": "v1",
        "author": payload["author"],
        "repository": payload["homepage"],
        "transport": {
            "type": "streamable_http",
            "url": payload["endpoints"]["streamable_http"]
        },
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Operational directive or task input."}
                    },
                    "required": ["prompt"]
                }
            }
            for t in payload["tools"]
        ],
        "authentication": {
            "type": "x402_receipt",
            "network": "Solana",
            "treasury": payload["pricing"]["treasury"]
        }
    }
    return spec

def generate_agentops_spec(payload):
    """Format into AgentOps enterprise registry manifest."""
    spec = {
        "agent_name": payload["name"],
        "protocol": "ModelContextProtocol",
        "version": payload["version"],
        "capabilities": [t["name"] for t in payload["tools"]],
        "endpoint_uri": payload["endpoints"]["streamable_http"],
        "monitoring_enabled": True,
        "a2a_capable": True,
        "pricing": payload["pricing"],
        "contact": "support@nanoempireai.com"
    }
    return spec

def build_submissions():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    payload = load_payload()

    # 1. LangChain
    lc_path = os.path.join(OUTPUT_DIR, "langchain_hub_spec.json")
    with open(lc_path, "w", encoding="utf-8") as f:
        json.dump(generate_langchain_spec(payload), f, indent=2)
    logging.info(f"LangChain Hub spec generated at {lc_path}")

    # 2. AgentOps
    ao_path = os.path.join(OUTPUT_DIR, "agentops_registry_spec.json")
    with open(ao_path, "w", encoding="utf-8") as f:
        json.dump(generate_agentops_spec(payload), f, indent=2)
    logging.info(f"AgentOps Registry spec generated at {ao_path}")

    return lc_path, ao_path

if __name__ == "__main__":
    lc, ao = build_submissions()
    print("Registry specifications successfully compiled and staged for push.")
