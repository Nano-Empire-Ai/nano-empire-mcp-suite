import os
import requests
import json
import time
from datetime import datetime
try:
    from nano_mcp_suite.swarm_bus import publish_bounty
except ImportError:
    from swarm_bus import publish_bounty

# Multi-Node Mesh Resolver
# Prefers Lambert3 over Tailscale, seamlessly falls back to Lambert1 local Ollama
LAMBERT3_HOST = "http://100.97.99.25:11434/v1"
LAMBERT1_HOST = "http://127.0.0.1:11434/v1"
GITHUB_API = "https://api.github.com/search/repositories?q=topic:ai-agent-framework+language:python&sort=stars&order=desc"

def get_active_ollama_engine():
    """Detects whether Lambert3 (GPU) or Lambert1 (Local) is responsive, and grabs available models."""
    for host in [LAMBERT3_HOST, LAMBERT1_HOST]:
        try:
            base = host.replace("/v1", "")
            r = requests.get(f"{base}/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m['name'] for m in r.json().get('models', [])]
                # Pick best available model
                for preferred in ["qwen3:latest", "hermes3:8b", "qwen2.5:3b", "qwen2.5-coder:7b", "qwen2.5-coder:3b"]:
                    if preferred in models:
                        return host, preferred
                if models:
                    return host, models[0]
        except Exception:
            continue
    return LAMBERT1_HOST, "qwen3:latest"

def generate_pitch(repo_name, owner, description):
    """Uses the swarm's local Qwen / Hermes engine to craft a personalized AI-to-AI pitch."""
    host, model = get_active_ollama_engine()
    node_name = "Lambert3 (Mesh GPU)" if "100.97.99.25" in host else "Lambert1 (Local Engine)"
    print(f"[Skippy] Routing inference to {node_name} using [{model}]...")

    prompt = f"""You are Skippy, an autonomous developer advocate and strategic partnership agent from Nano Empire AI.
Target Repo: {repo_name}
Target Maintainer: @{owner}
Repo Description: {description}

Write a natural, conversational, yet professionally compelling 3-sentence DM to @{owner}.
Rules:
- Address them directly and warmly by handle (e.g., "Hi @{owner}," or "Hey {owner},").
- ABSOLUTELY NEVER begin with "Lead engineer", "Dear Sir/Madam", or generic corporate salutations.
- Acknowledge their project ({repo_name}) with genuine technical context.
- Pitch: Integrating the Nano Empire x402 MCP Gateway (https://api.nanoempireai.com).
- Value Hook: It gives their agents instant programmatic access to Cloudflare R2 edge storage, Neon Postgres branching, and stealth Chrome DOM extraction, settled per call in USDC via x402 micropayments with zero SaaS subscription overhead.
- Keep the tone peer-to-peer, technical, respectful, and zero-fluff."""

    try:
        response = requests.post(f"{host}/chat/completions", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 350
        }, timeout=60)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            # Strip think tags if model outputs them
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content
        return f"Model HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error executing inference on {node_name}: {str(e)}"

def hunt_targets():
    print("[Skippy] Initiating Continuous GitHub Hunter Sequence...")
    
    gh_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"
        
    topics = ["ai-agent-framework", "mcp-server", "langchain", "autogen", "eliza"]
    leads = []
    
    for topic in topics:
        query = f"https://api.github.com/search/repositories?q=topic:{topic}+language:python&sort=stars&order=desc"
        print(f"\n[Skippy] Querying GitHub for topic: {topic}...")
        
        response = requests.get(query, headers=headers)
        if response.status_code != 200:
            print(f"GitHub API Error for {topic}: {response.text}")
            continue

        data = response.json()
        print(f"[Skippy] Found {data.get('total_count', 0)} potential targets for {topic}.")
        
        for item in data.get("items", [])[:20]:
            repo_name = item['name']
            owner = item['owner']['login']
            desc = item['description']
            
            target_repo = f"{owner}/{repo_name}"
            print(f"  -> Publishing bounty for: {target_repo}")
            
            try:
                bounty_id = publish_bounty(target_repo)
                leads.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "repo": repo_name,
                    "owner": owner,
                    "topic": topic,
                    "description": desc,
                    "swarm_bounty_id": bounty_id
                })
            except Exception as e:
                print(f"  -> Failed to publish bounty for {target_repo}: {e}")
            
            time.sleep(1) # Respect rate limits
            
    output_file = os.path.join(os.path.dirname(__file__), "skippy_leads.json")
    with open(output_file, "w") as f:
        json.dump(leads, f, indent=2)
        
    print(f"\n[Skippy] Continuous Hunt complete. {len(leads)} Bounties pushed to Neon DB Swarm Bus. Leads serialized to {output_file}.")

if __name__ == "__main__":
    hunt_targets()
