import logging
import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse
from bson import ObjectId

from app.db.mongo import get_db
from app.models.note import NoteOut, NoteSection
from app.routers.auth import get_current_user

logger = logging.getLogger("app.routers.notes")
router = APIRouter(prefix="/api/notes", tags=["Notes"])

# Fallback in-memory storage for notes
IN_MEMORY_NOTES = {}

@router.get("/{meetingId}", response_model=NoteOut)
async def get_notes(meetingId: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    note_doc = None
    
    if db is not None:
        try:
            note_doc = await db.notes.find_one({"meetingId": meetingId})
            if note_doc:
                note_doc["id"] = str(note_doc["_id"])
        except Exception as e:
            logger.error(f"Failed to fetch note from mongo: {e}")
            
    if not note_doc and meetingId in IN_MEMORY_NOTES:
        note_doc = IN_MEMORY_NOTES[meetingId]
        
    if not note_doc:
        # Check if meeting exists and has ended. If it has, create a default notes document on the fly so the user has something to view.
        from app.routers.meetings import IN_MEMORY_MEETINGS
        meeting = None
        if db is not None:
            try:
                meeting = await db.meetings.find_one({"_id": ObjectId(meetingId)})
            except Exception:
                pass
        if not meeting and meetingId in IN_MEMORY_MEETINGS:
            meeting = IN_MEMORY_MEETINGS[meetingId]
            
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found.")
            
        # Create a mock note if meeting has completed and pipeline hasn't run or is mocked
        from datetime import datetime, timezone
        from app.services.agent_service import generate_mock_notes
        
        mock_sections = generate_mock_notes(meeting.get("title", "Meeting"))
        note_doc = {
            "id": f"note_{meetingId}",
            "meetingId": meetingId,
            "structuredContent": [s.model_dump() for s in mock_sections],
            "pdfUrl": f"/api/notes/{meetingId}/pdf",
            "generatedAt": datetime.now(timezone.utc)
        }
        IN_MEMORY_NOTES[meetingId] = note_doc
        
        # Save to Mongo if possible
        if db is not None:
            try:
                # Remove mock id from payload before saving to mongo
                mongo_payload = note_doc.copy()
                del mongo_payload["id"]
                res = await db.notes.insert_one(mongo_payload)
                note_doc["id"] = str(res.inserted_id)
                IN_MEMORY_NOTES[meetingId] = note_doc
            except Exception:
                pass

    return NoteOut(
        id=note_doc["id"],
        meetingId=note_doc["meetingId"],
        structuredContent=[NoteSection(**s) for s in note_doc["structuredContent"]],
        pdfUrl=note_doc.get("pdfUrl"),
        generatedAt=note_doc["generatedAt"]
    )

@router.get("/{meetingId}/pdf")
async def download_notes_pdf(meetingId: str, current_user: dict = Depends(get_current_user)):
    # Look for notes
    db = get_db()
    note_doc = None
    if db is not None:
        try:
            note_doc = await db.notes.find_one({"meetingId": meetingId})
        except Exception:
            pass
    if not note_doc and meetingId in IN_MEMORY_NOTES:
        note_doc = IN_MEMORY_NOTES[meetingId]
        
    pdf_filename = f"notes_{meetingId}.pdf"
    pdf_path = os.path.join(os.getcwd(), "storage", "pdfs", pdf_filename)
    
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename=pdf_filename, media_type="application/pdf")
        
    # Generate the PDF file on the fly if it does not exist
    from app.services.pdf_service import generate_meeting_pdf
    
    sections = []
    if note_doc:
        sections = [NoteSection(**s) for s in note_doc["structuredContent"]]
    else:
        from app.services.agent_service import generate_mock_notes
        sections = generate_mock_notes("Sample Meeting Notes")
        
    generated_pdf_path = await generate_meeting_pdf(meetingId, sections)
    if generated_pdf_path and os.path.exists(generated_pdf_path):
        return FileResponse(generated_pdf_path, filename=pdf_filename, media_type="application/pdf")
        
    raise HTTPException(status_code=404, detail="PDF notes file could not be generated.")
