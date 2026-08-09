def build_context(
    tenant,
    customer,
    message,
    conversation,
    conversation_context,
    history=None,
    transitions=None,
    services=None,
    operators=None,
    faq=None,
    settings=None,
    whatsapp_account=None,
    calendar=None
):
    """
    Costruisce il Context ufficiale da passare ai workflow n8n.
    Il Backend è l'unica fonte responsabile della costruzione del Context.
    """

    history = history or []
    transitions = transitions or []
    services = services or []
    operators = operators or []
    faq = faq or []
    settings = settings or {}
    calendar = calendar or {}

    received_at = (
        message.get("received_at")
        or message.get("created_at")
    )

    message_id = (
        message.get("message_id")
        or message.get("id")
    )

    context = {

        # ---------------------------------------------------------
        # TENANT
        # ---------------------------------------------------------
        "tenant": {
            "id": tenant.get("id"),
            "business_name": tenant.get("business_name"),
            "assistant_name": tenant.get("assistant_name"),

            "phone_number": (
                whatsapp_account.get("phone_number")
                if whatsapp_account
                else None
            ),

            "timezone": tenant.get("timezone"),
            "language": tenant.get("language")
        },

        # ---------------------------------------------------------
        # CUSTOMER
        # ---------------------------------------------------------
        "customer": {
            "id": customer.get("id"),
            "phone": customer.get("phone"),
            "name": customer.get("name")
        },

        # ---------------------------------------------------------
        # REQUEST
        # ---------------------------------------------------------
        "request": {
            "channel": "whatsapp",
            "message": message.get("message"),
            "received_at": received_at,
            "message_id": message_id
        },

        # ---------------------------------------------------------
        # CONVERSATION
        # ---------------------------------------------------------
        "conversation": {

            "state": {
                "status": conversation.get("status"),
                "workflow": conversation.get("workflow"),
                "step": conversation.get("step"),
                "retry_count": conversation.get("retry_count", 0),
                "waiting_since": conversation.get("waiting_since"),
                "timeout_at": conversation.get("timeout_at"),
                "last_message_at": conversation.get("last_message_at"),
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at")
            },

            "context": {
                "service_id": conversation_context.get("service_id"),
                "service_name": conversation_context.get("service_name"),
                "operator_id": conversation_context.get("operator_id"),
                "selected_slot": conversation_context.get("selected_slot"),
                "booking_id": conversation_context.get("booking_id"),
                "language": conversation_context.get("language"),
                "customer_notes": conversation_context.get("customer_notes"),
                "last_intent": conversation_context.get("last_intent"),
                "ai_summary": conversation_context.get("ai_summary"),
                "booking_preferences": conversation_context.get(
                    "booking_preferences"
                )
            },

            "history": history,

            # Storico delle deviazioni / transizioni
            "transitions": transitions
        },

        # ---------------------------------------------------------
        # KNOWLEDGE
        # ---------------------------------------------------------
        "knowledge": {
            "services": services,
            "operators": operators,
            "faq": faq,
            "settings": settings
        },

        # ---------------------------------------------------------
        # BOOKING
        # ---------------------------------------------------------
        "booking": {
            "intent": None,
            "service": None,
            "preferences": {},
            "candidate_slots": [],
            "selected_slot": None,
            "booking_result": None
        },

        # ---------------------------------------------------------
        # AI
        # ---------------------------------------------------------
        "ai": {
            "intent": None,
            "entities": {},
            "confidence": None,
            "notes": None
        },

        # ---------------------------------------------------------
        # INTEGRATIONS
        # ---------------------------------------------------------
        "integrations": {
            "calendar": calendar,
            "whatsapp": {
                "phone_number": (
                    whatsapp_account.get("phone_number")
                    if whatsapp_account
                    else None
                ),
                "provider": (
                    whatsapp_account.get("provider")
                    if whatsapp_account
                    else None
                )
            }
        },

        # ---------------------------------------------------------
        # RUNTIME
        # ---------------------------------------------------------
        "runtime": {
            "request_received_at": received_at,
            "workflow_started_at": None,
            "current_timestamp": None,
            "timezone": tenant.get("timezone")
        },

        # ---------------------------------------------------------
        # METADATA
        # ---------------------------------------------------------
        "metadata": {
            "conversation_id": conversation.get("conversation_id"),
            "last_workflow": None,
            "last_node": None,
            "version": "1.1",
            "processed_at": None
        }
    }

    return context