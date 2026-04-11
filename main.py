# ============================================================
# Capsule - Local Knowledge OS
# File: main.py
# Version: 2.1.0
# Date: 2026-04-06
# Changes: URL-based dedup, title update on re-save,
#          source_url stored on all entries
# ============================================================

import os
import json
import httpx
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from database import init_db, SessionLocal
from models import Entry, EntryMetadata, Conversation, Embedding, Project
from ai_processor import process_entry
from embeddings import generate_embedding

load_dotenv()

app = FastAPI(title="Capsule", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()
    print("✅ Database tables ready")
    print("✅ Capsule listener started")
    print("✅ Database ready")


@app.get("/favicon.svg")
async def favicon():
    return FileResponse("favicon.svg", media_type="image/svg+xml")

@app.get("/capsule-icon-{size}.png")
async def capsule_icon(size: int):
    return FileResponse(f"capsule-icon-{size}.png", media_type="image/png")

@app.get("/")
async def serve_ui():
    return FileResponse("capsule.html")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Capsule", "version": "2.1.0"}

# ============================================================
# BACKGROUND AI PROCESSING
# ============================================================
async def process_entry_background(entry_id: int, title: str, content: str):
    db = SessionLocal()
    try:
        entry = db.query(Entry).filter(Entry.id == entry_id).first()
        if not entry:
            return
        ai_result = await process_entry(title, content)
        entry.summary = ai_result.get("summary", "")
        metadata = db.query(EntryMetadata).filter(EntryMetadata.entry_id == entry_id).first()
        if metadata:
            metadata.tags = ai_result.get("tags", [])
            metadata.category = ai_result.get("category", "Conversation")
        else:
            metadata = EntryMetadata(
                entry_id=entry_id,
                tags=ai_result.get("tags", []),
                category=ai_result.get("category", "Conversation"),
            )
            db.add(metadata)
        existing_emb = db.query(Embedding).filter(Embedding.entry_id == entry_id).first()
        embedding_vector = await generate_embedding(content)
        if embedding_vector:
            if existing_emb:
                existing_emb.chunk_text = content[:2000]
                existing_emb.vector = embedding_vector
            else:
                emb = Embedding(entry_id=entry_id, chunk_text=content[:2000], vector=embedding_vector)
                db.add(emb)
        db.commit()
        print(f"✅ AI processing complete for entry {entry_id}: {title}")
    except Exception as e:
        print(f"❌ Background processing error: {e}")
        db.rollback()
    finally:
        db.close()

# ============================================================
# CONVERSATION IMPORT
# ============================================================
@app.post("/import/conversation")
async def import_conversation(request: Request):
    body = await request.json()
    platform   = body.get("platform", "unknown")
    title      = body.get("title", "Imported Conversation")
    content    = body.get("content", "")
    branch_of  = body.get("branch_of", None)
    conv_date  = body.get("conversation_date", None)
    project_id = body.get("project_id", None)
    source_url = body.get("source_url", None)

    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty conversation content")

    db = SessionLocal()
    try:
        # URL match first (most reliable), then title match as fallback
        existing = None
        if source_url:
            existing = db.query(Entry).filter(Entry.source_url == source_url).first()
        if not existing:
            existing = db.query(Entry).filter(
                Entry.title == title,
                Entry.source == platform
            ).order_by(Entry.created_at.desc()).first()

        if existing:
            existing.raw_content = content
            existing.summary = None
            existing.title = title  # update title in case it changed
            if source_url:
                existing.source_url = source_url
            db.commit()
            entry_id = existing.id
            print(f"✅ Conversation updated: {title} [{platform}]")
            asyncio.create_task(process_entry_background(entry_id, title, content))
            return {"status": "ok", "entry_id": entry_id, "action": "updated"}

        entry = Entry(source=platform, title=title, raw_content=content,
                      project_id=project_id, source_url=source_url,
                      created_at=datetime.utcnow())
        db.add(entry)
        db.flush()
        conversation = Conversation(
            entry_id=entry.id, platform=platform, branch_of=branch_of,
            conversation_date=datetime.fromisoformat(conv_date) if conv_date else datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        entry_id = entry.id
        print(f"✅ Conversation saved: {title} [{platform}]")
        asyncio.create_task(process_entry_background(entry_id, title, content))
        return {"status": "ok", "entry_id": entry_id, "action": "created"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error importing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================
# MAILGUN WEBHOOK
# ============================================================
@app.post("/inbound/email")
async def receive_email(request: Request):
    form = await request.form()
    subject     = form.get("subject", "No Subject")
    body_plain  = form.get("body-plain", "")
    body_html   = form.get("body-html", "")
    raw_content = body_plain if body_plain.strip() else body_html
    if not raw_content.strip():
        raise HTTPException(status_code=400, detail="Empty email body")
    db = SessionLocal()
    try:
        entry = Entry(source="email", title=subject, raw_content=raw_content, created_at=datetime.utcnow())
        db.add(entry)
        db.flush()
        db.commit()
        asyncio.create_task(process_entry_background(entry.id, subject, raw_content))
        return {"status": "ok", "entry_id": entry.id, "title": subject}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================
# HYBRID SEARCH
# ============================================================
@app.get("/search/hybrid")
async def hybrid_search(q: str, limit: int = 30):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Empty query")
    db = SessionLocal()
    try:
        text_results = db.execute(text("""
            SELECT e.id, e.title, e.summary, e.source, e.created_at,
                   em.tags, em.category,
                   CASE
                     WHEN e.title ILIKE :q THEN 1.0
                     WHEN em.tags::text ILIKE :q THEN 0.9
                     WHEN e.summary ILIKE :q THEN 0.75
                     ELSE 0.3
                   END AS text_score
            FROM entries e
            LEFT JOIN entry_metadata em ON em.entry_id = e.id
            WHERE e.title ILIKE :q
               OR e.summary ILIKE :q
               OR em.tags::text ILIKE :q
            LIMIT 50
        """), {"q": f"%{q}%"}).fetchall()

        semantic_results = []
        query_vector = await generate_embedding(q)
        if query_vector:
            semantic_results = db.execute(text("""
                SELECT e.id, e.title, e.summary, e.source, e.created_at,
                       em.tags, em.category,
                       1 - (emb.vector <=> :qv) AS semantic_score
                FROM embeddings emb
                JOIN entries e ON e.id = emb.entry_id
                LEFT JOIN entry_metadata em ON em.entry_id = e.id
                ORDER BY emb.vector <=> :qv
                LIMIT 50
            """), {"qv": "[" + ",".join(str(x) for x in query_vector) + "]"}).fetchall()

        seen = {}
        for r in text_results:
            seen[r.id] = {
                "id": r.id, "title": r.title, "summary": r.summary,
                "source": r.source, "created_at": str(r.created_at),
                "tags": r.tags, "category": r.category,
                "text_score": float(r.text_score), "semantic_score": 0.0,
                "match_type": "text"
            }
        for r in semantic_results:
            score = float(r.semantic_score)
            if r.id in seen:
                seen[r.id]["semantic_score"] = score
                seen[r.id]["match_type"] = "both"
            else:
                seen[r.id] = {
                    "id": r.id, "title": r.title, "summary": r.summary,
                    "source": r.source, "created_at": str(r.created_at),
                    "tags": r.tags, "category": r.category,
                    "text_score": 0.0, "semantic_score": score,
                    "match_type": "semantic"
                }

        for item in seen.values():
            item["score"] = (item["text_score"] * 0.7) + (item["semantic_score"] * 0.3)
            item["similarity"] = round(item["score"], 3)

        MIN_SCORE = 0.20
        results = [r for r in seen.values() if r["score"] >= MIN_SCORE]
        results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
        return results
    finally:
        db.close()

# ============================================================
# TEXT SEARCH
# ============================================================
@app.get("/search/text")
async def text_search(q: str, limit: int = 20):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Empty query")
    db = SessionLocal()
    try:
        results = db.execute(text("""
            SELECT e.id, e.title, e.summary, e.source, e.created_at,
                   em.tags, em.category,
                   CASE
                     WHEN e.title ILIKE :q THEN 1
                     WHEN em.tags::text ILIKE :q THEN 2
                     WHEN e.summary ILIKE :q THEN 3
                   END AS rank
            FROM entries e
            LEFT JOIN entry_metadata em ON em.entry_id = e.id
            WHERE e.title ILIKE :q
               OR e.summary ILIKE :q
               OR em.tags::text ILIKE :q
            ORDER BY rank, e.created_at DESC
            LIMIT :limit
        """), {"q": f"%{q}%", "limit": limit}).fetchall()
        return [
            {"id": r.id, "title": r.title, "summary": r.summary,
             "source": r.source, "created_at": str(r.created_at),
             "tags": r.tags, "category": r.category}
            for r in results
        ]
    finally:
        db.close()

# ============================================================
# SEMANTIC SEARCH (kept for MCP)
# ============================================================
@app.get("/search")
async def search(q: str, limit: int = 10):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Empty query")
    query_vector = await generate_embedding(q)
    if not query_vector:
        raise HTTPException(status_code=500, detail="Could not generate embedding")
    db = SessionLocal()
    try:
        results = db.execute(text("""
            SELECT e.id, e.title, e.summary, e.source, e.created_at,
                   em.tags, em.category, emb.chunk_text,
                   1 - (emb.vector <=> :query_vector) AS similarity
            FROM embeddings emb
            JOIN entries e ON e.id = emb.entry_id
            LEFT JOIN entry_metadata em ON em.entry_id = e.id
            ORDER BY emb.vector <=> :query_vector
            LIMIT :limit
        """), {
            "query_vector": "[" + ",".join(str(x) for x in query_vector) + "]",
            "limit": limit
        }).fetchall()
        return [
            {"id": r.id, "title": r.title, "summary": r.summary,
             "source": r.source, "created_at": str(r.created_at),
             "tags": r.tags, "category": r.category,
             "similarity": round(float(r.similarity), 3)}
            for r in results
        ]
    finally:
        db.close()

# ============================================================
# ENTRIES
# ============================================================
@app.get("/entries")
async def get_entries(limit: int = 500, offset: int = 0):
    db = SessionLocal()
    try:
        entries = db.query(Entry).order_by(Entry.created_at.desc()).offset(offset).limit(limit).all()
        return [
            {"id": e.id, "title": e.title, "summary": e.summary,
             "source": e.source, "project_id": e.project_id,
             "created_at": str(e.created_at)}
            for e in entries
        ]
    finally:
        db.close()

@app.get("/entries/{entry_id}")
async def get_entry(entry_id: int):
    db = SessionLocal()
    try:
        entry = db.query(Entry).filter(Entry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        metadata = db.query(EntryMetadata).filter(EntryMetadata.entry_id == entry_id).first()
        return {
            "id": entry.id, "title": entry.title, "summary": entry.summary,
            "raw_content": entry.raw_content, "source": entry.source,
            "project_id": entry.project_id, "created_at": str(entry.created_at),
            "tags": metadata.tags if metadata else [],
            "category": metadata.category if metadata else None
        }
    finally:
        db.close()

@app.delete("/entries/{entry_id}")
async def delete_entry(entry_id: int):
    db = SessionLocal()
    try:
        entry = db.query(Entry).filter(Entry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        db.query(Embedding).filter(Embedding.entry_id == entry_id).delete()
        db.query(EntryMetadata).filter(EntryMetadata.entry_id == entry_id).delete()
        db.query(Conversation).filter(Conversation.entry_id == entry_id).delete()
        db.delete(entry)
        db.commit()
        print(f"✅ Entry deleted: {entry_id}")
        return {"status": "ok", "deleted": entry_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================
# PROJECTS
# ============================================================
@app.get("/projects")
async def get_projects():
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        result = []
        for p in projects:
            count = db.query(Entry).filter(Entry.project_id == p.id).count()
            result.append({"id": p.id, "name": p.name, "description": p.description,
                           "created_at": str(p.created_at), "count": count})
        return result
    finally:
        db.close()

@app.post("/projects")
async def create_project(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    desc = body.get("description", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    db = SessionLocal()
    try:
        project = Project(name=name, description=desc, created_at=datetime.utcnow())
        db.add(project)
        db.commit()
        db.refresh(project)
        return {"id": project.id, "name": project.name, "description": project.description,
                "created_at": str(project.created_at), "count": 0}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        db.delete(project)
        db.commit()
        return {"status": "ok", "deleted": project_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
