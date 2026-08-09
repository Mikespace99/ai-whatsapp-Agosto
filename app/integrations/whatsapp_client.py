import os
import requests


def send_whatsapp_message(
    to: str,
    message: str
):
    phone_number_id = os.getenv(
        "WHATSAPP_PHONE_NUMBER_ID"
    )

    access_token = os.getenv(
        "WHATSAPP_ACCESS_TOKEN"
    )

    if not phone_number_id:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID non configurato"
        )

    if not access_token:
        raise RuntimeError(
            "WHATSAPP_ACCESS_TOKEN non configurato"
        )

    url = (
        f"https://graph.facebook.com/v23.0/"
        f"{phone_number_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
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
        timeout=20
    )

    print("=== WHATSAPP SEND ===")
    print(response.status_code)
    print(response.text)

    response.raise_for_status()

    return response.json()
