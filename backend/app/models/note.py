from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class NoteSection(BaseModel):
    heading: str
    bullets: List[str] = Field(default_factory=list)
    diagramUrl: Optional[str] = None
    diagramMermaid: Optional[str] = None # Mermaid code block string for markdown rendering

class NoteOut(BaseModel):
    id: str
    meetingId: str
    structuredContent: List[NoteSection] = Field(default_factory=list)
    pdfUrl: Optional[str] = None
    generatedAt: datetime
