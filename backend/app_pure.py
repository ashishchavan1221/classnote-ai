import os
import re
import json
import uuid
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Import pymongo for MongoDB connection
from pymongo import MongoClient

# Load environment configuration manually
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
MONGODB_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "meeting_notes_db"
GEMINI_API_KEY = ""

mongodb_configured = False

if os.path.exists(ENV_FILE):
    try:
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    if key.strip() == "MONGODB_URI":
                        MONGODB_URI = val.strip()
                        # If customized, set configured flag
                        if MONGODB_URI and MONGODB_URI != "mongodb://localhost:27017":
                            mongodb_configured = True
                    elif key.strip() == "MONGO_DB_NAME":
                        MONGO_DB_NAME = val.strip()
                    elif key.strip() == "GEMINI_API_KEY":
                        GEMINI_API_KEY = val.strip()
    except Exception as e:
        print(f"[Database] Error parsing env file: {e}")

def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k.strip() == "GEMINI_API_KEY":
                            val = v.strip()
                            if val:
                                key = val
        except Exception:
            pass
    return key

def call_gemini_with_fallback(prompt_or_parts):
    key = get_gemini_api_key()
    if not key:
        raise ValueError("No GEMINI_API_KEY found")
    import google.generativeai as genai
    genai.configure(api_key=key)
    candidate_models = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash"
    ]
    last_err = None
    for model_name in candidate_models:
        try:
            m = genai.GenerativeModel(model_name)
            res = m.generate_content(prompt_or_parts)
            if res and res.text:
                return res.text
        except Exception as err:
            last_err = err
            print(f"[Gemini] Candidate model '{model_name}' failed: {err}")
    raise last_err or Exception("All Gemini candidate models failed")

mongo_client = None
mongo_db = None
use_mongodb = False
connection_error_message = ""

def check_mongodb_connection():
    global mongo_client, mongo_db, use_mongodb, connection_error_message
    try:
        if not mongo_client:
            mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        # Simple check to see if database connection is alive
        mongo_client.admin.command('ping')
        mongo_db = mongo_client[MONGO_DB_NAME]
        use_mongodb = True
        connection_error_message = ""
        return True
    except Exception as e:
        use_mongodb = False
        connection_error_message = str(e)
        return False

# Initial connection check
print(f"[Database] Connecting to MongoDB at {MONGODB_URI}...")
check_mongodb_connection()
if use_mongodb:
    print(f"[Database] Successfully connected to MongoDB Atlas. Database: {MONGO_DB_NAME}")
else:
    if mongodb_configured:
        print(f"[Database] WARNING: MongoDB Atlas connection failed. Error: {connection_error_message}")
        print("[Database] Backend will require a successful reconnection for registration/login operations.")
    else:
        print("[Database] MongoDB Atlas not configured or not running. Operating in local JSON fallback mode.")

def ensure_db_ready(handler_instance):
    global use_mongodb
    if mongodb_configured:
        if not use_mongodb:
            check_mongodb_connection()
        if not use_mongodb:
            handler_instance.send_error_json(
                f"MongoDB connection failed. Please ensure your internet is connected and your IP is whitelisted on MongoDB Atlas. Details: {connection_error_message}",
                503
            )
            return False
    return True

# Fallback Local JSON DB Config
DB_FILE = os.path.join(BACKEND_DIR, "storage", "db.json")
os.makedirs(os.path.join(BACKEND_DIR, "storage", "pdfs"), exist_ok=True)
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": {}, "meetings": {}, "notes": {}, "tasks": {}}, f)

def read_json_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "meetings": {}, "notes": {}, "tasks": {}}

def write_json_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing local DB: {e}")

# Auto-seed demo users if they don't exist
def seed_demo_users():
    teacher_user = {
        "id": "teacher_demo_id_12345678",
        "name": "Professor Jane",
        "email": "teacher@classnote.com",
        "password": "password123",
        "role": "teacher",
        "institution": "ClassNote Academy",
        "connectedApps": {
            "notion": {"token": None, "databaseId": None},
            "jira": {"host": None, "email": None, "token": None, "projectKey": None}
        }
    }
    student_user = {
        "id": "student_demo_id_87654321",
        "name": "Alex Student",
        "email": "student@classnote.com",
        "password": "password123",
        "role": "student",
        "institution": "ClassNote Academy",
        "connectedApps": {
            "notion": {"token": None, "databaseId": None},
            "jira": {"host": None, "email": None, "token": None, "projectKey": None}
        }
    }
    
    if use_mongodb:
        try:
            mongo_db.users.update_one({"email": teacher_user["email"]}, {"$set": teacher_user}, upsert=True)
            mongo_db.users.update_one({"email": student_user["email"]}, {"$set": student_user}, upsert=True)
            print("[Seeder] Successfully verified/seeded demo users in MongoDB Atlas.")
        except Exception as seed_err:
            print(f"[Seeder] MongoDB Atlas seeding failed: {seed_err}")
    else:
        db = read_json_db()
        db["users"][teacher_user["id"]] = teacher_user
        db["users"][student_user["id"]] = student_user
        write_json_db(db)
        print("[Seeder] Successfully verified/seeded demo users in local JSON database.")

