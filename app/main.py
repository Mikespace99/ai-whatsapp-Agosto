from fastapi import FastAPI

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


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


import os

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse


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


# --------------------------------------------------
# TEST TENANTS
# --------------------------------------------------

@app.get("/test/tenants")
def test_tenants():

    from app.supabase_client import supabase

    response = (
        supabase
        .table("tenants")
        .select("*")
        .limit(10)
        .execute()
    )

    return {
        "count": len(response.data),
        "tenants": response.data
    }


# --------------------------------------------------
# TEST TENANT
# --------------------------------------------------

@app.get("/test/tenant/{phone_number}")
def test_tenant(phone_number: str):

    whatsapp_account = get_whatsapp_account(
        phone_number
    )

    if not whatsapp_account:
        return {
            "error": "WhatsApp account non trovato"
        }

    tenant_id = whatsapp_account["tenant_id"]

    tenant = get_tenant(
        tenant_id
    )

    if not tenant:
        return {
            "error": "Tenant non trovato",
            "tenant_id": tenant_id
        }

    return {
        "whatsapp_account": whatsapp_account,
        "tenant": tenant
    }


# --------------------------------------------------
# TEST MESSAGE
# --------------------------------------------------

@app.post("/test/message")
def test_message():

    # --------------------------------------------------
    # 1. MESSAGGIO WHATSAPP SIMULATO
    # --------------------------------------------------

    message = {
        "to": "+390000000000",
        "from": "+393331234567",
        "message": "Va bene anche sabato mattina?",
        "message_id": "test-003",
        "received_at": "2026-08-09T12:10:00+02:00"
    }


    # --------------------------------------------------
    # 2. IDENTIFICA IL TENANT
    # --------------------------------------------------

    whatsapp_account = get_whatsapp_account(
        message["to"]
    )

    if not whatsapp_account:
        return {
            "error": "WhatsApp account non trovato",
            "phone_number": message["to"]
        }

    tenant_id = whatsapp_account["tenant_id"]


    # --------------------------------------------------
    # 3. RECUPERA IL TENANT
    # --------------------------------------------------

    tenant = get_tenant(
        tenant_id
    )

    if not tenant:
        return {
            "error": "Tenant non trovato",
            "tenant_id": tenant_id
        }


    # --------------------------------------------------
    # 4. IDENTIFICA / CREA IL CUSTOMER
    # --------------------------------------------------

    customer = get_or_create_customer(
        tenant_id,
        message["from"]
    )


    # --------------------------------------------------
    # 5. IDENTIFICA / CREA LA CONVERSAZIONE
    # --------------------------------------------------

    conversation = get_or_create_conversation(
        tenant_id,
        customer["id"]
    )


    # --------------------------------------------------
    # 6. IDENTIFICA / CREA IL CONVERSATION CONTEXT
    # --------------------------------------------------

    conversation_context = get_or_create_context(
        conversation["conversation_id"],
        tenant["language"]
    )


    # --------------------------------------------------
    # 7. SALVA IL MESSAGGIO UTENTE
    # --------------------------------------------------

    conversation_message = save_message(
        conversation["conversation_id"],
        "user",
        message["message"]
    )


    # --------------------------------------------------
    # 8. RECUPERA LA HISTORY
    # --------------------------------------------------

    history = get_conversation_history(
        conversation["conversation_id"]
    )


    # --------------------------------------------------
    # 9. RECUPERA LE TRANSITIONS
    # --------------------------------------------------

    transitions = get_conversation_transitions(
        conversation["conversation_id"]
    )


    # --------------------------------------------------
    # 10. RECUPERA I SERVIZI DEL TENANT
    # --------------------------------------------------

    services = get_active_services(
        tenant_id
    )


    # --------------------------------------------------
    # 11. COSTRUISCI IL CONTEXT INIZIALE
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
    # 12. AI - INTERPRETA IL MESSAGGIO
    # --------------------------------------------------

    intent_result = parse_intent(
        message=message["message"],
        history=history,
        conversation=conversation,
        context=context
    )


    # --------------------------------------------------
    # 13. AGGIUNGI RISULTATO AI AL CONTEXT
    # --------------------------------------------------

    context["ai"] = intent_result


    # --------------------------------------------------
    # 14. ROUTING WORKFLOW
    # --------------------------------------------------

    workflow = conversation["workflow"]
    step = conversation["step"]

    current_workflow = conversation["workflow"]

    if intent_result["intent"] == "BOOKING_REQUEST":
        workflow = "BOOKING"
        step = "START"

    elif intent_result["intent"] == "BOOKING_CHANGE":
        workflow = "BOOKING"

    elif intent_result["intent"] == "BOOKING_CANCEL":
        workflow = "CANCELLATION"
        step = "START"

    elif intent_result["intent"] == "INFORMATION_REQUEST":
        workflow = "INFO"
        step = "START"


    # --------------------------------------------------
    # 15. AGGIORNA CONVERSATION STATE + TRANSITION
    # --------------------------------------------------

    updated_conversation = update_conversation_state(
        conversation["conversation_id"],
        tenant_id=tenant_id,
        workflow=workflow,
        step=step,
        transition_type=(
            "WORKFLOW_START"
            if workflow != current_workflow
            else None
        ),
        transition_reason=(
            f"Avvio workflow {workflow}"
            if workflow != current_workflow
            else None
        )
    )

    if updated_conversation:
        conversation = updated_conversation


    # --------------------------------------------------
    # 16. TROVA IL SERVIZIO
    # --------------------------------------------------

    service = find_service_by_name(
        tenant_id,
        "Pulizia viso"
    )


    # --------------------------------------------------
    # 17. AGGIORNA IL CONVERSATION CONTEXT
    # --------------------------------------------------

    updated_conversation_context = update_conversation_context(
        conversation["conversation_id"],
        service_id=service["id"] if service else None,
        service_name=service["name"] if service else None,
        last_intent=intent_result["intent"]
    )

    if updated_conversation_context:
        conversation_context = updated_conversation_context


    # --------------------------------------------------
    # 18. RECUPERA LE TRANSITIONS AGGIORNATE
    # --------------------------------------------------

    transitions = get_conversation_transitions(
        conversation["conversation_id"]
    )


    # --------------------------------------------------
    # 19. RICOSTRUISCI IL CONTEXT UFFICIALE
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
    # 20. AGGIUNGI RISULTATO AI
    # --------------------------------------------------

    context["ai"] = intent_result


    # --------------------------------------------------
    # 21. INVIA IL CONTEXT A N8N
    # --------------------------------------------------

    n8n_response = send_context(
        context
    )

    assistant_message = n8n_response.get(
        "message"
    )

    if assistant_message:
        save_message(
            conversation["conversation_id"],
            "assistant",
            assistant_message
        )


    # --------------------------------------------------
    # 22. RISULTATO DEL TEST
    # --------------------------------------------------

    return {
        "message": message,
        "whatsapp_account": whatsapp_account,
        "tenant": tenant,
        "customer": customer,
        "conversation": conversation,
        "conversation_context": conversation_context,
        "conversation_message": conversation_message,
        "history": history,
        "transitions": transitions,
        "context": context,
        "intent_result": intent_result,
        "services": services,
        "service": service,
        "n8n_response": n8n_response
    }
