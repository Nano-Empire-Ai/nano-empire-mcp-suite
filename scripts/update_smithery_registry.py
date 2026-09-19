import json
import os

REGISTRY_PATH = "artifacts/registry/registry_smithery.json"
CLOUD_RUN_URL = "https://nano-empire-mcp-1064490927432.us-central1.run.app"

def main():
    if not os.path.exists("artifacts/registry"):
        os.makedirs("artifacts/registry")
        
    registry = {
        "name": "nano-empire-mcp-suite",
        "version": "1.0.0",
        "description": "Monetized MCP suite by Nano Empire",
        "url": CLOUD_RUN_URL,
        "manifestUrl": f"{CLOUD_RUN_URL}/mcp/manifest",
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
    
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
        
    print(f"Updated {REGISTRY_PATH}")
    print(f"Total tools: {len(registry['tools'])}")
    print(f"Cloud Run URL: {CLOUD_RUN_URL}")
    print(f"Manifest URL: {registry['manifestUrl']}")

if __name__ == '__main__':
    main()
