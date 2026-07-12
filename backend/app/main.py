import os
import logging
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.mongo import db_connection
from app.routers import auth, meetings, notes, tasks, integrations

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")

app = FastAPI(
    title="Autonomous Meeting Notes to Action Items Pipeline",
    description="Full-stack EdTech Platform with RAG, Audio Transcription, Agentic task syncing, and handwriting PDF exports.",
    version="1.0.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all. Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to database on startup
@app.on_event("startup")
async def startup_db_client():
    db_connection.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    db_connection.close()

# Include routers
app.include_router(auth.router)
app.include_router(meetings.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(integrations.router)

# Mount local storage folder for serving generated files
storage_dir = os.path.join(os.getcwd(), "storage")
os.makedirs(storage_dir, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

# Root endpoint
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Autonomous Meeting-Notes-to-Action-Items Backend API."
    }

# -------------------------------------------------------------
# WebSocket Manager for Real-Time Meeting transcription updates
# -------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        if meeting_id not in self.active_connections:
            self.active_connections[meeting_id] = []
        self.active_connections[meeting_id].append(websocket)
        logger.info(f"WebSocket client connected to meeting room {meeting_id}. Total: {len(self.active_connections[meeting_id])}")

    def disconnect(self, meeting_id: str, websocket: WebSocket):
        if meeting_id in self.active_connections:
            self.active_connections[meeting_id].remove(websocket)
            if not self.active_connections[meeting_id]:
                del self.active_connections[meeting_id]
            logger.info(f"WebSocket client disconnected from meeting room {meeting_id}.")

    async def broadcast(self, meeting_id: str, message: dict):
        if meeting_id in self.active_connections:
            for connection in self.active_connections[meeting_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass # handle broken connections gracefully

manager = ConnectionManager()

@app.websocket("/api/meetings/{meeting_id}/websocket")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str):
    await manager.connect(meeting_id, websocket)
    try:
        while True:
            # Receive text or audio blob update from client
            # The client can send message objects like: {"type": "audio_chunk" or "transcript_chunk", "data": "..."}
            data = await websocket.receive_json()
            
            # Broadcast the received chunk to everyone else in the room (e.g. students or host)
            await manager.broadcast(meeting_id, {
                "sender": data.get("sender", "anonymous"),
                "text": data.get("text", ""),
                "timestamp": data.get("timestamp", "00:00")
            })
    except WebSocketDisconnect:
        manager.disconnect(meeting_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error in room {meeting_id}: {e}")
        manager.disconnect(meeting_id, websocket)
