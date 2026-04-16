#!/usr/bin/env python3
# ============================================================
# Capsule - Local Knowledge OS
# File: repair_embeddings.py
# Version: 1.0.0
# Date: 2026-04-16
# Purpose: (Re)embed all entries using the v1.0.0 chunker.
#
# When to run:
#   - After running the 001_schema_v1.sql migration (which wipes
#     the vector column), to restore embeddings.
#   - Any time you suspect embeddings are out of sync with entries.
#   - After pulling new code with chunker improvements, to regenerate
#     embeddings using the new strategy.
#
# What it does:
#   - Finds every entry with no embedding rows.
#   - Chunks each entry's content (paragraph-based, no truncation).
#   - Embeds each chunk via Ollama.
#   - Inserts one embeddings row per chunk.
#
# Safe to re-run. Entries that already have embeddings are skipped.
# If you want to force re-embed everything, run with --force.
# ============================================================

import asyncio
import sys
from sqlalchemy import text
from database import SessionLocal
from models import Embedding
from embeddings import generate_embedding
from chunker import chunk_text


FORCE = "--force" in sys.argv


async def repair():
    db = SessionLocal()
    try:
        if FORCE:
            print("⚠️  --force specified. Re-embedding ALL entries.")
            rows = db.execute(text("""
                SELECT e.id, e.title, e.raw_content
                FROM entries e
                ORDER BY e.id
            """)).fetchall()
            # Clear all existing embeddings up front, in one transaction.
            db.execute(text("DELETE FROM embeddings"))
            db.commit()
        else:
            rows = db.execute(text("""
                SELECT e.id, e.title, e.raw_content
                FROM entries e
                LEFT JOIN embeddings emb ON emb.entry_id = e.id
                WHERE emb.id IS NULL
                ORDER BY e.id
            """)).fetchall()

        total = len(rows)
        if total == 0:
            print("✅ Nothing to repair.")
            if not FORCE:
                print("   Every entry already has at least one embedding.")
                print("   To force re-embed everything: python3 repair_embeddings.py --force")
            return

        action = "Re-embedding" if FORCE else "Repairing"
        print(f"🔧 {action} {total} entries...")
        print()

        entry_success = 0
        entry_failed = 0
        total_chunks = 0

        for i, row in enumerate(rows, 1):
            entry_id = row.id
            title = row.title or "(no title)"
            content = row.raw_content or ""

            if not content.strip():
                print(f"⚠️  [{i}/{total}] Entry {entry_id} has no content — skipping")
                entry_failed += 1
                continue

            chunks = chunk_text(content)
            if not chunks:
                print(f"⚠️  [{i}/{total}] Entry {entry_id} produced no chunks — skipping")
                entry_failed += 1
                continue

            chunks_added = 0
            try:
                for chunk in chunks:
                    vector = await generate_embedding(chunk)
                    if not vector:
                        continue
                    db.add(Embedding(
                        entry_id=entry_id,
                        chunk_text=chunk,
                        vector=vector,
                    ))
                    chunks_added += 1

                if chunks_added > 0:
                    db.commit()
                    total_chunks += chunks_added
                    print(f"✅ [{i}/{total}] Entry {entry_id}: {chunks_added}/{len(chunks)} chunks — {title[:55]}")
                    entry_success += 1
                else:
                    db.rollback()
                    print(f"❌ [{i}/{total}] Entry {entry_id} failed: no chunks embedded — {title[:55]}")
                    entry_failed += 1

            except Exception as e:
                db.rollback()
                print(f"❌ [{i}/{total}] Entry {entry_id} error: {e}")
                entry_failed += 1

        print()
        print(f"🎉 Done — {entry_success} entries succeeded ({total_chunks} chunks), "
              f"{entry_failed} entries failed")

        if entry_failed > 0:
            print()
            print("Common causes of failure:")
            print("  - Ollama not running (start it with `ollama serve` or open the app)")
            print("  - nomic-embed-text not pulled (run `ollama pull nomic-embed-text`)")
            print("  - Entry has no content")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(repair())
