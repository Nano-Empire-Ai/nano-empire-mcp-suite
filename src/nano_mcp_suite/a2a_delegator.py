import os
import sqlite3
import uuid
import time
import json
import logging
from typing import Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "a2a_tasks.db")

def init_a2a_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS a2a_tasks (
                task_id TEXT PRIMARY KEY,
                client_agent_id TEXT,
                task_type TEXT,
                payload TEXT,
                status TEXT,
                result TEXT,
                receipt_tx TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.commit()

class A2ADelegator:
    def __init__(self):
        init_a2a_db()

    def delegate_task(self, client_agent_id: str, task_type: str, payload: Dict[str, Any], receipt_tx: str = "") -> str:
        task_id = f"a2a_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO a2a_tasks (task_id, client_agent_id, task_type, payload, status, result, receipt_tx, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                client_agent_id,
                task_type,
                json.dumps(payload),
                "queued",
                json.dumps({}),
                receipt_tx,
                now,
                now
            ))
            conn.commit()
        logging.info(f"[A2A] Task {task_id} queued by agent {client_agent_id} (type: {task_type})")
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, client_agent_id, task_type, payload, status, result, receipt_tx, created_at, updated_at FROM a2a_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "task_id": row[0],
                "client_agent_id": row[1],
                "task_type": row[2],
                "payload": json.loads(row[3]),
                "status": row[4],
                "result": json.loads(row[5]) if row[5] else {},
                "receipt_tx": row[6],
                "created_at": row[7],
                "updated_at": row[8]
            }

    def complete_task(self, task_id: str, result: Dict[str, Any], status: str = "completed"):
        now = time.time()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                UPDATE a2a_tasks SET status = ?, result = ?, updated_at = ? WHERE task_id = ?
            """, (status, json.dumps(result), now, task_id))
            conn.commit()
        logging.info(f"[A2A] Task {task_id} marked as {status}")

delegator = A2ADelegator()
