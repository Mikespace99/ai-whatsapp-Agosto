from app.supabase_client import supabase


def get_active_services(tenant_id: str):
    response = (
        supabase
        .table("services")
        .select("id, name, duration_minutes, price, active")
        .eq("tenant_id", tenant_id)
        .eq("active", True)
        .execute()
    )

    return response.data


def find_service_by_name(tenant_id: str, service_name: str):
    response = (
        supabase
        .table("services")
        .select("id, name, duration_minutes, price, active")
        .eq("tenant_id", tenant_id)
        .eq("active", True)
        .ilike("name", service_name)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]