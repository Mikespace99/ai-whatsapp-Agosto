from app.supabase_client import supabase


def get_or_create_customer(tenant_id: str, phone: str):

    response = (
        supabase
        .table("customers")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    response = (
        supabase
        .table("customers")
        .insert({
            "tenant_id": tenant_id,
            "phone": phone
        })
        .execute()
    )

    return response.data[0]