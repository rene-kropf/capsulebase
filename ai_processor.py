# ============================================================
# Capsule - Local Knowledge OS
# File: ai_processor.py
# Version: 1.2.0
# Date: 2026-04-06
# Changes: Added Claude (Anthropic) as AI provider option
# ============================================================

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER       = os.getenv("AI_PROVIDER", "claude")
OLLAMA_URL        = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3.2")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

SYSTEM_PROMPT = """You are a personal knowledge classifier for Capsule, a local AI conversation archive.

Your job is to process conversations and notes that a person wants to remember and retrieve later.
Content will be AI conversations (Claude, ChatGPT etc.), voice transcriptions, or personal notes.
Never expect web articles or URLs — this is a conversation and thinking archive.

Return ONLY valid JSON with these exact fields. No explanation. No markdown. Just the object:
{
  "title": "concise descriptive title capturing the core topic — max 10 words",
  "summary": "2-3 sentences capturing what was figured out, decided, or explored. Written so the person understands the value of this entry at a glance without re-reading it.",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "category": "one of: Architecture / Strategy / Technical / Decision / Insight / Planning / Personal / Reference",
  "deep_dive_hint": "if this clearly belongs to an ongoing topic or project name it — otherwise empty string"
}

Tag guidance — be specific and useful. Prefer concrete nouns over vague adjectives.
Good: filemaker, local-first, pricing, simplesuite, capsule, performance, sync, workflow
Bad: interesting, important, good, various, misc

Category guidance:
- Architecture: system design, technical structure, how things connect
- Strategy: business direction, positioning, product decisions
- Technical: code, implementation, specific technology problems solved
- Decision: a conclusion was reached, a clear choice was made
- Insight: a realization or principle that changes how you think about something
- Planning: roadmap, next steps, what to build next
- Personal: life, family, non-work thinking
- Reference: factual, something to look up again"""


async def process_entry(title: str, content: str) -> dict:
    prompt = f"Title: {title}\n\nContent:\n{content[:3000]}"
    if AI_PROVIDER == "ollama":
        return await _process_ollama(prompt)
    elif AI_PROVIDER == "claude":
        return await _process_claude(prompt)
    else:
        return await _process_openai(prompt)


async def _process_claude(prompt: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            response.raise_for_status()
            raw = response.json()["content"][0]["text"]
            return _parse_ai_response(raw)
    except Exception as e:
        print(f"❌ Claude error: {e}")
        return _fallback_result()


async def _process_openai(prompt: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )
            response.raise_for_status()
            return _parse_ai_response(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return _fallback_result()


async def _process_ollama(prompt: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}", "stream": False}
            )
            response.raise_for_status()
            return _parse_ai_response(response.json().get("response", "{}"))
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return _fallback_result()


def _parse_ai_response(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"⚠️  Could not parse AI response: {e}")
        return _fallback_result()


def _fallback_result() -> dict:
    return {
        "title":          "Untitled",
        "summary":        "",
        "tags":           [],
        "category":       "Uncategorized",
        "deep_dive_hint": ""
    }
