# ============================================================
# Capsule - Local Knowledge OS
# File: embeddings.py
# Version: 1.0.0
# Date: 2026-03-05
# Changes: Initial build - embedding generation dual provider
# ============================================================

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER     = os.getenv("AI_PROVIDER", "ollama")
OLLAMA_URL      = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED    = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")


async def generate_embedding(text: str) -> list | None:
    """Generate vector embedding for text"""
    if AI_PROVIDER == "ollama":
        return await _embed_ollama(text)
    else:
        return await _embed_openai(text)


async def _embed_ollama(text: str) -> list | None:
    """Generate embedding via Ollama"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={
                    "model": OLLAMA_EMBED,
                    "prompt": text[:4000]
                }
            )
            response.raise_for_status()
            return response.json().get("embedding")

    except Exception as e:
        print(f"❌ Ollama embedding error: {e}")
        return None


async def _embed_openai(text: str) -> list | None:
    """Generate embedding via OpenAI"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "text-embedding-3-small",
                    "input": text[:8000]
                }
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]

    except Exception as e:
        print(f"❌ OpenAI embedding error: {e}")
        return None
