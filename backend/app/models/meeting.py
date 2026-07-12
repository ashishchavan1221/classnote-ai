from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    scheduledAt: datetime
    participantEmails: List[str] = Field(default_factory=list)

class MeetingOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    hostId: str
    participantIds: List[str] = Field(default_factory=list)
    scheduledAt: datetime
    startedAt: Optional[datetime] = None
    endedAt: Optional[datetime] = None
    meetingLink: str
    status: str = Field(..., pattern="^(scheduled|live|completed)$")
    recordingUrl: Optional[str] = None
    transcriptId: Optional[str] = None
