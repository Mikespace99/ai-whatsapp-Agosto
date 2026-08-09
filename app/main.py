import os
from datetime import datetime, timezone

import requests

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from app.workflows.n8n_client import send_context

from app.context.context_builder import build_context
from app.ai.intent_parser import parse_intent

from app.repositories.service_repository import (
    get_active_services,
    find_service_by_name
)

from app.repositories.tenant_repository import (
    get_whatsapp_account,
    get_tenant
)

from app.repositories.customer_repository import (
    get_or_create_customer
)

from app.repositories.conversation_repository import (
    get_or_create_conversation,
    get_or_create_context,
    update_conversation_context,
    save_message,
    get_conversation_transitions,
    get_conversation_history,
    update_conversation_state
)


app = FastAPI(
    title="AI Booking Backend",
    version="0.1.0"
)


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ==================================================
# WHATSAPP WEBHOOK VERIFICATION
# ==================================================

@app.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):

    params = request.query_params

    mode = params.get("hub.mode")
    verify_token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and verify_token == expected_token:
        return PlainTextResponse(challenge)

    return PlainTextResponse(
        "Verification failed",
        status_code=403
    )


# ==================================================
# WHATSAPP MESSAGE WEBHOOK
# ==================================================

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):

    payload = await request.json()

    message = extract_whatsapp_message(payload)

    # Meta può inviare webhook che non sono messaggi
    if not message:
        return {
            "status": "ignored"
        }

    assistant_message = process_message(message)

    # Invia risposta a WhatsApp
    if assistant_message:
        send_whatsapp_message(
            to=message["from"],
            message=assistant_message
        )

    return {
        "status": "ok"
    }


# ==================================================
# ESTRAE IL MESSAGGIO DAL PAYLOAD META
# ==================================================

def extract_whatsapp_message(payload):

    try:

        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")

        if not messages:
            return None

        whatsapp_message = messages[0]

        # Per ora gestiamo solo messaggi testuali
        if whatsapp_message.get("type") != "text":
            return None

        metadata = value.get("metadata", {})

        business_phone = metadata.get(
            "display_phone_number"
        )

        user_phone = whatsapp_message.get(
            "from"
        )

        text = whatsapp_message["text"]["body"]

        timestamp = whatsapp_message.get(
            "timestamp"
        )

        if timestamp:
            received_at = datetime.fromtimestamp(
                int(timestamp),
                tz=timezone.utc
            ).isoformat()
        else:
            received_at = datetime.now(
                timezone.utc
            ).isoformat()

        return {
            "to": business_phone,
            "from": user_phone,
            "message": text,
            "message_id": whatsapp_message.get("id"),
            "received_at": received_at
        }

    except (KeyError, IndexError, TypeError):

        return None


# ==================================================
# PIPELINE PRINCIPALE
# ==================================================

