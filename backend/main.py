from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
import json
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from db_models import Base, Conversation, Session, Artifact
from typing import Optional
from file_processor import process_file
from utils.gen_titles import generate_snippet_title
from pydantic import BaseModel
from utils.llm_client import LLMClient
from utils.search import WebSearchEnhancer
import logging


class TitleRequest(BaseModel):
    content: str
    language: str

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

llm_client = LLMClient()
web_enhancer = WebSearchEnhancer(llm_client, max_tokens_per_chunk=600)

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[int] = None
    settings: Optional[dict] = None

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

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await process_file(file)
    if content is None:
        raise HTTPException(status_code=400, detail="Could not process file")

    return {
        "filename": file.filename,
        "content": content
    }

@app.post("/generate_title")
async def generate_title(request: TitleRequest):
    try:
        title, type_desc = generate_snippet_title(request.content, request.language)
        return {"title": title, "type_desc": type_desc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/artifacts")
async def create_artifact(artifact_data: dict):
    db = SessionLocal()
    try:
        artifact = Artifact(
            id=artifact_data["id"],
            content=artifact_data["content"],
            title=artifact_data["title"],
            type_desc=artifact_data["type_desc"],
            language=artifact_data["language"],
            size=artifact_data["size"]
        )
        db.add(artifact)
        db.commit()
        return {"message": "Artifact saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/artifacts")
async def get_artifacts():
    db = SessionLocal()
    try:
        artifacts = db.query(Artifact).order_by(Artifact.created_at.desc()).all()
        return [{
            "id": art.id,
            "title": art.title,
            "type_desc": art.type_desc,
            "language": art.language,
            "content": art.content,
            "size": art.size
        } for art in artifacts]
    finally:
        db.close()

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

        settings = chat_message.settings or {
            "model": "llama-3.2-3b-instruct",
            "max_tokens": 2048,
            "temperature": 0.7,
            "stream": True
        }

        async def stream_response():
            collected_response = []
            db_inner = SessionLocal()

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream(
                        "POST",
                        "http://127.0.0.1:8080/v1/chat/completions",
                        json={
                            **settings,
                            "messages": messages,
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

@app.post("/chat/web")
async def chat_with_web(chat_message: ChatMessage):
    logger = logging.getLogger(__name__)

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

        async def stream_response():
            collected_response = []
            db_inner = SessionLocal()

            try:
                context = [
                    {"role": "user", "content": msg.user_input}
                    for msg in db_inner.query(Conversation).filter(
                        Conversation.session_id == session_id
                    ).order_by(Conversation.timestamp.desc()).limit(5)
                ]

                # Get the response generator
                response_generator = web_enhancer.enhance_response(
                    chat_message.message,
                    context=context
                )

                # Iterate through the responses
                async for chunk in response_generator:
                    collected_response.append(chunk)
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for natural flow

                # Save complete conversation to database
                complete_response = "".join(collected_response)
                conversation = Conversation(
                    session_id=session_id,
                    user_input=chat_message.message,
                    ai_response=complete_response
                )
                db_inner.add(conversation)
                db_inner.commit()

            except Exception as e:
                logger.error(f"Error in stream_response: {str(e)}")
                db_inner.rollback()
                yield f"data: {json.dumps({'content': f'Error: {str(e)}'})}\n\n"
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
