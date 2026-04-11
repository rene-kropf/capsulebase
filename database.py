# ============================================================
# Capsule - Local Knowledge OS
# File: database.py
# Version: 1.0.0
# Date: 2026-03-05
# Changes: Initial build - Postgres + pgvector setup
# ============================================================

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost/capsule"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def init_db():
    """Initialize database and enable pgvector extension"""
    from models import Entry, EntryMetadata, Conversation, Embedding, Project

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")
