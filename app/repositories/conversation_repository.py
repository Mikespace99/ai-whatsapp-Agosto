import uuid

from app.supabase_client import supabase


def get_conversation_history(conversation_id):
    response = (
        supabase
        .table("conversation_messages")
        .select("id, role, message, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return [
        {
            "id": row["id"],
            "role": row["role"],
            "message": row["message"],
            "timestamp": row["created_at"]
        }
        for row in (response.data or [])
    ]

    return response.data or []


def get_conversation_transitions(conversation_id):
    from app.supabase_client import supabase

    response = (
        supabase
        .table("conversation_transition")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return response.data or []


def save_transition(
    conversation_id: str,
    tenant_id: str,
    transition_type: str,
    reason: str,
    from_workflow: str,
    from_step: str,
    resume_workflow: str = None,
    resume_step: str = None,
    parent_transition_id: str = None,
    status: str = "OPEN",
    metadata: dict = None
):
    response = (
        supabase
        .table("conversation_transition")
        .insert({
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "parent_transition_id": parent_transition_id,
            "type": transition_type,
            "reason": reason,
            "from_workflow": from_workflow,
            "from_step": from_step,
            "resume_workflow": resume_workflow,
            "resume_step": resume_step,
            "status": status,
            "metadata": metadata
        })
        .execute()
    )

    return response.data[0] if response.data else None


def get_or_create_conversation(tenant_id: str, customer_id: str):

    response = (
        supabase
        .table("conversation_state")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("customer_id", customer_id)
        .eq("status", "ACTIVE")
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    conversation_id = str(uuid.uuid4())

    response = (
        supabase
        .table("conversation_state")
        .insert({
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "status": "ACTIVE",
            "workflow": "IDLE",
            "step": "NONE",
            "retry_count": 0
        })
        .execute()
    )

    return response.data[0]


def get_or_create_context(conversation_id: str, language: str):

    response = (
        supabase
        .table("conversation_context")
        .select("*")
        .eq("conversation_id", conversation_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    response = (
        supabase
        .table("conversation_context")
        .insert({
            "conversation_id": conversation_id,
            "service_id": None,
            "service_name": None,
            "operator_id": None,
            "requested_date": None,
            "requested_time": None,
            "selected_slot": None,
            "booking_id": None,
            "booking_preferences": {
                "date_from": None,
                "date_to": None,
                "time_from": None,
                "time_to": None,
                "days_of_week": [],
                "flexible": True
            },
            "language": language,
            "customer_notes": None,
            "last_intent": None,
            "ai_summary": None
        })
        .execute()
    )

    return response.data[0]


def update_conversation_context(
    conversation_id: str,
    context: dict
):
    allowed_fields = {
        "service_id",
        "service_name",
        "operator_id",
        "requested_date",
        "requested_time",
        "selected_slot",
        "booking_id",
        "booking_preferences",
        "language",
        "customer_notes",
        "last_intent",
        "ai_summary"
    }

    data = {
        key: value
        for key, value in context.items()
        if key in allowed_fields
    }

    if not data:
        return None

    response = (
        supabase
        .table("conversation_context")
        .update(data)
        .eq("conversation_id", conversation_id)
        .execute()
    )

    return response.data[0] if response.data else None


def update_conversation_state(
    conversation_id: str,
    tenant_id: str,
    workflow: str = None,
    step: str = None,
    transition_type: str = None,
    transition_reason: str = None
):
    current_response = (
        supabase
        .table("conversation_state")
        .select("*")
        .eq("conversation_id", conversation_id)
        .limit(1)
        .execute()
    )

    if not current_response.data:
        return None

    current = current_response.data[0]

    state_changed = (
        current["workflow"] != workflow
        or current["step"] != step
    )

    if state_changed and transition_type:
        save_transition(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            transition_type=transition_type,
            reason=transition_reason or "",
            from_workflow=current["workflow"],
            from_step=current["step"],
            resume_workflow=workflow,
            resume_step=step
        )

    response = (
        supabase
        .table("conversation_state")
        .update({
            "workflow": workflow,
            "step": step
        })
        .eq("conversation_id", conversation_id)
        .execute()
    )

    return response.data[0] if response.data else None

def save_message(conversation_id: str, role: str, message: str):

    response = (
        supabase
        .table("conversation_messages")
        .insert({
            "conversation_id": conversation_id,
            "role": role,
            "message": message
        })
        .execute()
    )

    return response.data[0]
