
import os
import httpx
import logging

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
PAGERDUTY_ROUTING_KEY = os.getenv("PAGERDUTY_ROUTING_KEY", "")

async def send_alert(title: str, message: str, severity: str = "info"):
    if not SLACK_WEBHOOK_URL and not PAGERDUTY_ROUTING_KEY:
        logging.warning(f"Alert [{severity}] {title}: {message}")
        return

    try:
        async with httpx.AsyncClient() as client:
            if SLACK_WEBHOOK_URL:
                color = "#ff0000" if severity == "critical" else "#ffcc00" if severity == "warning" else "#36a64f"
                await client.post(SLACK_WEBHOOK_URL, json={
                    "attachments": [{
                        "color": color,
                        "title": f"[{severity.upper()}] {title}",
                        "text": message
                    }]
                })
    except Exception as e:
        logging.error(f"Failed to send alert: {e}")