seed_demo_users()

# MongoDB Helper CRUD wrappers
def get_user(user_id):
    if use_mongodb:
        user = mongo_db.users.find_one({"id": user_id})
        if user:
            user["_id"] = str(user["_id"])
        return user
    else:
        return read_json_db()["users"].get(user_id)

def save_user(user):
    if use_mongodb:
        user_to_save = dict(user)
        user_to_save.pop("_id", None)
        mongo_db.users.update_one({"id": user["id"]}, {"$set": user_to_save}, upsert=True)
    else:
        db = read_json_db()
        db["users"][user["id"]] = user
        write_json_db(db)

def get_user_by_email(email):
    if use_mongodb:
        user = mongo_db.users.find_one({"email": email.lower()})
        if user:
            user["_id"] = str(user["_id"])
        return user
    else:
        for u in read_json_db()["users"].values():
            if u["email"] == email.lower():
                return u
        return None

def sanitize_note_sections(sections):
    if not sections or not get_gemini_api_key():
        return sections
    sanitized = []
    for section in sections:
        sec_copy = dict(section)
        bullets = sec_copy.get("bullets", [])
        clean_bullets = [b for b in bullets if not (isinstance(b, str) and b.startswith("[NOTE: Please add a GEMINI_API_KEY"))]
        sec_copy["bullets"] = clean_bullets
        sanitized.append(sec_copy)
    return sanitized

def list_meetings_for_user(user):
    if use_mongodb:
        query = {}
        if user["role"] == "student":
            query = {
                "$or": [
                    {"participantIds": user["id"]},
                    {"participantIds": {"$size": 0}},
                    {"participantIds": {"$exists": False}},
                    {"participantIds": None}
                ]
            }
        else:
            query = {"hostId": user["id"]}
        meetings = list(mongo_db.meetings.find(query))
        for m in meetings:
            m["_id"] = str(m["_id"])
            if "structuredContent" in m:
                m["structuredContent"] = sanitize_note_sections(m["structuredContent"])
        return meetings
    else:
        db = read_json_db()
        meetings_list = []
        for m in db["meetings"].values():
            if user["role"] == "student":
                p_ids = m.get("participantIds", [])
                if not p_ids or user["id"] in p_ids:
                    m_copy = dict(m)
                    if "structuredContent" in m_copy:
                        m_copy["structuredContent"] = sanitize_note_sections(m_copy["structuredContent"])
                    meetings_list.append(m_copy)
            else:
                if m["hostId"] == user["id"]:
                    m_copy = dict(m)
                    if "structuredContent" in m_copy:
                        m_copy["structuredContent"] = sanitize_note_sections(m_copy["structuredContent"])
                    meetings_list.append(m_copy)
        return meetings_list

def save_meeting(meeting):
    if use_mongodb:
        meeting_to_save = dict(meeting)
        meeting_to_save.pop("_id", None)
        mongo_db.meetings.update_one({"id": meeting["id"]}, {"$set": meeting_to_save}, upsert=True)
    else:
        db = read_json_db()
        db["meetings"][meeting["id"]] = meeting
        write_json_db(db)

def get_meeting(meeting_id):
    if use_mongodb:
        m = mongo_db.meetings.find_one({"id": meeting_id})
        if m:
            m["_id"] = str(m["_id"])
    else:
        m = read_json_db()["meetings"].get(meeting_id)
    if m and "structuredContent" in m:
        m["structuredContent"] = sanitize_note_sections(m["structuredContent"])
    return m

def get_notes(meeting_id):
    if use_mongodb:
        n = mongo_db.notes.find_one({"meetingId": meeting_id})
        if n:
            n["_id"] = str(n["_id"])
    else:
        n = read_json_db()["notes"].get(meeting_id)
    if n and "structuredContent" in n:
        n["structuredContent"] = sanitize_note_sections(n["structuredContent"])
    return n

