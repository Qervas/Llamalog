from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from typing import List, Optional

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with conversations
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('sessions.id'))
    user_input: Mapped[str] = mapped_column(Text)
    ai_response: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship with session
    session: Mapped["Session"] = relationship("Session", back_populates="conversations")

class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(255))
    type_desc: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(50))
    size: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
