import json
import re

from openai import OpenAI

from .config import settings

client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def chat(messages, tools=None, json_mode=False, temperature=0.1):
    kw = {}
    if tools:
        kw["tools"] = tools
    elif json_mode:
        kw["response_format"] = {"type": "json_object"}
    return client.chat.completions.create(
        model=settings.llm_model, messages=messages, temperature=temperature, **kw
    )


def safe_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j > i:
            return json.loads(text[i : j + 1])
        raise


def json_chat(system: str, user: str) -> dict:
    r = chat([{"role": "system", "content": system}, {"role": "user", "content": user}], json_mode=True)
    return safe_json(r.choices[0].message.content)