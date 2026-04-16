# ============================================================
# Capsule - Local Knowledge OS
# File: embeddings.py
# Version: 1.0.0
# Date: 2026-04-16
# Changes: Fail loudly if AI_PROVIDER=openai is configured
#          for embeddings. Capsule v1.0.x uses Ollama exclusively
#          for embeddings to match the 768-dimension schema and
#          preserve the local-first guarantee.
# ============================================================

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# AI_PROVIDER controls which service is used for CHAT/summaries
# elsewhere in the app (Claude, OpenAI, Ollama). Embeddings are
# ALWAYS done through Ollama in this version, regardless of
# AI_PROVIDER, for local-first consistency and schema correctness.
AI_PROVIDER     = os.getenv("AI_PROVIDER", "ollama")
OLLAMA_URL      = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED    = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


class EmbeddingConfigError(RuntimeError):
    """Raised when embedding configuration is invalid."""
    pass


async def generate_embedding(text: str) -> list | None:
    """
    Generate a vector embedding for text using Ollama.

    Returns a list of 768 floats on success, or None if the Ollama
    call failed (network error, model not pulled, etc.). None return
    is the signal to the caller that this chunk couldn't be embedded.

    Raises EmbeddingConfigError at startup time if the user has
    AI_PROVIDER=openai set, since OpenAI embeddings produce 1536-dim
    vectors which won't fit the 768-dim schema.
    """
    if AI_PROVIDER == "openai":
        raise EmbeddingConfigError(
            "Capsule v1.0.x uses Ollama for embeddings (768 dimensions). "
            "AI_PROVIDER=openai is not supported for embeddings in this version. "
            "Either:\n"
            "  - Set AI_PROVIDER=claude or AI_PROVIDER=ollama in .env "
            "(OpenAI can still be used for chat if AI_PROVIDER=openai is needed "
            "elsewhere; embeddings will always go through Ollama regardless).\n"
            "  - Make sure Ollama is running: `ollama list` should show "
            "`nomic-embed-text`.\n"
            "  - If you need OpenAI embeddings specifically, open an issue "
            "on GitHub — it's planned but not in v1.0.x."
        )

    return await _embed_ollama(text)


async def _embed_ollama(text: str) -> list | None:
    """Generate embedding via Ollama. Returns 768-dim vector or None."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={
                    "model": OLLAMA_EMBED,
                    "prompt": text,
                }
            )
            response.raise_for_status()
            vector = response.json().get("embedding")

            if not vector:
                print(f"⚠️  Ollama returned empty embedding. Model: {OLLAMA_EMBED}")
                return None

            if len(vector) != 768:
                print(
                    f"⚠️  Ollama returned {len(vector)}-dim vector, expected 768. "
                    f"Model '{OLLAMA_EMBED}' may not match Capsule's schema. "
                    f"Capsule v1.0.x is built for nomic-embed-text (768 dims)."
                )
                return None

            return vector

    except httpx.ConnectError:
        print(
            f"❌ Could not reach Ollama at {OLLAMA_URL}. Is it running?\n"
            f"   Start it with: `ollama serve` or open the Ollama app."
        )
        return None

    except Exception as e:
        print(f"❌ Ollama embedding error: {e}")
        return None
