# ============================================================
# Capsule - Local Knowledge OS
# File: chunker.py
# Version: 1.0.0
# Date: 2026-04-16
# Purpose: Split entry content into embedding-ready chunks.
#
# Strategy:
#   Paragraph-based with accumulation up to a target size, and a
#   small overlap between chunks so concepts that straddle a chunk
#   boundary don't get lost.
#
#   Designed for conversational content where:
#     - Natural boundaries are paragraph breaks (turn boundaries)
#     - High-value synthesis often lands at the end
#     - Length varies wildly (a few hundred to tens of thousands
#       of characters)
#
#   Key behaviors:
#     - No truncation anywhere. Every paragraph gets emitted.
#     - Short terminal paragraphs ("so yeah, that's the call") are
#       merged with the substantive paragraph right before them.
#     - Small overlap (~150 chars) ties adjacent chunks together.
#     - Pure function. No DB, no HTTP, no state. Easy to test.
# ============================================================

from typing import List

# Tuning constants.
# TARGET_CHARS is the soft limit per chunk. Chunks can run slightly
# over if a single paragraph exceeds it (we don't split paragraphs).
# 1500 chars is roughly 350-500 tokens with nomic-embed-text — well
# inside the model's 8192-token context window.
TARGET_CHARS = 1500

# Overlap between adjacent chunks. Helps retrieval when a relevant
# concept straddles a boundary. ~150 chars is a couple of sentences.
OVERLAP_CHARS = 150

# Minimum chunk size. If the final chunk is smaller than this, merge
# it into the previous chunk rather than emit a tiny standalone chunk.
# Protects against "so yeah" or "thanks" ending up as their own chunk.
MIN_FINAL_CHARS = 200


def chunk_text(content: str) -> List[str]:
    """
    Split conversation content into chunks suitable for embedding.

    Returns a list of chunk strings. Each chunk is independently
    embeddable. Every part of the original content appears in at
    least one chunk.
    """
    if not content or not content.strip():
        return []

    # Split on blank lines (paragraph boundaries). Strip and drop empties.
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    if not paragraphs:
        return []

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        # +2 accounts for the "\n\n" we'll re-add between paragraphs
        para_len = len(para) + (2 if current else 0)

        # If adding this paragraph would push us over target AND we
        # already have content, emit what we have and start a new chunk.
        if current and (current_len + para_len) > TARGET_CHARS:
            chunks.append("\n\n".join(current))
            # Seed the next chunk with an overlap tail from the chunk
            # we just emitted. Keeps continuity across the boundary.
            overlap = _tail(chunks[-1], OVERLAP_CHARS)
            if overlap:
                current = [overlap, para]
                current_len = len(overlap) + 2 + len(para)
            else:
                current = [para]
                current_len = len(para)
        else:
            current.append(para)
            current_len += para_len

    # Final chunk. If it's too small, merge into the previous chunk
    # instead of emitting a near-empty standalone vector.
    if current:
        final = "\n\n".join(current)
        if chunks and len(final) < MIN_FINAL_CHARS:
            chunks[-1] = chunks[-1] + "\n\n" + final
        else:
            chunks.append(final)

    return chunks


def _tail(text: str, n_chars: int) -> str:
    """
    Return the last ~n_chars of text, preferring to start at a
    sentence or paragraph boundary so the overlap reads cleanly.
    """
    if len(text) <= n_chars:
        return text

    tail = text[-n_chars:]

    # Try to start the overlap at a sentence-ish boundary.
    # Look for ". " or "! " or "? " or "\n" in the first portion
    # of the tail; if we find one, start just after it.
    for marker in [". ", "! ", "? ", "\n"]:
        idx = tail.find(marker)
        if 0 <= idx < n_chars // 2:
            return tail[idx + len(marker):].strip()

    # No clean boundary found — just use the raw tail.
    return tail.strip()


# ============================================================
# Quick self-test. Run with:  python3 chunker.py
# ============================================================
if __name__ == "__main__":
    sample = """Me: I want to talk about fig trees in Oklahoma.

Claude: Figs do well in Oklahoma, though Bartlesville sits in a tricky spot.
You're in zone 7a, which is right at the edge of where figs survive winters
without dying back to the roots.

Variety matters a lot. Cold-hardy cultivars are the way to go. Chicago Hardy
is the standard recommendation for your zone — it will die back in a bad
winter but regrow from the roots and still fruit on new wood the same season.

Me: what about winter protection

Claude: Minimum protection is heavy mulch over the root zone. 6-12 inches of
straw or leaves after the first hard freeze. That alone saves the roots
through almost anything.

For more protection, add a trunk wrap with burlap plus a chicken-wire cage
stuffed with dry leaves. Covers the lower 3-4 feet of wood.

So yeah — for your setup, Chicago Hardy with heavy mulch is the call."""

    result = chunk_text(sample)
    print(f"Original: {len(sample)} chars, {len(sample.split(chr(10)+chr(10)))} paragraphs")
    print(f"Chunks: {len(result)}")
    for i, c in enumerate(result, 1):
        print(f"\n--- Chunk {i} ({len(c)} chars) ---")
        print(c[:200] + ("..." if len(c) > 200 else ""))