def save_notes(notes_doc):
    # Always fully replace existing notes — never keep stale content
    if use_mongodb:
        notes_to_save = dict(notes_doc)
        notes_to_save.pop("_id", None)
        mongo_db.notes.delete_many({"meetingId": notes_doc["meetingId"]})
        mongo_db.notes.insert_one(notes_to_save)
    else:
        db = read_json_db()
        db["notes"][notes_doc["meetingId"]] = notes_doc
        write_json_db(db)

def delete_notes(meeting_id):
    """Delete all notes for a meeting so stale data is never returned."""
    if use_mongodb:
        mongo_db.notes.delete_many({"meetingId": meeting_id})
    else:
        db = read_json_db()
        db["notes"].pop(meeting_id, None)
        write_json_db(db)

def list_tasks_for_user(user):
    if use_mongodb:
        query = {}
        if user["role"] == "student":
            query = {"assigneeId": user["id"]}
        tasks = list(mongo_db.tasks.find(query))
        for t in tasks:
            t["_id"] = str(t["_id"])
            meeting = mongo_db.meetings.find_one({"id": t["meetingId"]})
            t["meetingTitle"] = meeting["title"] if meeting else "Class Session"
        return tasks
    else:
        db = read_json_db()
        tasks_list = []
        for t in db["tasks"].values():
            if user["role"] == "student" and t.get("assigneeId") != user["id"]:
                continue
            meeting = db["meetings"].get(t["meetingId"])
            t["meetingTitle"] = meeting["title"] if meeting else "Class Session"
            tasks_list.append(t)
        return tasks_list

def save_task(task):
    if use_mongodb:
        task_to_save = dict(task)
        task_to_save.pop("_id", None)
        mongo_db.tasks.update_one({"id": task["id"]}, {"$set": task_to_save}, upsert=True)
    else:
        db = read_json_db()
        db["tasks"][task["id"]] = task
        write_json_db(db)

def get_task(task_id):
    if use_mongodb:
        t = mongo_db.tasks.find_one({"id": task_id})
        if t:
            t["_id"] = str(t["_id"])
        return t
    else:
        return read_json_db()["tasks"].get(task_id)


class PureAPIRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def get_post_data(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            return json.loads(post_data.decode('utf-8'))
        except Exception:
            return {}

    def authenticate(self):
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        token = auth_header.split(' ')[1]
        return get_user(token)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_json(self, message, status=400):
        self.send_json({"detail": message}, status)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # GET /api/status
        if path == "/api/status":
            if mongodb_configured and not use_mongodb:
                check_mongodb_connection()
            return self.send_json({
                "use_mongodb": use_mongodb,
                "mongodb_configured": mongodb_configured,
                "database_name": MONGO_DB_NAME if use_mongodb else "local_json",
                "error_message": connection_error_message
            })

        # GET /api/auth/me
        elif path == "/api/auth/me":
            user = self.authenticate()
            if not user:
                return self.send_error_json("Session expired or invalid token", 401)
            
            return self.send_json({
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "institution": user.get("institution"),
                "connectedApps": user.get("connectedApps", {
                    "notion": {"token": None, "databaseId": None},
                    "jira": {"host": None, "email": None, "token": None, "projectKey": None}
                })
            })

        # GET /api/meetings
        elif path == "/api/meetings":
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
            return self.send_json(list_meetings_for_user(user))

        # GET /api/meetings/{id}
        elif path.startswith("/api/meetings/"):
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            meeting_id = path.split("/")[-1]
            meeting = get_meeting(meeting_id)
            if not meeting:
                return self.send_error_json("Meeting not found", 404)
            return self.send_json(meeting)

        # GET /api/notes/{meetingId}
        elif path.startswith("/api/notes/") and not path.endswith("/pdf"):
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            meeting_id = path.split("/")[-1]
            note = get_notes(meeting_id)
            
            if not note:
                return self.send_error_json("Notes not yet generated for this session", 404)
                
            return self.send_json(note)

        # GET /api/notes/{meetingId}/pdf
        elif path.startswith("/api/notes/") and path.endswith("/pdf"):
            meeting_id = path.split("/")[-2]
            pdf_path = os.path.join(BACKEND_DIR, "storage", "pdfs", f"notes_{meeting_id}.pdf")
            
            if not os.path.exists(pdf_path):
                with open(pdf_path, "w") as f:
                    f.write("ClassNote Study Guide Fallback: ReportLab compilation omitted on Python 3.14.")
            
            try:
                with open(pdf_path, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f"attachment; filename=notes_{meeting_id}.pdf")
                    self.end_headers()
                    self.wfile.write(f.read())
                    return
            except Exception as e:
                return self.send_error_json(f"Failed to read file: {e}", 500)

        # GET /api/tasks
        elif path == "/api/tasks":
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
            return self.send_json(list_tasks_for_user(user))

        else:
            # Serve frontend static files from frontend/dist
            frontend_dist = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend", "dist"))
            
            # Clean path to prevent traversal vulnerabilities
            normalized_path = path.lstrip("/")
            file_path = os.path.abspath(os.path.join(frontend_dist, normalized_path))
            
            # Prevent path traversal
            if not file_path.startswith(frontend_dist):
                self.send_response(403)
                self.end_headers()
                return
                
            # React Router SPA routing fallback
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                file_path = os.path.join(frontend_dist, "index.html")
                
            if not os.path.exists(file_path):
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Frontend not built. Please run npm run build in the frontend directory.")
                return
                
            # Content type mappings
            content_type = "text/html"
            if file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif file_path.endswith(".svg"):
                content_type = "image/svg+xml"
            elif file_path.endswith(".ico"):
                content_type = "image/x-icon"
            elif file_path.endswith(".json"):
                content_type = "application/json"
                
            try:
                with open(file_path, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    if not file_path.endswith("index.html"):
                        self.send_header("Cache-Control", "public, max-age=31536000")
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_response(500)
                self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.get_post_data()

        # POST /api/auth/register
        if path == "/api/auth/register":
            if not ensure_db_ready(self):
                return
            name = data.get("name")
            email = data.get("email", "").lower()
            password = data.get("password")
            role = data.get("role", "student")
            institution = data.get("institution")
            
            if not name or not email or not password:
                return self.send_error_json("Missing required fields")
                
            existing_user = get_user_by_email(email)
            if existing_user:
                return self.send_error_json("Email already registered")
                    
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "name": name,
                "email": email,
                "password": password,
                "role": role,
                "institution": institution,
                "connectedApps": {
                    "notion": {"token": None, "databaseId": None},
                    "jira": {"host": None, "email": None, "token": None, "projectKey": None}
                }
            }
            
            save_user(user)
            return self.send_json({
                "access_token": user_id,
                "token_type": "bearer"
            })

        # POST /api/auth/login
        elif path == "/api/auth/login":
            if not ensure_db_ready(self):
                return
            email = data.get("email", "").lower()
            password = data.get("password")
            
            user = get_user_by_email(email)
            password_correct = False
            if user:
                stored_password = user.get("password")
                if stored_password is not None:
                    password_correct = (stored_password == password)
                else:
                    stored_hash = user.get("passwordHash")
                    if stored_hash is not None:
                        try:
                            from app.core.security import verify_password
                            password_correct = verify_password(password, stored_hash)
                        except Exception:
                            password_correct = False
            if not user or not password_correct:
                return self.send_error_json("Incorrect email or password", 401)
                
            return self.send_json({
                "access_token": user["id"],
                "token_type": "bearer"
            })

        # POST /api/meetings
        elif path == "/api/meetings":
            user = self.authenticate()
            if not user or user["role"] != "teacher":
                return self.send_error_json("Only teachers can create meetings", 403)
                
            title = data.get("title")
            description = data.get("description")
            scheduled_at = data.get("scheduledAt")
            participant_emails = data.get("participantEmails", [])
            
            if not title or not scheduled_at:
                return self.send_error_json("Missing required fields")
                
            meeting_id = str(uuid.uuid4())
            jitsi_room = f"meeting-notes-pipeline-{uuid.uuid4().hex[:10]}"
            
            # Resolve participant IDs
            participant_ids = []
            for email in participant_emails:
                if email and isinstance(email, str):
                    u = get_user_by_email(email.strip().lower())
                    if u and u["id"] not in participant_ids:
                        participant_ids.append(u["id"])

            meeting = {
                "id": meeting_id,
                "title": title,
                "description": description,
                "hostId": user["id"],
                "participantIds": participant_ids,
                "scheduledAt": scheduled_at,
                "startedAt": None,
                "endedAt": None,
                "meetingLink": f"https://jitsi.riot.im/{jitsi_room}",
                "status": "scheduled",
                "recordingUrl": None,
                "transcriptId": None
            }
            
            save_meeting(meeting)
            return self.send_json(meeting)

        # POST /api/meetings/{id}/start
        elif path.startswith("/api/meetings/") and path.endswith("/start"):
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            meeting_id = path.split("/")[-2]
            meeting = get_meeting(meeting_id)
            if not meeting:
                return self.send_error_json("Meeting not found", 404)
                
            meeting["status"] = "live"
            meeting["startedAt"] = datetime.datetime.now().isoformat()
            save_meeting(meeting)
            return self.send_json(meeting)

        # POST /api/meetings/{id}/end
        elif path.startswith("/api/meetings/") and path.endswith("/end"):
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            meeting_id = path.split("/")[-2]
            meeting = get_meeting(meeting_id)
            if not meeting:
                return self.send_error_json("Meeting not found", 404)
            
            meeting["status"] = "completed"
            meeting["endedAt"] = datetime.datetime.now().isoformat()
            
            # Get real transcript from this specific meeting's recording
            transcript_text = data.get("transcript", "").strip()
            meeting_title = meeting.get("title", "Class Session")
            
            # Decode audio recording if uploaded
            audio_base64 = data.get("audioBase64", "").strip()
            audio_bytes = None
            if audio_base64:
                try:
                    import base64
                    audio_bytes = base64.b64decode(audio_base64)
                    print(f"[Audio] Decoded audio file, size: {len(audio_bytes)} bytes.")
                except Exception as e:
                    print(f"[Audio] Failed to decode base64 audio: {e}")

            # ALWAYS delete old/stale notes first — every meeting gets fresh content
            delete_notes(meeting_id)
            
            # Use Gemini to transcribe the audio if available
            current_gemini_key = get_gemini_api_key()
            if current_gemini_key and audio_bytes:
                try:
                    audio_part = {
                        "mime_type": "audio/webm",
                        "data": audio_bytes
                    }
                    transcribe_prompt = (
                        "Listen to this classroom lecture audio. "
                        "Transcribe the spoken content verbatim. Do not summarize. "
                        "Return ONLY the verbatim transcript text."
                    )
                    print("[Gemini] Transcribing audio recording fallback...")
                    audio_transcript = call_gemini_with_fallback([transcribe_prompt, audio_part])
                    if audio_transcript:
                        print(f"[Gemini] Verbatim audio transcript: {audio_transcript}")
                        transcript_text = audio_transcript
                except Exception as audio_err:
                    print(f"[Gemini] Audio transcription failed: {audio_err}")

            # Build notes strictly from what was spoken in THIS meeting only
            if transcript_text:
                current_gemini_key = get_gemini_api_key()
                if current_gemini_key:
                    try:
                        prompt = f"""
                        You are an AI Class Assistant. Analyze this class transcript and generate structured, comprehensive study notes for the students. 
                        Focus ONLY on educational/academic content related to the subject taught (e.g. numpy, python libraries, data structures, data analysis). 
                        Discard any small talk, audio test chatter, or greetings.

                        Transcript:
                        \"\"\"{transcript_text}\"\"\"

                        Your output MUST be a valid JSON object inside a ```json ``` code block matching this format:
                        {{
                          "sections": [
                            {{
                              "heading": "Section Heading",
                              "bullets": [
                                "Bullet point detailing the concepts discussed",
                                "Technical details or code example if relevant"
                              ],
                              "diagramMermaid": "graph TD\\n  ... (optional Mermaid flowchart code if relevant)"
                            }}
                          ]
                        }}
                        """
                        response_text = call_gemini_with_fallback(prompt)
                        
                        # Parse JSON from response
                        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group(1).strip())
                        else:
                            data = json.loads(response_text.strip())
                            
                        sections = data.get("sections", [])

                    except Exception as e:
                        print(f"[Gemini] Failed to generate AI notes: {e}. Falling back to text extraction.")
                        # Fallback to simple extraction
                        sentences = [s.strip() for s in re.split(r'[.!?]+', transcript_text) if s.strip() and len(s.strip()) > 8]
                        sections = []
                        chunk_size = 3
                        for i in range(0, max(len(sentences), 1), chunk_size):
                            chunk = sentences[i:i + chunk_size]
                            if not chunk:
                                break
                            first = chunk[0]
                            words = first.split()
                            heading_words = [w for w in words if len(w) > 3][:4]
                            heading = " ".join(heading_words).title() if heading_words else f"Topic {i // chunk_size + 1}"
                            sections.append({
                                "heading": heading,
                                "bullets": chunk
                            })
                else:
                    # No Gemini key — fallback to simple text extraction
                    sentences = [s.strip() for s in re.split(r'[.!?]+', transcript_text) if s.strip() and len(s.strip()) > 8]
                    sections = []
                    chunk_size = 3
                    for i in range(0, max(len(sentences), 1), chunk_size):
                        chunk = sentences[i:i + chunk_size]
                        if not chunk:
                            break
                        first = chunk[0]
                        words = first.split()
                        heading_words = [w for w in words if len(w) > 3][:4]
                        heading = " ".join(heading_words).title() if heading_words else f"Topic {i // chunk_size + 1}"
                        sections.append({
                            "heading": heading,
                            "bullets": chunk
                        })
                    
                    if sections and not get_gemini_api_key():
                        sections[0]["bullets"].insert(0, "[NOTE: Please add a GEMINI_API_KEY in backend/.env to get high-quality AI-generated study notes.]")
                
                if not sections:
                    sections = [{
                        "heading": f"{meeting_title} – Session Notes",
                        "bullets": [transcript_text[:400]]
                    }]
            else:
                # No speech captured — show a helpful message
                sections = [
                    {
                        "heading": f"Session: {meeting_title}",
                        "bullets": [
                            "No speech was captured during this session.",
                            "Please enable your microphone and allow browser mic permissions to generate notes from speech.",
                            "Start the meeting again and speak clearly – your words will appear in the Live Transcription Feed and be saved here."
                        ]
                    }
                ]
            
            generated_at = datetime.datetime.now().isoformat()
            
            # ── Standalone notes document (for GET /api/notes/{id}) ──────────
            note = {
                "id": f"note_{meeting_id}",
                "meetingId": meeting_id,
                "meetingTitle": meeting_title,
                "structuredContent": sections,
                "pdfUrl": f"/api/notes/{meeting_id}/pdf",
                "generatedAt": generated_at,
                "transcriptText": transcript_text
            }
            save_notes(note)

            # ── Embed notes INSIDE the meeting document itself ───────────────
            # This makes each meeting a fully self-contained dataset.
            # No other meeting's notes will ever appear here.
            meeting["transcriptText"] = transcript_text
            meeting["structuredContent"] = sections
            meeting["notesGeneratedAt"] = generated_at
            meeting["transcriptId"] = f"note_{meeting_id}"

            save_meeting(meeting)
            print(f"[Notes] Meeting '{meeting_title}' (ID: {meeting_id}) — notes saved. "
                  f"Transcript words: {len(transcript_text.split()) if transcript_text else 0}.")
            return self.send_json(meeting)

        # POST /api/tasks/{id}/sync
        elif path.startswith("/api/tasks/") and path.endswith("/sync"):
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            task_id = path.split("/")[-2]
            task = get_task(task_id)
            if not task:
                return self.send_error_json("Task not found", 404)
                
            task["status"] = "synced"
            task["syncedTo"] = "notion"
            task["externalTaskId"] = "https://notion.so/mock-task-page"
            save_task(task)
            return self.send_json(task)

        # POST /api/integrations/notion/connect
        elif path == "/api/integrations/notion/connect":
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            user["connectedApps"]["notion"] = {
                "token": data.get("token"),
                "databaseId": data.get("databaseId")
            }
            save_user(user)
            return self.send_json(user)

        # POST /api/integrations/jira/connect
        elif path == "/api/integrations/jira/connect":
            user = self.authenticate()
            if not user:
                return self.send_error_json("Unauthorized", 401)
                
            user["connectedApps"]["jira"] = {
                "host": data.get("host"),
                "email": data.get("email"),
                "token": data.get("token"),
                "projectKey": data.get("projectKey")
            }
            save_user(user)
            return self.send_json(user)

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        """Admin: wipe all stale notes from the database."""
        path = urlparse(self.path).path
        if path == "/api/admin/clear-notes":
            if use_mongodb:
                result = mongo_db.notes.delete_many({})
                return self.send_json({"deleted": result.deleted_count, "message": "All stale notes cleared. Fresh notes will be generated on next session end."})
            else:
                db = read_json_db()
                count = len(db["notes"])
                db["notes"] = {}
                write_json_db(db)
                return self.send_json({"deleted": count, "message": "All notes cleared from local JSON database."})
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=None):
    if port is None:
        try:
            port = int(os.environ.get("PORT", 8000))
        except ValueError:
            port = 8000
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, PureAPIRequestHandler)
    print(f"[Pure-Backend] Server running at http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("[Pure-Backend] Server stopped.")

if __name__ == "__main__":
    run_server()
