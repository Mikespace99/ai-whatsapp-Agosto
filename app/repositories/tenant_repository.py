from app.supabase_client import supabase


def get_whatsapp_account(phone_number: str):

    response = (
        supabase
        .table("whatsapp_accounts")
        .select("id, tenant_id, phone_number, provider")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_tenant(tenant_id: str):

    response = (
        supabase
        .table("tenants")
        .select("*")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]