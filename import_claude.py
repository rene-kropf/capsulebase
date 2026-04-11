# ============================================================
# Capsule - Local Knowledge OS
# File: import_claude.py
# Version: 1.0.0
# Date: 2026-03-13
# Changes: Initial build - Claude JSON export importer
# Usage: python3 import_claude.py conversations.json
#        python3 import_claude.py conversations.json --limit 10
# ============================================================

import json
import sys
import argparse
import httpx
from datetime import datetime

CAPSULE_URL = "http://localhost:8000"

def extract_text(message):
    """Extract plain text from a message, handles both text field and content blocks."""
    # Try simple text field first
    if message.get("text"):
        return message["text"]
    # Fall back to content blocks
    content = message.get("content", [])
    parts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
    return " ".join(parts).strip()

def format_conversation(convo):
    """Format a conversation into a readable text block."""
    messages = convo.get("chat_messages", [])
    lines = []
    for msg in messages:
        sender = msg.get("sender", "unknown").upper()
        text = extract_text(msg)
        if text:
            lines.append(f"{sender}: {text}")
    return "\n\n".join(lines)

def import_conversation(convo, dry_run=False):
    """Send a single conversation to Capsule."""
    title = convo.get("name") or "Untitled Conversation"
    content = format_conversation(convo)
    
    if not content.strip():
        return "skipped", "no content"

    if dry_run:
        print(f"  [DRY RUN] Would import: {title[:60]}")
        return "dry_run", None

    payload = {
        "platform": "claude",
        "title": title,
        "content": content,
        "conversation_date": convo.get("created_at", "")
    }

    try:
        response = httpx.post(
            f"{CAPSULE_URL}/import/conversation",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return "ok", None
        else:
            return "error", f"HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return "error", str(e)

def main():
    parser = argparse.ArgumentParser(description="Import Claude export into Capsule")
    parser.add_argument("file", help="Path to conversations.json from Claude export")
    parser.add_argument("--limit", type=int, help="Only import first N conversations")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--skip", type=int, default=0, help="Skip first N conversations")
    args = parser.parse_args()

    print(f"\n🚀 Capsule - Claude Import")
    print(f"{'=' * 50}")

    with open(args.file, "r") as f:
        conversations = json.load(f)

    total = len(conversations)
    print(f"📦 Found {total} conversations in export")

    # Apply skip and limit
    conversations = conversations[args.skip:]
    if args.limit:
        conversations = conversations[:args.limit]

    print(f"📋 Processing {len(conversations)} conversations")
    if args.dry_run:
        print(f"🔍 DRY RUN - no data will be written")
    print(f"{'=' * 50}\n")

    ok = 0
    skipped = 0
    errors = 0

    for i, convo in enumerate(conversations, 1):
        title = convo.get("name") or "Untitled"
        msg_count = len(convo.get("chat_messages", []))
        print(f"[{i}/{len(conversations)}] {title[:55]:<55} ({msg_count} msgs)", end=" ")

        status, reason = import_conversation(convo, dry_run=args.dry_run)

        if status == "ok" or status == "dry_run":
            print("✅")
            ok += 1
        elif status == "skipped":
            print(f"⏭  {reason}")
            skipped += 1
        else:
            print(f"❌ {reason}")
            errors += 1

    print(f"\n{'=' * 50}")
    print(f"✅ Imported:  {ok}")
    print(f"⏭  Skipped:   {skipped}")
    print(f"❌ Errors:    {errors}")
    print(f"{'=' * 50}\n")

if __name__ == "__main__":
    main()
