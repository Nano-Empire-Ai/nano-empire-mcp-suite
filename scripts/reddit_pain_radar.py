import os
import json
import httpx
import feedparser
import time

def load_env():
    env_path = r"C:\Users\robla\.env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip()

def analyze_pain_signal(title, summary, api_key):
    """Uses OpenAI API via httpx to evaluate if a post is a monetizable pain point."""
    if not api_key:
        return {"is_pain": True, "score": 75, "proposed_tool": "Unknown Tool (No LLM key)"}
    
    prompt = f"""
    Analyze this Reddit post for business/developer pain points that could be solved by a programmatic API tool (which we will sell for $0.50 per call).
    Title: {title}
    Body: {summary}
    
    Respond STRICTLY in this JSON format, nothing else:
    {{"is_pain": boolean, "score": int (0-100, 100 being highest desperation/willingness to pay), "proposed_tool_name": "string", "proposed_tool_description": "string"}}
    """
    
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            },
            timeout=10.0
        )
        if response.status_code == 200:
            return json.loads(response.json()["choices"][0]["message"]["content"])
        else:
            return None
    except Exception as e:
        print(f"[LLM Error] {e}")
        return None

def run_radar():
    print("========================================")
    print("   NANO EMPIRE REDDIT PAIN RADAR        ")
    print("========================================")
    
    load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    
    # We use RSS to bypass Reddit's strict OAuth requirements
    subreddits = ["dataengineering", "webscraping", "Automate", "SaaS"]
    
    # We will use a highly permissive keyword list, or just analyze everything.
    # To save tokens, we'll keep a broader list.
    pain_keywords = ["how do", "is there an api", "looking for", "tool for", "struggle", "hate", "automate", "tired of", "wish", "hard time", "expensive", "best way to", "help", "need a way", "can i", "extract", "download"]
    
    extracted_signals = []

    for sub in subreddits:
        print(f"\n[>] Scanning r/{sub}...")
        feed_url = f"https://www.reddit.com/r/{sub}/new/.rss"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        try:
            resp = httpx.get(feed_url, headers=headers, timeout=10.0)
            feed = feedparser.parse(resp.text)
            
            for entry in feed.entries[:10]: # Look at latest 10 posts to save LLM tokens
                title_lower = entry.title.lower()
                summary_lower = entry.summary.lower()
                
                # Check if it hits our keyword heuristics (very broad now)
                if any(k in title_lower or k in summary_lower for k in pain_keywords):
                    print(f"  [!] Potential signal: {entry.title[:50]}...")
                    
                    analysis = analyze_pain_signal(entry.title, entry.summary, api_key)
                    # Lower the threshold to 60 for early traction
                    if analysis and analysis.get("is_pain") and analysis.get("score", 0) >= 60:
                        signal = {
                            "source": f"r/{sub}",
                            "link": entry.link,
                            "title": entry.title,
                            "score": analysis.get("score"),
                            "proposed_tool": analysis.get("proposed_tool_name"),
                            "proposed_solution": analysis.get("proposed_tool_description")
                        }
                        extracted_signals.append(signal)
                        print(f"      => CONFIRMED PAIN: Score {signal['score']}")
                        print(f"      => IDEA: {signal['proposed_tool']}")
                        
        except Exception as e:
            print(f"  [X] Failed to scan r/{sub}: {e}")
            
        time.sleep(2) # Be nice to Reddit's servers
        
    # Save the signals to disk
    out_dir = "scratch"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "x_radar_signals.json")
    
    with open(out_path, "w") as f:
        json.dump(extracted_signals, f, indent=2)
        
    print("\n========================================")
    print(f"[+] Radar Complete. Found {len(extracted_signals)} high-value actionable signals.")
    print(f"[+] Signals written to {out_path}.")
    print("========================================")

if __name__ == "__main__":
    run_radar()
