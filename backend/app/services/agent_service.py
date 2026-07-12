import logging
import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Dict
try:
    from bson import ObjectId
except ImportError:
    class ObjectId:
        def __init__(self, val=None):
            self.val = val or "000000000000000000000000"
        def __str__(self):
            return str(self.val)


from app.core.config import settings
from app.db.mongo import get_db
from app.models.note import NoteSection
from app.models.task import ActionItemOut

logger = logging.getLogger("app.services.agent")

def generate_mock_notes(title: str = "Web Application Pipelines") -> List[NoteSection]:
    """Generates styled study notes with embedded Mermaid diagrams for mock fallback."""
    return [
        NoteSection(
            heading=f"Introduction to {title}",
            bullets=[
                "Discussed modern multi-layer pipeline architecture for classroom meetings.",
                "Explored real-time transcription parsing to automate student workflows.",
                "RAG context ensures continuity by retrieving context from past class lectures."
            ]
        ),
        NoteSection(
            heading="Authentication Flow & Database Schema",
            bullets=[
                "User registration POSTs data containing email, hashed password, and role to '/api/auth/register'.",
                "Password hashed using bcrypt securely on the FastAPI server before saving.",
                "MongoDB records details under 'users' collection; JWT returned to client for local storage."
            ],
            diagramMermaid="""graph TD
    Client[React Client] -->|1. Register Request| Server[FastAPI Server]
    Server -->|2. Hash Password| Bcrypt[Bcrypt Hash]
    Server -->|3. Save Document| Mongo[(MongoDB)]
    Server -->|4. Return JWT Token| Client
    style Client fill:#3b82f6,stroke:#1d4ed8,stroke-width:2px,color:#fff
    style Server fill:#10b981,stroke:#047857,stroke-width:2px,color:#fff
    style Mongo fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#fff"""
        ),
        NoteSection(
            heading="Class Assignments & Project Allocations",
            bullets=[
                "Alex is assigned the React frontend scaffold using shadcn/ui (Due: July 18).",
                "Chloe is responsible for JWT login endpoints and MongoDB integration (Due: July 20).",
                "Dan will build the Notion/Jira sync and ReportLab handwriting PDF exporter (Due: July 22)."
            ]
        )
    ]

