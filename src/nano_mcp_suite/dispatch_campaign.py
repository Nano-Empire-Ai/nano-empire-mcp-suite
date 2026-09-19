import os
import time
import argparse
import psycopg
from github import Github, GithubException
try:
    from agentmail_client import AgentMailClient
except ImportError:
    from nano_mcp_suite.agentmail_client import AgentMailClient

NEON_URI = "postgresql://neondb_owner:npg_wsMhrBn8UF6y@ep-restless-grass-akvdgzme-pooler.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require"

def fetch_ready_bounties():
    with psycopg.connect(NEON_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, target_repo, pitch 
                FROM bounties 
                WHERE status = 'completed' AND pitch IS NOT NULL
                ORDER BY processed_at ASC;
            """)
            return cur.fetchall()

def mark_dispatched(bounty_id, dry_run=True):
    if dry_run:
        return
    with psycopg.connect(NEON_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE bounties SET status = 'dispatched' WHERE id = %s", (bounty_id,))
            conn.commit()

def run_dispatch(dry_run=True, channel="all"):
    print(f"============================================================")
    print(f"     SWARM DISPATCHER (DRY_RUN={dry_run})")
    print(f"============================================================")
    
    gh_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    gh = Github(gh_token) if gh_token else Github()
    mail_client = AgentMailClient()
    
    bounties = fetch_ready_bounties()
    print(f"[Dispatcher] Found {len(bounties)} completed pitches ready for dispatch.")
    
    for bounty_id, target_repo, pitch in bounties:
        print(f"\n[Dispatching] Bounty #{bounty_id} -> {target_repo}")
        
        # 1. GitHub Issue Dispatch
        if channel in ["all", "github"]:
            try:
                issue_title = f"Integration with Nano Empire x402 Gateway"
                issue_body = f"{pitch}\n\n---\n*This is an autonomous integration proposal from the Nano Empire Swarm.*"
                
                if not dry_run:
                    # Caution: We wrap in try/except so it doesn't crash on bad repos
                    if gh_token:
                        repo = gh.get_repo(target_repo)
                        repo.create_issue(title=issue_title, body=issue_body)
                        print(f"  [GitHub] Successfully opened issue on {target_repo}")
                    else:
                        print("  [GitHub] No token found, skipping live dispatch.")
                else:
                    print(f"  [GitHub] (DRY RUN) Would create issue on {target_repo}")
                    
            except Exception as e:
                print(f"  [GitHub Error] Could not post to {target_repo}: {str(e)}")
            
        # 2. AgentMail Dispatch
        if channel in ["all", "agentmail"]:
            parts = target_repo.split("/")
            owner = parts[0]
            target_email = f"{owner}@users.noreply.github.com"
            
            if not dry_run:
                mail_client.send(target_email, f"Integration with {target_repo}", pitch, metadata={"bounty_id": bounty_id, "repo": target_repo})
                print(f"  [AgentMail] Sent payload to spooler for {target_email}")
            else:
                print(f"  [AgentMail] (DRY RUN) Would spool email to {target_email}")
            
        mark_dispatched(bounty_id, dry_run=dry_run)
        time.sleep(1) # Prevent GitHub API rate limits
        
    print("\n[Dispatcher] Run complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch completed pitches to targets.")
    parser.add_argument("--live", action="store_true", help="Actually dispatch (no dry run)")
    parser.add_argument("--channel", choices=["all", "github", "agentmail"], default="all", help="Which channel to dispatch on")
    args = parser.parse_args()
    
    run_dispatch(dry_run=not args.live, channel=args.channel)
