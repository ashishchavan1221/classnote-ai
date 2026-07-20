import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
try:
    from bson import ObjectId
except ImportError:
    class ObjectId:
        def __init__(self, val=None):
            self.val = val or "000000000000000000000000"
        def __str__(self):
            return str(self.val)


from app.db.mongo import get_db
from app.models.meeting import MeetingCreate, MeetingOut
from app.routers.auth import get_current_user

logger = logging.getLogger("app.routers.meetings")
router = APIRouter(prefix="/api/meetings", tags=["Meetings"])

# In-memory meetings storage fallback
IN_MEMORY_MEETINGS: Dict[str, dict] = {}

# We import pipeline functions dynamically inside the end_meeting handler to avoid circular imports.

async def run_pipeline_orchestrator(meeting_id: str):
    """Triggers the full AI meeting processing pipeline in the background."""
    from app.services.transcription_service import transcribe_meeting
    from app.services.rag_service import run_meeting_rag
    from app.services.agent_service import run_agent_notes_tasks
    from app.services.pdf_service import generate_meeting_pdf
    from app.services.task_sync_service import auto_sync_meeting_tasks
    
    db = get_db()
    logger.info(f"Starting post-meeting AI orchestrator pipeline for meeting {meeting_id}")
    
    try:
        # Step 1: Transcribe the audio recording
        transcript_text, segments = await transcribe_meeting(meeting_id)
        
        # Step 2 & 3: Run RAG retrieval & update vector store
        rag_context = await run_meeting_rag(meeting_id, transcript_text, segments)
        
        # Step 4: Run Agent notes and action item generator
        note_data, action_items = await run_agent_notes_tasks(meeting_id, transcript_text, rag_context)
        
        # Step 5: Build handwriting-style PDF
        pdf_url = await generate_meeting_pdf(meeting_id, note_data)
        
        # Update PDF URL in notes
        if db is not None:
            await db.notes.update_one({"meetingId": meeting_id}, {"$set": {"pdfUrl": pdf_url}})
            await db.meetings.update_one({"_id": ObjectId(meeting_id)}, {"$set": {"recordingUrl": pdf_url.replace(".pdf", "_rec.mp3") if pdf_url else None}})
        
        # Step 6: Push action items to Notion / Jira
        await auto_sync_meeting_tasks(meeting_id, action_items)
        
        logger.info(f"AI Orchestrator pipeline successfully finished for meeting {meeting_id}!")
    except Exception as e:
        logger.error(f"Error executing AI Orchestrator pipeline for meeting {meeting_id}: {e}", exc_info=True)

@router.get("", response_model=List[MeetingOut])
async def list_meetings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    meetings_list = []
    
    if db is not None:
        try:
            # Query based on role
            query = {}
            if user_role == "student":
                # Students can see meetings where they are in participantIds
                query = {"participantIds": user_id}
            else:
                # Teachers see meetings they host
                query = {"hostId": user_id}
                
            cursor = db.meetings.find(query).sort("scheduledAt", -1)
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                meetings_list.append(doc)
        except Exception as e:
            logger.error(f"Database list_meetings error: {e}")
            
    # Fallback/merge with in-memory storage
    if not meetings_list:
        for m in IN_MEMORY_MEETINGS.values():
            if user_role == "student":
                if user_id in m["participantIds"]:
                    meetings_list.append(m)
            else:
                if m["hostId"] == user_id:
                    meetings_list.append(m)
                    
    # Format and return MeetingOut models safely
    result = []
    for m in meetings_list:
        result.append(MeetingOut(
            id=m["id"],
            title=m["title"],
            description=m.get("description"),
            hostId=m["hostId"],
            participantIds=m.get("participantIds", []),
            scheduledAt=m["scheduledAt"],
            startedAt=m.get("startedAt"),
            endedAt=m.get("endedAt"),
            meetingLink=m["meetingLink"],
            status=m["status"],
            recordingUrl=m.get("recordingUrl"),
            transcriptId=m.get("transcriptId")
        ))
        
    return result

