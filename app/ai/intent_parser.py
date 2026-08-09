from openai import OpenAI
import json

client = OpenAI()


def parse_intent(message: str, history=None, conversation=None, context=None) -> dict:
    """
    Analizza il messaggio dell'utente usando OpenAI.
    """

    history = history or []

    history_text = "\n".join(
        f"{item['role']}: {item['message']}"
        for item in history
    )

    conversation_state = {
        "workflow": conversation.get("workflow") if conversation else None,
        "step": conversation.get("step") if conversation else None,
    }

    prompt = f"""
Sei il motore AI di un sistema di prenotazione WhatsApp.

Devi classificare il messaggio dell'utente considerando
anche la conversazione precedente.

CONVERSATION STATE:
{json.dumps(conversation_state, ensure_ascii=False)}

CONTEXT:
{json.dumps(context or {}, ensure_ascii=False)}

HISTORY:
{history_text}

MESSAGGIO ATTUALE:
{message}

Intent possibili:
- BOOKING_REQUEST
- BOOKING_CHANGE
- BOOKING_CANCEL
- INFORMATION_REQUEST
- UNKNOWN

Regole:
- considera sempre la conversazione precedente
- una frase come "sabato mattina" può essere una risposta
  ad una precedente richiesta di prenotazione
- non classificare il messaggio isolatamente
- restituisci esclusivamente JSON valido

Formato:
{{
  "intent": "...",
  "entities": {{}},
  "confidence": 0.0,
  "notes": "..."
}}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return json.loads(response.output_text)