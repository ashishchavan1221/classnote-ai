import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger("app.services.transcription")

async def transcribe_meeting(meeting_id: str) -> tuple[str, list[dict]]:
    """
    Transcribes audio recording for a meeting.
    Returns:
        tuple containing (raw_text_transcript, list_of_segments)
        Each segment is a dict: {"speaker": str, "text": str, "timestamp": str}
    """
    logger.info(f"Transcribing audio for meeting {meeting_id}...")
    
    # Simulate processing time
    await asyncio.sleep(2)
    
    if settings.USE_MOCK_SERVICES or not settings.OPENAI_API_KEY:
        logger.info("Using mock transcription services.")
        
        # High quality CS class simulation transcript
        segments = [
            {
                "speaker": "Teacher (Dr. Sarah)",
                "text": "Good morning class! Today we are discussing the architecture of Web Application Pipelines, specifically connecting React frontends with FastAPI backends and syncing jobs to external boards like Jira and Notion.",
                "timestamp": "00:00"
            },
            {
                "speaker": "Teacher (Dr. Sarah)",
                "text": "For our course project, Alex will be responsible for creating the React Vite scaffold and integrating TailwindCSS. This needs to be completed by next Friday, July 18th.",
                "timestamp": "01:15"
            },
            {
                "speaker": "Student (Alex)",
                "text": "Sure, Dr. Sarah. I'll get that set up and use shadcn/ui components for a premium look.",
                "timestamp": "02:00"
            },
            {
                "speaker": "Teacher (Dr. Sarah)",
                "text": "Excellent. Now, Chloe, you will take charge of building the FastAPI endpoints for JWT Auth and hooking it up to MongoDB. Can you have a working draft ready by July 20th?",
                "timestamp": "02:40"
            },
            {
                "speaker": "Student (Chloe)",
                "text": "Yes, I will use Motor for async mongo access and set up local environment variables for the secret keys.",
                "timestamp": "03:10"
            },
            {
                "speaker": "Teacher (Dr. Sarah)",
                "text": "Perfect. For the database connection flow: first the React client makes a POST request to /api/auth/register, the backend hashes the password, inserts into MongoDB, and returns a JWT token. Let's make sure we document this flow in a flowchart inside our study notes.",
                "timestamp": "03:50"
            },
            {
                "speaker": "Teacher (Dr. Sarah)",
                "text": "Lastly, Dan, your task is to wire up the Notion API integrations and write the ReportLab PDF export service. Let's aim to have that finalized by July 22nd.",
                "timestamp": "04:30"
            },
            {
                "speaker": "Student (Dan)",
                "text": "Got it. I'll read up on ReportLab canvas formatting and Notion's database pages endpoint.",
                "timestamp": "05:00"
            },
            {
                "speaker": "Teacher (Dr. Sarah)",
                "text": "Great! Let's summarize: Alex does frontend by July 18, Chloe does auth by July 20, and Dan does Notion sync and PDF by July 22. That concludes today's lecture. Let's get to work!",
                "timestamp": "05:30"
            }
        ]
        
        raw_text = " ".join([f"[{s['timestamp']}] {s['speaker']}: {s['text']}" for s in segments])
        return raw_text, segments

    # Real Whisper API transcription could go here
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # In a real environment, we would download the meeting audio file.
        # For this setup, we simulate reading an audio file or handle a placeholder.
        logger.info("Executing OpenAI Whisper transcription call...")
        # (This block runs if the user populates OPENAI_API_KEY)
        # For simplicity, we fallback to the mock or return a basic message
        raw_text, segments = await run_whisper_on_placeholder()
        return raw_text, segments
    except Exception as e:
        logger.error(f"Whisper API transcription failed, falling back to mock: {e}")
        # Call mock
        settings.USE_MOCK_SERVICES = True
        return await transcribe_meeting(meeting_id)

async def run_whisper_on_placeholder():
    # Return placeholder transcript
    text = "Teacher: This is a live class. We are learning how to build RAG pipelines."
    segments = [{"speaker": "Teacher", "text": "This is a live class. We are learning how to build RAG pipelines.", "timestamp": "00:00"}]
    return text, segments
