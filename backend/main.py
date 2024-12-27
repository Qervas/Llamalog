from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
import json
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from db_models import Base, Conversation, Session
from typing import Optional

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = "sqlite:///./chat_history.db"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[int] = None

class SessionCreate(BaseModel):
    title: str = "New Chat"

class SessionUpdate(BaseModel):
    title: str

@app.post("/sessions")
async def create_session():
    db = SessionLocal()
    new_session = Session(title="New Chat")
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {
        "id": new_session.id,
        "title": new_session.title,
        "created_at": new_session.created_at
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: int):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    conversations = db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).order_by(Conversation.timestamp).all()

    return {
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at
        },
        "conversations": [{
            "user_input": conv.user_input,
            "ai_response": conv.ai_response,
            "timestamp": conv.timestamp
        } for conv in conversations]
    }

@app.put("/sessions/{session_id}")
async def update_session(session_id: int, session_update: SessionUpdate):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = session_update.title
    session.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Session updated successfully"}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    db = SessionLocal()
    try:
        # First delete associated conversations
        db.query(Conversation).filter(Conversation.session_id == session_id).delete()

        # Then delete the session
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        db.delete(session)
        db.commit()
        return {"message": "Session deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/sessions")
async def get_sessions():
    db = SessionLocal()
    sessions = db.query(Session).order_by(Session.updated_at.desc()).all()
    return [{
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    } for session in sessions]

@app.post("/chat")
async def chat(chat_message: ChatMessage):
    db = SessionLocal()
    try:
        session_id = chat_message.session_id
        if not session_id:
            title = chat_message.message[:30] + "..." if len(chat_message.message) > 30 else chat_message.message
            new_session = Session(title="New Chat")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            session_id = new_session.id

        # Get conversation history for this session
        previous_messages = db.query(Conversation).filter(
            Conversation.session_id == session_id
        ).order_by(Conversation.timestamp).all()

        # Build the messages array with conversation history
        messages = []

        # Add system message to set the context and behavior
        messages.append({
            "role": "system",
            "content": "You are a helpful AI assistant. Be concise and clear in your responses."
        })

        # Add previous conversations
        for msg in previous_messages:
            messages.extend([
                {"role": "user", "content": msg.user_input},
                {"role": "assistant", "content": msg.ai_response}
            ])

        # Add the current message
        messages.append({"role": "user", "content": chat_message.message})

        async def stream_response():
            collected_response = []
            db_inner = SessionLocal()

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream(
                        "POST",
                        "http://127.0.0.1:8080/v1/chat/completions",
                        json={
                            "model": "llama-3.2-3b-instruct",
                            "messages": messages,
                            "max_tokens": 2048,
                            "temperature": 0.7,
                            "stream": True
                        },
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    if line.startswith("data: "):
                                        line = line[6:]
                                    if line == "[DONE]":
                                        continue

                                    json_line = json.loads(line)
                                    if content := json_line.get('choices', [{}])[0].get('delta', {}).get('content'):
                                        collected_response.append(content)
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                                except json.JSONDecodeError:
                                    continue

                # Save complete conversation to database
                complete_response = "".join(collected_response)
                conversation = Conversation(
                    session_id=session_id,
                    user_input=chat_message.message,
                    ai_response=complete_response
                )
                db_inner.add(conversation)

                # Update session's updated_at
                session = db_inner.query(Session).filter(Session.id == session_id).first()
                if session:
                    session.updated_at = datetime.utcnow()
                db_inner.commit()
            except Exception as e:
                db_inner.rollback()
                raise e
            finally:
                db_inner.close()

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
