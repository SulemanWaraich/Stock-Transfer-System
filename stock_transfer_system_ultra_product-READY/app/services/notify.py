import requests
from app.core.config import settings
def notify_slack(text: str):
    if not settings.SLACK_WEBHOOK_URL: return False
    try:
        requests.post(settings.SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
        return True
    except Exception:
        return False
