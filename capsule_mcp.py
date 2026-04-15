# ============================================================
# Capsule MCP Server
# File: capsule_mcp.py
# Version: 1.1.0
# Date: 2026-04-15
# Changes: Switched to hybrid search (/search/hybrid) so
#          results work with or without embeddings
# ============================================================

import httpx
import json
from mcp.server.fastmcp import FastMCP

CAPSULE_URL = "http://localhost:8000"

mcp = FastMCP("Capsule")

@mcp.tool()
async def search_capsule(query: str, limit: int = 5) -> str:
    """
    Search your personal Capsule knowledge base for relevant past conversations and notes.
    Use this to retrieve context from previous discussions before answering questions.
    Returns summaries and key tags from the most relevant entries.

    Args:
        query: What to search for — use natural language describing the topic
        limit: Number of results to return (default 5, max 10)
    """
    try:
        limit = min(limit, 10)
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{CAPSULE_URL}/search/hybrid",
                params={"q": query, "limit": limit}
            )
            res.raise_for_status()
            results = res.json()

        if not results:
            return "No relevant entries found in Capsule for this query."

        lines = [f"Found {len(results)} relevant entries in Capsule:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"--- Entry {i}: {r['title']} ---")
            lines.append(f"Source: {r['source']} | Category: {r.get('category', 'Unknown')} | Relevance: {int(r.get('similarity', 0) * 100)}%")
            if r.get('summary'):
                lines.append(f"Summary: {r['summary']}")
            if r.get('tags'):
                lines.append(f"Tags: {', '.join(r['tags'])}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error searching Capsule: {str(e)}"


@mcp.tool()
async def get_capsule_entry(entry_id: int) -> str:
    """
    Retrieve the full content of a specific Capsule entry by ID.
    Use this when you need the complete conversation text, not just the summary.

    Args:
        entry_id: The numeric ID of the entry to retrieve
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{CAPSULE_URL}/entries/{entry_id}")
            res.raise_for_status()
            entry = res.json()

        lines = [
            f"Title: {entry['title']}",
            f"Source: {entry['source']} | Category: {entry.get('category', 'Unknown')}",
            f"Tags: {', '.join(entry.get('tags', []))}",
            f"Date: {entry['created_at']}",
            "",
            "Summary:",
            entry.get('summary', 'No summary available'),
            "",
            "Content:",
            entry.get('raw_content', 'No content available')[:4000]
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error retrieving entry: {str(e)}"


if __name__ == "__main__":
    mcp.run()
