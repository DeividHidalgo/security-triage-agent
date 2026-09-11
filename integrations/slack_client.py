"""
Cliente Slack via Incoming Webhook (o jeito mais simples de notificar um
canal sem precisar criar um app Slack completo).

Docs: https://api.slack.com/messaging/webhooks
"""
from __future__ import annotations
import os
import requests


def send_message(text: str, blocks: list[dict] | None = None, webhook_url: str | None = None) -> None:
    url = webhook_url or os.environ["SLACK_WEBHOOK_URL"]
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
