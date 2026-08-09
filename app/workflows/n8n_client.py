import os

import requests


N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://karl66.app.n8n.cloud/webhook-test/ai.booking"
)


def send_context(context: dict):
    response = requests.post(
        N8N_WEBHOOK_URL,
        json=context,
        timeout=30
    )

    response.raise_for_status()

    return response.json()