@router.post("", response_model=MeetingOut)
async def create_meeting(meeting_data: MeetingCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers/mentors can schedule meetings."
        )
        
    db = get_db()
    meeting_id_str = str(uuid.uuid4())
    jitsi_room_name = f"meeting-notes-pipeline-{uuid.uuid4().hex[:10]}"
    meeting_link = f"https://jitsi.riot.im/{jitsi_room_name}"
    
    # Resolve participant emails to IDs
    participant_ids = []
    if meeting_data.participantEmails:
        if db is not None:
            try:
                emails = [e.lower() for e in meeting_data.participantEmails]
                cursor = db.users.find({"email": {"$in": emails}})
                async for u in cursor:
                    participant_ids.append(str(u["_id"]))
            except Exception:
                pass
        
        # Check in memory users fallback
        from app.routers.auth import IN_MEMORY_USERS
        for u_id, u_info in IN_MEMORY_USERS.items():
            if u_info["email"] in meeting_data.participantEmails and u_id not in participant_ids:
                participant_ids.append(u_id)

    meeting_dict = {
        "title": meeting_data.title,
        "description": meeting_data.description,
        "hostId": current_user["id"],
        "participantIds": participant_ids,
        "scheduledAt": meeting_data.scheduledAt,
        "startedAt": None,
        "endedAt": None,
        "meetingLink": meeting_link,
        "status": "scheduled",
        "recordingUrl": None,
        "transcriptId": None
    }
    
    if db is not None:
        try:
            # We can force insert custom string id or let mongo assign ObjectId. Let's let mongo assign ObjectId
            res = await db.meetings.insert_one(meeting_dict)
            meeting_id_str = str(res.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert meeting to db: {e}")
            
    meeting_dict["id"] = meeting_id_str
    IN_MEMORY_MEETINGS[meeting_id_str] = meeting_dict
    
    return MeetingOut(
        id=meeting_id_str,
        title=meeting_dict["title"],
        description=meeting_dict.get("description"),
        hostId=meeting_dict["hostId"],
        participantIds=meeting_dict["participantIds"],
        scheduledAt=meeting_dict["scheduledAt"],
        startedAt=meeting_dict["startedAt"],
        endedAt=meeting_dict["endedAt"],
        meetingLink=meeting_dict["meetingLink"],
        status=meeting_dict["status"],
        recordingUrl=meeting_dict.get("recordingUrl"),
        transcriptId=meeting_dict.get("transcriptId")
    )

@router.get("/{id}", response_model=MeetingOut)
async def get_meeting(id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    meeting = None
    
    if db is not None:
        try:
            meeting = await db.meetings.find_one({"_id": ObjectId(id)})
            if meeting:
                meeting["id"] = str(meeting["_id"])
        except Exception:
            pass
            
    if not meeting and id in IN_MEMORY_MEETINGS:
        meeting = IN_MEMORY_MEETINGS[id]
        
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found."
        )
        
    return MeetingOut(
        id=meeting["id"],
        title=meeting["title"],
        description=meeting.get("description"),
        hostId=meeting["hostId"],
        participantIds=meeting.get("participantIds", []),
        scheduledAt=meeting["scheduledAt"],
        startedAt=meeting.get("startedAt"),
        endedAt=meeting.get("endedAt"),
        meetingLink=meeting["meetingLink"],
        status=meeting["status"],
        recordingUrl=meeting.get("recordingUrl"),
        transcriptId=meeting.get("transcriptId")
    )

@router.post("/{id}/start", response_model=MeetingOut)
async def start_meeting(id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    meeting = None
    
    if db is not None:
        try:
            meeting = await db.meetings.find_one({"_id": ObjectId(id)})
        except Exception:
            pass
            
    if not meeting and id in IN_MEMORY_MEETINGS:
        meeting = IN_MEMORY_MEETINGS[id]
        
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
        
    if meeting["hostId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the host can start the meeting.")
        
    now = datetime.now(timezone.utc)
    meeting["startedAt"] = now
    meeting["status"] = "live"
    
    if db is not None:
        try:
            await db.meetings.update_one(
                {"_id": ObjectId(id)},
                {"$set": {"startedAt": now, "status": "live"}}
            )
            # Re-fetch
            refetched = await db.meetings.find_one({"_id": ObjectId(id)})
            refetched["id"] = str(refetched["_id"])
            meeting = refetched
        except Exception:
            pass
            
    IN_MEMORY_MEETINGS[id] = meeting
    
    return MeetingOut(
        id=id,
        title=meeting["title"],
        description=meeting.get("description"),
        hostId=meeting["hostId"],
        participantIds=meeting.get("participantIds", []),
        scheduledAt=meeting["scheduledAt"],
        startedAt=meeting.get("startedAt"),
        endedAt=meeting.get("endedAt"),
        meetingLink=meeting["meetingLink"],
        status=meeting["status"]
    )

@router.post("/{id}/end", response_model=MeetingOut)
async def end_meeting(id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    db = get_db()
    meeting = None
    
    if db is not None:
        try:
            meeting = await db.meetings.find_one({"_id": ObjectId(id)})
        except Exception:
            pass
            
    if not meeting and id in IN_MEMORY_MEETINGS:
        meeting = IN_MEMORY_MEETINGS[id]
        
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
        
    if meeting["hostId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the host can end the meeting.")
        
    now = datetime.now(timezone.utc)
    meeting["endedAt"] = now
    meeting["status"] = "completed"
    
    if db is not None:
        try:
            await db.meetings.update_one(
                {"_id": ObjectId(id)},
                {"$set": {"endedAt": now, "status": "completed"}}
            )
            refetched = await db.meetings.find_one({"_id": ObjectId(id)})
            refetched["id"] = str(refetched["_id"])
            meeting = refetched
        except Exception:
            pass
            
    IN_MEMORY_MEETINGS[id] = meeting
    
    # Trigger AI processing orchestrator pipeline in the background!
    background_tasks.add_task(run_pipeline_orchestrator, id)
    
    return MeetingOut(
        id=id,
        title=meeting["title"],
        description=meeting.get("description"),
        hostId=meeting["hostId"],
        participantIds=meeting.get("participantIds", []),
        scheduledAt=meeting["scheduledAt"],
        startedAt=meeting.get("startedAt"),
        endedAt=meeting.get("endedAt"),
        meetingLink=meeting["meetingLink"],
        status=meeting["status"]
    )
