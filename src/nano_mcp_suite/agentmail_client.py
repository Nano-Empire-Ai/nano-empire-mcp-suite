import os
import json
import uuid
from datetime import datetime

class AgentMailClient:
    def __init__(self, outbox_dir="agentmail_outbox"):
        self.outbox_dir = os.path.join(os.path.dirname(__file__), outbox_dir)
        os.makedirs(self.outbox_dir, exist_ok=True)
    
    def send(self, to_email: str, subject: str, body: str, metadata: dict = None):
        """
        Spooled dispatch to AgentMail. In an ExO system, this is picked up
        by the AgentMail clawhub tool or a local MTA daemon for actual delivery.
        """
        message_id = str(uuid.uuid4())
        payload = {
            "message_id": message_id,
            "to": to_email,
            "subject": subject,
            "body": body,
            "metadata": metadata or {},
            "queued_at": datetime.utcnow().isoformat()
        }
        
        filepath = os.path.join(self.outbox_dir, f"{message_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            
        print(f"[AgentMail] Queued message to {to_email} (ID: {message_id})")
        return message_id
