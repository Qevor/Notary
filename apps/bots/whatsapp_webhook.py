from __future__ import annotations


def parse_whatsapp_message(text: str) -> dict[str, str]:
    lowered = text.lower()
    if "pay" in lowered and "when" in lowered:
        return {"intent": "conditional_payment", "text": text}
    if "dispute" in lowered:
        return {"intent": "dispute", "text": text}
    return {"intent": "observation", "text": text}

