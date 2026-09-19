import os
import time
import psycopg

NEON_URI = "postgresql://neondb_owner:npg_wsMhrBn8UF6y@ep-restless-grass-akvdgzme-pooler.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require"

def publish_bounty(target_repo: str):
    """Lambert1: Push a target repo to the queue."""
    with psycopg.connect(NEON_URI) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bounties (target_repo, status) VALUES (%s, 'pending') RETURNING id;",
                (target_repo,)
            )
            bounty_id = cur.fetchone()[0]
            conn.commit()
            print(f"[SwarmBus] Published bounty #{bounty_id} for target: {target_repo}")
            return bounty_id

def poll_bounty():
    """Lambert3: Poll the queue for a pending bounty, lock it, and return it."""
    with psycopg.connect(NEON_URI) as conn:
        with conn.cursor() as cur:
            # Atomic check-and-set
            cur.execute("""
                UPDATE bounties 
                SET status = 'processing' 
                WHERE id = (
                    SELECT id FROM bounties 
                    WHERE status = 'pending' 
                    ORDER BY created_at ASC 
                    LIMIT 1 
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, target_repo;
            """)
            row = cur.fetchone()
            conn.commit()
            if row:
                print(f"[SwarmBus] Claimed bounty #{row[0]} ({row[1]})")
                return {"id": row[0], "target_repo": row[1]}
            return None

def complete_bounty(bounty_id: int, pitch: str):
    """Lambert3: Mark bounty as complete and attach the pitch."""
    with psycopg.connect(NEON_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE bounties 
                SET status = 'completed', pitch = %s, processed_at = CURRENT_TIMESTAMP 
                WHERE id = %s;
            """, (pitch, bounty_id))
            conn.commit()
            print(f"[SwarmBus] Completed bounty #{bounty_id}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        b_id = publish_bounty("nanoempire/demo")
        b = poll_bounty()
        if b:
            complete_bounty(b["id"], "This is an amazing test pitch.")
