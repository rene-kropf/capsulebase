# ============================================================
# Capsule - Local Knowledge OS
# File: resummary.py
# Version: 1.0.0
# One-time script to re-process all entries with Claude
# Run from your capsule project directory:
#   python resummary.py
# ============================================================

import asyncio
import time
from database import SessionLocal
from models import Entry, EntryMetadata, Embedding
from ai_processor import process_entry
from embeddings import generate_embedding

BATCH_SIZE   = 5    # entries to process before a short pause
PAUSE_SECS   = 2    # seconds between batches (rate limit buffer)
START_OFFSET = 0    # set higher to resume from a specific entry if interrupted

async def resummary():
    db = SessionLocal()
    try:
        entries = db.query(Entry).order_by(Entry.id.asc()).offset(START_OFFSET).all()
        total = len(entries)
        print(f"📦 Found {total} entries to reprocess\n")

        success = 0
        failed  = 0

        for i, entry in enumerate(entries, 1):
            print(f"[{i}/{total}] Processing: {entry.title[:60]}")

            if not entry.raw_content or not entry.raw_content.strip():
                print(f"  ⚠️  Skipping — no raw content\n")
                continue

            try:
                # Re-run AI processing
                ai_result = await process_entry(entry.title, entry.raw_content)

                # Update summary
                entry.summary = ai_result.get("summary", "")

                # Update or create metadata
                metadata = db.query(EntryMetadata).filter(
                    EntryMetadata.entry_id == entry.id
                ).first()

                if metadata:
                    metadata.tags     = ai_result.get("tags", [])
                    metadata.category = ai_result.get("category", "Uncategorized")
                else:
                    metadata = EntryMetadata(
                        entry_id = entry.id,
                        tags     = ai_result.get("tags", []),
                        category = ai_result.get("category", "Uncategorized")
                    )
                    db.add(metadata)

                # Regenerate embedding
                embedding_vector = await generate_embedding(entry.raw_content)
                if embedding_vector:
                    existing_emb = db.query(Embedding).filter(
                        Embedding.entry_id == entry.id
                    ).first()
                    if existing_emb:
                        existing_emb.chunk_text = entry.raw_content[:2000]
                        existing_emb.vector     = embedding_vector
                    else:
                        emb = Embedding(
                            entry_id   = entry.id,
                            chunk_text = entry.raw_content[:2000],
                            vector     = embedding_vector
                        )
                        db.add(emb)

                db.commit()
                print(f"  ✅ Done — {ai_result.get('category', '?')} | tags: {ai_result.get('tags', [])[:3]}\n")
                success += 1

            except Exception as e:
                db.rollback()
                print(f"  ❌ Error: {e}\n")
                failed += 1

            # Pause between batches
            if i % BATCH_SIZE == 0:
                print(f"  ⏸  Batch pause {PAUSE_SECS}s...\n")
                await asyncio.sleep(PAUSE_SECS)

        print(f"\n{'='*50}")
        print(f"✅ Complete: {success} succeeded, {failed} failed out of {total}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(resummary())
