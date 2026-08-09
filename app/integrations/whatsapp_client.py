import os

import requests


def send_whatsapp_message(
    to: str,
    message: str
):
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    api_version = os.getenv(
        "WHATSAPP_API_VERSION",
        "v23.0"
    )

    if not access_token:
        raise RuntimeError(
            "WHATSAPP_ACCESS_TOKEN non configurato"
        )

    if not phone_number_id:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID non configurato"
        )

    url = (
        f"https://graph.facebook.com/"
        f"{api_version}/"
        f"{phone_number_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()