def parse_llm_json(response_text: str) -> dict:
    """Attempts to find and parse JSON inside LLM outputs."""
    # Find anything between ```json and ```
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except Exception:
            pass
            
    # Try parsing whole text
    try:
        return json.loads(response_text.strip())
    except Exception:
        pass
        
    # Try parsing any {} block
    brace_match = re.search(r"(\{.*?\})", response_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except Exception:
            pass
            
    raise ValueError("Failed to extract valid JSON from LLM response.")

async def run_agent_notes_tasks(meeting_id: str, transcript: str, rag_context: str) -> Tuple[List[NoteSection], List[dict]]:
    """
    Invokes LLM to construct study notes, diagram code, and action items.
    Returns:
        tuple (list_of_NoteSections, list_of_action_items)
    """
    logger.info("Invoking AI Agent to analyze transcript and extract data...")
    
    db = get_db()
    meeting_title = "Class Session"
    
    # Try fetching meeting title
    if db is not None:
        try:
            from bson import ObjectId
            m = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
            if m:
                meeting_title = m.get("title", meeting_title)
        except Exception:
            pass
            
    # Check mock mode
    if settings.USE_MOCK_SERVICES or (not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY):
        logger.info("Using simulation mode for Agent service.")
        note_sections = generate_mock_notes(meeting_title)
        
        # Match students in system if possible, or use raw names
        alex_id = None
        chloe_id = None
        dan_id = None
        
        # Look for users named Alex, Chloe, Dan
        if db is not None:
            try:
                cursor = db.users.find({"name": {"$in": ["Alex", "Chloe", "Dan"]}})
                async for u in cursor:
                    name_lower = u["name"].lower()
                    if "alex" in name_lower:
                        alex_id = str(u["_id"])
                    elif "chloe" in name_lower:
                        chloe_id = str(u["_id"])
                    elif "dan" in name_lower:
                        dan_id = str(u["_id"])
            except Exception:
                pass
                
        now = datetime.now(timezone.utc)
        action_items = [
            {
                "meetingId": meeting_id,
                "description": "Create React Vite scaffold with TailwindCSS and shadcn/ui components.",
                "assigneeId": alex_id,
                "assigneeName": "Alex",
                "dueDate": now + timedelta(days=7),
                "status": "pending",
                "syncedTo": None,
                "externalTaskId": None
            },
            {
                "meetingId": meeting_id,
                "description": "Create FastAPI auth register and login endpoints with Motor MongoDB wrapper.",
                "assigneeId": chloe_id,
                "assigneeName": "Chloe",
                "dueDate": now + timedelta(days=9),
                "status": "pending",
                "syncedTo": None,
                "externalTaskId": None
            },
            {
                "meetingId": meeting_id,
                "description": "Integrate Notion database page builder and ReportLab handwriting PDF exporter.",
                "assigneeId": dan_id,
                "assigneeName": "Dan",
                "dueDate": now + timedelta(days=11),
                "status": "pending",
                "syncedTo": None,
                "externalTaskId": None
            }
        ]
        
        # Save notes and action items in DB
        await save_agent_outputs_to_db(meeting_id, note_sections, action_items)
        return note_sections, action_items

    # LLM execution (Gemini or OpenAI)
    prompt = f"""
    You are an AI Class Assistant. Analyze this class transcript and past class context.
    Generate a detailed markdown study note for the students and extract a list of action items.
    
    Transcript:
    \"\"\"{transcript}\"\"\"
    
    Past Context:
    \"\"\"{rag_context}\"\"\"
    
    Your output MUST be a JSON object inside a ```json ``` block with this exact format:
    {{
      "sections": [
        {{
          "heading": "Section Heading",
          "bullets": [
            "Bullet point 1 detailing concepts discussed",
            "Bullet point 2 detailing technical aspects"
          ],
          "diagramMermaid": "graph TD\\n  ... (optional Mermaid flowchart code if relevant to the concepts)"
        }}
      ],
      "action_items": [
        {{
          "description": "Clear actionable assignment description",
          "assigneeName": "Name of student/owner",
          "dueDateDaysFromNow": 7
        }}
      ]
    }}
    
    Make the notes structured, comprehensive, and clear. If a database sequence, network packet flow, or setup process is mentioned, write a beautiful Mermaid graph.
    """
    
    try:
        llm_response = ""
        if settings.GEMINI_API_KEY:
            logger.info("Calling Gemini API...")
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            llm_response = response.text
        elif settings.OPENAI_API_KEY:
            logger.info("Calling OpenAI API...")
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            llm_response = response.choices[0].message.content
            
        logger.info("Parsing LLM response payload...")
        data = parse_llm_json(llm_response)
        
        # Construct NoteSections
        note_sections = []
        for s in data.get("sections", []):
            note_sections.append(NoteSection(
                heading=s.get("heading", "Untitled Section"),
                bullets=s.get("bullets", []),
                diagramMermaid=s.get("diagramMermaid")
            ))
            
        if not note_sections:
            note_sections = generate_mock_notes(meeting_title)
            
        # Parse action items
        action_items = []
        now = datetime.now(timezone.utc)
        for t in data.get("action_items", []):
            assignee_name = t.get("assigneeName")
            days = t.get("dueDateDaysFromNow", 5)
            
            # Look up assignee ID from name
            assignee_id = None
            if db is not None and assignee_name:
                user_doc = await db.users.find_one({"name": {"$regex": f"^{assignee_name}$", "$options": "i"}})
                if user_doc:
                    assignee_id = str(user_doc["_id"])
                    
            action_items.append({
                "meetingId": meeting_id,
                "description": t.get("description", "Assignment"),
                "assigneeId": assignee_id,
                "assigneeName": assignee_name,
                "dueDate": now + timedelta(days=days),
                "status": "pending",
                "syncedTo": None,
                "externalTaskId": None
            })
            
        await save_agent_outputs_to_db(meeting_id, note_sections, action_items)
        return note_sections, action_items
        
    except Exception as e:
        logger.error(f"Failed calling LLM Agent service: {e}. Falling back to simulation.", exc_info=True)
        # Fall back to simulation
        return await run_agent_notes_tasks(meeting_id, transcript, rag_context)

async def save_agent_outputs_to_db(meeting_id: str, note_sections: List[NoteSection], action_items: List[dict]):
    db = get_db()
    
    # Save notes
    note_payload = {
        "meetingId": meeting_id,
        "structuredContent": [s.model_dump() for s in note_sections],
        "pdfUrl": f"/api/notes/{meeting_id}/pdf",
        "generatedAt": datetime.now(timezone.utc)
    }
    
    # Save to local in-memory as well
    from app.routers.notes import IN_MEMORY_NOTES
    from app.routers.tasks import IN_MEMORY_TASKS
    
    note_id_str = f"note_{meeting_id}"
    if db is not None:
        try:
            # Delete old note if exists
            await db.notes.delete_many({"meetingId": meeting_id})
            res = await db.notes.insert_one(note_payload)
            note_id_str = str(res.inserted_id)
        except Exception as e:
            logger.error(f"Mongo notes write failed: {e}")
            
    note_payload["id"] = note_id_str
    IN_MEMORY_NOTES[meeting_id] = note_payload
    
    # Save tasks
    if db is not None:
        try:
            await db.action_items.delete_many({"meetingId": meeting_id})
        except Exception:
            pass
            
    for i, item in enumerate(action_items):
        task_id_str = f"task_{meeting_id}_{i}"
        
        if db is not None:
            try:
                res = await db.action_items.insert_one(item.copy())
                task_id_str = str(res.inserted_id)
            except Exception as e:
                logger.error(f"Mongo task write failed: {e}")
                
        item["id"] = task_id_str
        IN_MEMORY_TASKS[task_id_str] = item
