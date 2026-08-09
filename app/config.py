import os

from dotenv import load_dotenv

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
N8N_API_KEY = os.getenv("N8N_API_KEY")


if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL non configurata")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY non configurata")