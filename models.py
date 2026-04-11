# ============================================================
# Capsule - Local Knowledge OS
# File: models.py
# Version: 1.1.0
# Date: 2026-04-10
# Changes: Added source_url to Entry for URL-based dedup
# ============================================================

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id          = Column(Integer, primary_key=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text)
    created_at  = Column(TIMESTAMP, default=datetime.utcnow)

    entries     = relationship("Entry", back_populates="project")


class Entry(Base):
    __tablename__ = "entries"

    id          = Column(Integer, primary_key=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=True)
    source      = Column(String(50), nullable=False)  # email/claude/chatgpt/manual
    source_url  = Column(Text, nullable=True)          # conversation URL for dedup
    title       = Column(Text)
    raw_content = Column(Text)
    summary     = Column(Text)
    created_at  = Column(TIMESTAMP, default=datetime.utcnow)

    project     = relationship("Project", back_populates="entries")
    metadata_   = relationship("EntryMetadata", back_populates="entry", uselist=False)
    conversation= relationship("Conversation", back_populates="entry", uselist=False)
    embeddings  = relationship("Embedding", back_populates="entry")


class EntryMetadata(Base):
    __tablename__ = "entry_metadata"

    id          = Column(Integer, primary_key=True)
    entry_id    = Column(Integer, ForeignKey("entries.id"), nullable=False)
    tags        = Column(ARRAY(String))
    category    = Column(String(100))
    deep_dive_id= Column(Integer, ForeignKey("projects.id"), nullable=True)

    entry       = relationship("Entry", back_populates="metadata_")


class Conversation(Base):
    __tablename__ = "conversations"

    id                  = Column(Integer, primary_key=True)
    entry_id            = Column(Integer, ForeignKey("entries.id"), nullable=False)
    platform            = Column(String(50))
    branch_of           = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    conversation_date   = Column(TIMESTAMP)

    entry       = relationship("Entry", back_populates="conversation")


class Embedding(Base):
    __tablename__ = "embeddings"

    id          = Column(Integer, primary_key=True)
    entry_id    = Column(Integer, ForeignKey("entries.id"), nullable=False)
    chunk_text  = Column(Text)
    vector      = Column(Vector(1536))

    entry       = relationship("Entry", back_populates="embeddings")