def process_message(message):

    # --------------------------------------------------
    # 1. IDENTIFICA ACCOUNT WHATSAPP
    # --------------------------------------------------

    whatsapp_account = get_whatsapp_account(
        message["to"]
    )

    if not whatsapp_account:
        print(
            "WhatsApp account non trovato:",
            message["to"]
        )
        return None

    tenant_id = whatsapp_account["tenant_id"]


    # --------------------------------------------------
    # 2. RECUPERA TENANT
    # --------------------------------------------------

    tenant = get_tenant(
        tenant_id
    )

    if not tenant:
        print(
            "Tenant non trovato:",
            tenant_id
        )
        return None


    # --------------------------------------------------
    # 3. CUSTOMER
    # --------------------------------------------------

    customer = get_or_create_customer(
        tenant_id,
        message["from"]
    )


    # --------------------------------------------------
    # 4. CONVERSATION
    # --------------------------------------------------

    conversation = get_or_create_conversation(
        tenant_id,
        customer["id"]
    )


    # --------------------------------------------------
    # 5. CONVERSATION CONTEXT
    # --------------------------------------------------

    conversation_context = get_or_create_context(
        conversation["conversation_id"],
        tenant["language"]
    )


    # --------------------------------------------------
    # 6. SALVA MESSAGGIO USER
    # --------------------------------------------------

    save_message(
        conversation["conversation_id"],
        "user",
        message["message"]
    )


    # --------------------------------------------------
    # 7. HISTORY
    # --------------------------------------------------

    history = get_conversation_history(
        conversation["conversation_id"]
    )


    # --------------------------------------------------
    # 8. TRANSITIONS
    # --------------------------------------------------

    transitions = get_conversation_transitions(
        conversation["conversation_id"]
    )


    # --------------------------------------------------
    # 9. SERVIZI
    # --------------------------------------------------

    services = get_active_services(
        tenant_id
    )


    # --------------------------------------------------
    # 10. COSTRUISCI CONTEXT
    # --------------------------------------------------

    context = build_context(
        tenant=tenant,
        customer=customer,
        message=message,
        conversation=conversation,
        conversation_context=conversation_context,
        history=history,
        transitions=transitions,
        services=services,
        whatsapp_account=whatsapp_account
    )


    # --------------------------------------------------
    # 11. AI
    # --------------------------------------------------

    intent_result = parse_intent(
        message=message["message"],
        history=history,
        conversation=conversation,
        context=context
    )

    context["ai"] = intent_result


    # --------------------------------------------------
    # 12. ROUTING
    # --------------------------------------------------

    workflow = conversation["workflow"]
    step = conversation["step"]

    current_workflow = conversation["workflow"]

    intent = intent_result["intent"]

    if intent == "BOOKING_REQUEST":
        workflow = "BOOKING"
        step = "START"

    elif intent == "BOOKING_CHANGE":
        workflow = "BOOKING"

    elif intent == "BOOKING_CANCEL":
        workflow = "CANCELLATION"
        step = "START"

    elif intent == "INFORMATION_REQUEST":
        workflow = "INFO"
        step = "START"


    # --------------------------------------------------
    # 13. AGGIORNA STATE + TRANSITION
    # --------------------------------------------------

    workflow_changed = (
        workflow != current_workflow
    )

    updated_conversation = update_conversation_state(
        conversation["conversation_id"],
        tenant_id=tenant_id,
        workflow=workflow,
        step=step,
        transition_type=(
            "WORKFLOW_START"
            if workflow_changed
            else None
        ),
        transition_reason=(
            f"Avvio workflow {workflow}"
            if workflow_changed
            else None
        )
    )

    if updated_conversation:
        conversation = updated_conversation


    # --------------------------------------------------
    # 14. SERVIZIO DETERMINATO DALL'AI
    # --------------------------------------------------

    service = None

    entities = intent_result.get(
        "entities",
        {}
    )

    service_name = entities.get(
        "service_name"
    )

    if service_name:

        service = find_service_by_name(
            tenant_id,
            service_name
        )


    # --------------------------------------------------
    # 15. AGGIORNA CONVERSATION CONTEXT
    # --------------------------------------------------

    updated_conversation_context = update_conversation_context(
        conversation["conversation_id"],
        service_id=(
            service["id"]
            if service
            else conversation_context.get("service_id")
        ),
        service_name=(
            service["name"]
            if service
            else conversation_context.get("service_name")
        ),
        last_intent=intent
    )

    if updated_conversation_context:
        conversation_context = (
            updated_conversation_context
        )


    # --------------------------------------------------
    # 16. TRANSITIONS AGGIORNATE
    # --------------------------------------------------

    transitions = get_conversation_transitions(
        conversation["conversation_id"]
    )


    # --------------------------------------------------
    # 17. CONTEXT UFFICIALE AGGIORNATO
    # --------------------------------------------------

    context = build_context(
        tenant=tenant,
        customer=customer,
        message=message,
        conversation=conversation,
        conversation_context=conversation_context,
        history=history,
        transitions=transitions,
        services=services,
        whatsapp_account=whatsapp_account
    )

    context["ai"] = intent_result


    # --------------------------------------------------
    # 18. N8N
    # --------------------------------------------------

    n8n_response = send_context(
        context
    )

    assistant_message = (
        n8n_response.get("message")
        if n8n_response
        else None
    )


    # --------------------------------------------------
    # 19. SALVA RISPOSTA ASSISTANT
    # --------------------------------------------------

    if assistant_message:

        save_message(
            conversation["conversation_id"],
            "assistant",
            assistant_message
        )


    # --------------------------------------------------
    # 20. RETURN
    # --------------------------------------------------

    return assistant_message


# ==================================================
# INVIO MESSAGGIO WHATSAPP
# ==================================================

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

    if not phone_number_id or not access_token:
        print(
            "WhatsApp credentials mancanti"
        )
        return None

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

    print(
        "=== WHATSAPP SEND ==="
    )
    print(
        response.status_code
    )
    print(
        response.text
    )

    response.raise_for_status()

    return response.json()
