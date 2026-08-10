"""Thin client for the two free-tier LLM providers this repo uses.

See ../../../.agents/skills/llm-call/SKILL.md for which models are
actually free right now and why these particular defaults were picked.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

DEFAULT_OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"


class LLMError(RuntimeError):
    pass


def _load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _repo_root_env():
    here = os.path.dirname(os.path.abspath(__file__))
    # src/vericot -> vericot -> reproductions -> repo root
    root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    _load_dotenv(os.path.join(root, ".env"))


_repo_root_env()


def _retry_delay_seconds(detail, attempt):
    """Prefer the server's own suggested wait (Gemini embeds `retryDelay:
    "42s"` in the 429 body; OpenRouter's daily-cap 429 has no useful delay
    since it won't clear until midnight UTC) over a blind guess."""
    match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', detail)
    if match:
        return int(match.group(1)) + 2
    return 2**attempt * 5


def _post_json(url, headers, payload, timeout=60, retries=4):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code == 429 and attempt < retries - 1:
                time.sleep(_retry_delay_seconds(detail, attempt))
                continue
            raise LLMError(f"HTTP {e.code} from {url}: {detail}") from e
    raise LLMError(f"exhausted retries against {url}")


def call_openrouter(prompt, model=DEFAULT_OPENROUTER_MODEL, temperature=0.0):
    api_key = os.environ.get("OPEN_ROUTER_API_KEY")
    if not api_key:
        raise LLMError("OPEN_ROUTER_API_KEY not set")
    resp = _post_json(
        OPENROUTER_URL,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
    )
    if "choices" not in resp:
        raise LLMError(f"unexpected OpenRouter response: {resp}")
    return resp["choices"][0]["message"]["content"]


def call_gemini(prompt, model=DEFAULT_GEMINI_MODEL, temperature=0.0):
    api_key = os.environ.get("AI_STUDIO_API_KEY")
    if not api_key:
        raise LLMError("AI_STUDIO_API_KEY not set")
    url = GEMINI_URL_TMPL.format(model=model, key=api_key)
    resp = _post_json(
        url,
        {"Content-Type": "application/json"},
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        },
    )
    try:
        parts = resp["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"unexpected Gemini response: {resp}") from e
    # Thinking-capable models (Gemma included) return a leading part with
    # "thought": true holding the reasoning trace -- skip it, we want the
    # actual answer text, not the model's scratch work.
    answer_parts = [p["text"] for p in parts if not p.get("thought") and "text" in p]
    if not answer_parts:
        raise LLMError(f"Gemini response had no non-thought text parts: {resp}")
    return "\n".join(answer_parts)


def complete(prompt, provider="openrouter", model=None, temperature=0.0):
    if provider == "openrouter":
        return call_openrouter(prompt, model=model or DEFAULT_OPENROUTER_MODEL, temperature=temperature)
    if provider == "gemini":
        return call_gemini(prompt, model=model or DEFAULT_GEMINI_MODEL, temperature=temperature)
    raise LLMError(f"unknown provider: {provider}")
