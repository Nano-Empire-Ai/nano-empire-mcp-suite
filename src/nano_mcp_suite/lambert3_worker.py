import time
import requests
try:
    from nano_mcp_suite.swarm_bus import poll_bounty, complete_bounty
except ImportError:
    from swarm_bus import poll_bounty, complete_bounty
import os

LAMBERT3_HOST = "http://127.0.0.1:11434/v1"

def generate_pitch(target_repo, owner, description):
    """Lambert3: Generate pitch using local Ollama (runs directly on Lambert3)."""
    prompt = f"""You are Skippy, an autonomous developer advocate and strategic partnership agent from Nano Empire AI.
Target Repo: {target_repo}
Target Maintainer: @{owner}
Repo Description: {description}

Write a natural, conversational, yet professionally compelling 3-sentence DM to @{owner}.
Rules:
- Address them directly and warmly by handle (e.g., "Hi @{owner}," or "Hey {owner},").
- ABSOLUTELY NEVER begin with "Lead engineer", "Dear Sir/Madam", or generic corporate salutations.
- Acknowledge their project ({target_repo}) with genuine technical context.
- Pitch: Integrating the Nano Empire x402 MCP Gateway (https://api.nanoempireai.com).
- Value Hook: It gives their agents instant programmatic access to Cloudflare R2 edge storage, Neon Postgres branching, and stealth Chrome DOM extraction, settled per call in USDC via x402 micropayments with zero SaaS subscription overhead.
- Keep the tone peer-to-peer, technical, respectful, and zero-fluff."""

    try:
        response = requests.post(f"{LAMBERT3_HOST}/chat/completions", json={
            "model": "qwen2.5-coder:3b",  # Lambert3's fast model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 350
        }, timeout=60)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content
        return f"Model HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error executing inference on Lambert3: {str(e)}"

def send_agentmail(to_email, subject, body):
    """
    Hook up AgentMail (ClawHub skill) to send the email.
    Assuming AgentMail exposes an API or CLI locally.
    For now, we mock the dispatch until the agentmail CLI is fully configured.
    """
    print(f"[AgentMail] Dispatching to {to_email}...")
    print(f"[AgentMail] Subject: {subject}")
    print(f"[AgentMail] Body:\n{body}")
    # In reality, this would use `agentmail send ...` or similar.
    return True

def run_worker():
    print("[Lambert3 Worker] Booting up and polling Swarm Bus...")
    while True:
        bounty = poll_bounty()
        if bounty:
            repo_path = bounty["target_repo"]
            print(f"[Lambert3 Worker] Processing bounty: {repo_path}")
            
            # For simplicity, extract owner and repo from target_repo ("owner/repo")
            parts = repo_path.split("/")
            owner = parts[0] if len(parts) > 0 else "maintainer"
            
            # Fetch repo description from GitHub to get context
            desc = "An awesome AI agent framework."
            try:
                r = requests.get(f"https://api.github.com/repos/{repo_path}")
                if r.status_code == 200:
                    desc = r.json().get("description", desc)
            except:
                pass

            pitch = generate_pitch(repo_path, owner, desc)
            print(f"[Lambert3 Worker] Generated Pitch:\n{pitch}")
            
            # Complete bounty on the bus
            complete_bounty(bounty["id"], pitch)
            
            # Fire AgentMail
            send_agentmail(f"{owner}@users.noreply.github.com", f"Integrating {repo_path} with x402 Gateway", pitch)
            
        else:
            time.sleep(5)

if __name__ == "__main__":
    run_worker()
