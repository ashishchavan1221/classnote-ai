import os
import sys
import asyncio
from datetime import datetime, timezone

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.core.security import hash_password, verify_password
from app.db.vector_store import get_vector_store
from app.services.transcription_service import transcribe_meeting
from app.services.rag_service import run_meeting_rag
from app.services.agent_service import run_agent_notes_tasks
from app.services.pdf_service import generate_meeting_pdf

async def test_auth():
    print("[TEST] Running Authentication Security check...")
    pwd = "secretpassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) == True
    assert verify_password("wrong_pwd", hashed) == False
    print("[TEST] Security password validation succeeded!")

async def test_vector_store():
    print("[TEST] Running Vector DB check...")
    vs = get_vector_store()
    collection = vs.get_or_create_collection("test_collection")
    collection.add(
        documents=["FastAPI is a modern web framework.", "React Vite is for frontend assets."],
        ids=["doc1", "doc2"],
        metadatas=[{"tech": "python"}, {"tech": "js"}]
    )
    
    # Query FastAPI
    res = collection.query(query_texts=["FastAPI"], n_results=1)
    assert "FastAPI" in res["documents"][0][0]
    print("[TEST] Vector Store search indexing succeeded!")

async def test_ai_pipeline():
    print("[TEST] Running AI Pipeline check...")
    meeting_id = "test_meeting_999"
    
    # Transcription
    transcript, segments = await transcribe_meeting(meeting_id)
    assert len(segments) > 0
    assert "Teacher" in segments[0]["speaker"]
    print("[TEST] Transcription mock compiler succeeded!")
    
    # RAG
    rag_context = await run_meeting_rag(meeting_id, transcript, segments)
    assert len(rag_context) > 0
    print("[TEST] RAG continuity queries succeeded!")
    
    # Agent notes
    notes, tasks = await run_agent_notes_tasks(meeting_id, transcript, rag_context)
    assert len(notes) > 0
    assert len(tasks) > 0
    print("[TEST] Agent notes and tasks extraction succeeded!")
    
    # PDF generation
    pdf_path = await generate_meeting_pdf(meeting_id, notes)
    assert os.path.exists(pdf_path) == True
    print(f"[TEST] ReportLab handwriting PDF compilation succeeded! Path: {pdf_path}")

async def main():
    print("=================== STARTING BACKEND TESTS ===================")
    await test_auth()
    await test_vector_store()
    await test_ai_pipeline()
    print("=================== ALL TESTS PASSED SUCCESSFULLY! ===================")

if __name__ == "__main__":
    asyncio.run(main())
