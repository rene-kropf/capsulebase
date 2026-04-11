# ============================================================
# Capsule - Local Knowledge OS
# File: import_chatgpt.py
# Version: 1.0.0
# Date: 2026-04-10
# Usage: python3 import_chatgpt.py conversations.json
#        python3 import_chatgpt.py conversations.json --limit 10
#        python3 import_chatgpt.py conversations.json --dry-run
# ============================================================

import json
import sys
import argparse
import httpx
from datetime import datetime

CAPSULE_URL = "http://localhost:8000"

def extract_messages(conversation):
    """
    ChatGPT export format uses a 'mapping' dict where each node has:
    - id, parent, children
    - message: { role, content: { parts: [...] } }
    We walk the tree from root to get messages in order.
    """
    mapping = conversation.get("mapping", {})
    if not mapping:
        return []

    # Find root node (no parent or parent is None)
    root_id = None
    for node_id, node in mapping.items():
        if not node.get("parent"):
            root_id = node_id
            break

    if not root_id:
        return []

    # Walk tree in order
    messages = []
    visited = set()

    def walk(node_id):
        if node_id in visited or node_id not in mapping:
            return
        visited.add(node_id)
        node = mapping[node_id]
        msg = node.get("message")
        if msg:
            role = msg.get("author", {}).get("role", "")
            content = msg.get("content", {})
            parts = content.get("parts", [])
            text = ""
            for part in parts:
                if isinstance(part, str):
                    text += part
                elif isinstance(part, dict) and part.get("content_type") == "text":
                    text += part.get("text", "")
            if text.strip() and role in ("user", "assistant"):
                messages.append({
                    "role": "HUMAN" if role == "user" else "ASSISTANT",
                    "text": text.strip()
                })
        # Walk first child (main conversation thread)
        children = node.get("children", [])
        if children:
            walk(children[0])

    walk(root_id)
    return messages


def format_conversation(convo):
    messages = extract_messages(convo)
    if not messages:
        return ""
    return "\n\n".join(f"{m['role']}: {m['text']}" for m in messages)


def import_conversation(convo, dry_run=False):
    title = convo.get("title") or "Untitled Conversation"
    content = format_conversation(convo)

    if not content.strip():
        return "skipped", "no content"

    if dry_run:
        print(f"  [DRY RUN] Would import: {title[:60]}")
        return "dry_run", None

    # Get conversation date
    created = convo.get("create_time")
    conv_date = datetime.fromtimestamp(created).isoformat() if created else None

    payload = {
        "platform": "chatgpt",
        "title": title,
        "content": content,
        "conversation_date": conv_date
    }

    try:
        response = httpx.post(
            f"{CAPSULE_URL}/import/conversation",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            action = response.json().get("action", "saved")
            return action, None
        else:
            return "error", f"HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return "error", str(e)


def main():
    parser = argparse.ArgumentParser(description="Import ChatGPT export into Capsule")
    parser.add_argument("file", help="Path to conversations.json from ChatGPT export")
    parser.add_argument("--limit", type=int, help="Only import first N conversations")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--skip", type=int, default=0, help="Skip first N conversations")
    args = parser.parse_args()

    print(f"\n🚀 Capsule — ChatGPT Import")
    print(f"{'=' * 50}")

    with open(args.file, "r") as f:
        conversations = json.load(f)

    total = len(conversations)
    print(f"📦 Found {total} conversations in export")

    conversations = conversations[args.skip:]
    if args.limit:
        conversations = conversations[:args.limit]

    print(f"📋 Processing {len(conversations)} conversations")
    if args.dry_run:
        print(f"🔍 DRY RUN — no data will be written")
    print(f"{'=' * 50}\n")

    created = skipped = updated = errors = 0

    for i, convo in enumerate(conversations, 1):
        title = convo.get("title") or "Untitled"
        msg_count = len(convo.get("mapping", {}))
        print(f"[{i}/{len(conversations)}] {title[:55]:<55} ({msg_count} nodes)", end=" ")

        status, reason = import_conversation(convo, dry_run=args.dry_run)

        if status in ("created", "dry_run"):
            print("✅")
            created += 1
        elif status == "updated":
            print("🔄 updated")
            updated += 1
        elif status == "skipped":
            print(f"⏭  {reason}")
            skipped += 1
        else:
            print(f"❌ {reason}")
            errors += 1

    print(f"\n{'=' * 50}")
    print(f"✅ Created:  {created}")
    print(f"🔄 Updated:  {updated}")
    print(f"⏭  Skipped:  {skipped}")
    print(f"❌ Errors:   {errors}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
