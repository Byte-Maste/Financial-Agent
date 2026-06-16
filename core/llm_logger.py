import json
import os
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "llm")


def log_llm_call(prompt_messages: list[dict], response_text: str, model: str) -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(LOG_DIR, f"llm_{ts}.txt")

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"=== LLM Call: {ts} | model={model} ===\n\n")
        f.write("--- PROMPT ---\n")
        for msg in prompt_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            f.write(f"\n[{role}]\n{content}\n")
        f.write("\n--- RESPONSE ---\n")
        f.write(response_text)
        f.write("\n")

    return path


def log_llm_call_from_messages(
    messages: list, response_content: str, model: str
) -> str:
    dicts = []
    for m in messages:
        if hasattr(m, "content") and hasattr(m, "type"):
            dicts.append({"role": m.type, "content": m.content})
        elif isinstance(m, dict):
            dicts.append(m)
    return log_llm_call(dicts, response_content, model)
