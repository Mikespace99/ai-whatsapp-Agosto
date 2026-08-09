import uuid

from fastapi import FastAPI

from app.supabase_client import supabase


app = FastAPI(
    title="AI Booking Backend",
    version="0.1.0"
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/test/tenants")
def test_tenants():

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


@app.get("/test/tenant/{phone_number}")
def test_tenant(phone_number: str):

    whatsapp_response = (
        supabase
        .table("whatsapp_accounts")
        .select("id, tenant_id, phone_number, provider")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )

    if not whatsapp_response.data:
        return {
            "error": "WhatsApp account non trovato"
        }

    whatsapp_account = whatsapp_response.data[0]

    tenant_id = whatsapp_account["tenant_id"]

    tenant_response = (
        supabase
        .table("tenants")
        .select("*")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )

    if not tenant_response.data:
        return {
            "error": "Tenant non trovato",
            "tenant_id": tenant_id
        }

    return {
        "whatsapp_account": whatsapp_account,
        "tenant": tenant_response.data[0]
    }


@app.post("/test/message")
def test_message():

    # --------------------------------------------------
    # 1. MESSAGGIO WHATSAPP SIMULATO
    # --------------------------------------------------

    message = {
        "to": "+390000000000",
        "from": "+393331234567",
        "message": "Vorrei prenotare una pulizia viso",
        "message_id": "test-001",
        "received_at": "2026-08-08T12:20:00+02:00"
    }


    # --------------------------------------------------
    # 2. IDENTIFICA IL TENANT
    # --------------------------------------------------

    phone_number = message["to"]

    whatsapp_response = (
        supabase
        .table("whatsapp_accounts")
        .select("id, tenant_id, phone_number, provider")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )

    if not whatsapp_response.data:
        return {
            "error": "WhatsApp account non trovato",
            "phone_number": phone_number
        }

    whatsapp_account = whatsapp_response.data[0]

    tenant_id = whatsapp_account["tenant_id"]


    # --------------------------------------------------
    # 3. RECUPERA IL TENANT
    # --------------------------------------------------

    tenant_response = (
        supabase
        .table("tenants")
        .select("*")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )

    if not tenant_response.data:
        return {
            "error": "Tenant non trovato",
            "tenant_id": tenant_id
        }

    tenant = tenant_response.data[0]


    # --------------------------------------------------
    # 4. IDENTIFICA IL CUSTOMER
    # --------------------------------------------------

    customer_phone = message["from"]

    customer_response = (
        supabase
        .table("customers")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("phone", customer_phone)
        .limit(1)
        .execute()
    )


    # --------------------------------------------------
    # 5. CREA IL CUSTOMER SE NON ESISTE
    # --------------------------------------------------

    if customer_response.data:

        customer = customer_response.data[0]

    else:

        customer_response = (
            supabase
            .table("customers")
            .insert({
                "tenant_id": tenant_id,
                "phone": customer_phone
            })
            .execute()
        )

        customer = customer_response.data[0]


    # --------------------------------------------------
    # 6. RECUPERA LA CONVERSAZIONE ATTIVA
    # --------------------------------------------------

    conversation_response = (
        supabase
        .table("conversation_state")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("customer_id", customer["id"])
        .eq("status", "ACTIVE")
        .limit(1)
        .execute()
    )


    # --------------------------------------------------
    # 7. CREA LA CONVERSAZIONE SE NON ESISTE
    # --------------------------------------------------

    if conversation_response.data:

        conversation = conversation_response.data[0]

    else:

        conversation_id = str(uuid.uuid4())

        conversation_response = (
            supabase
            .table("conversation_state")
            .insert({
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "customer_id": customer["id"],
                "status": "ACTIVE",
                "workflow": "IDLE",
                "step": "NONE",
                "retry_count": 0
            })
            .execute()
        )

        conversation = conversation_response.data[0]


    # --------------------------------------------------
    # 8. RECUPERA IL CONVERSATION CONTEXT
    # --------------------------------------------------

    context_response = (
        supabase
        .table("conversation_context")
        .select("*")
        .eq("conversation_id", conversation["conversation_id"])
        .limit(1)
        .execute()
    )


    # --------------------------------------------------
    # 9. CREA IL CONVERSATION CONTEXT SE NON ESISTE
    # --------------------------------------------------

    if context_response.data:

        conversation_context = context_response.data[0]

    else:

        context_response = (
            supabase
            .table("conversation_context")
            .insert({
                "conversation_id": conversation["conversation_id"],
                "service_id": None,
                "service_name": None,
                "operator_id": None,
                "requested_date": None,
                "requested_time": None,
                "selected_slot": None,
                "booking_id": None,
                "language": tenant["language"],
                "customer_notes": None,
                "last_intent": None,
                "ai_summary": None
            })
            .execute()
        )

        conversation_context = context_response.data[0]


    # --------------------------------------------------
    # 10. RISULTATO
    # --------------------------------------------------

    return {
        "message": message,
        "whatsapp_account": whatsapp_account,
        "tenant": tenant,
        "customer": customer,
        "conversation": conversation,
        "conversation_context": conversation_context
    }