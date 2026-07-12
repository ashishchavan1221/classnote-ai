from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ActionItemOut(BaseModel):
    id: str
    meetingId: str
    meetingTitle: Optional[str] = None
    description: str
    assigneeId: Optional[str] = None
    assigneeName: Optional[str] = None
    dueDate: Optional[datetime] = None
    status: str = Field(..., pattern="^(pending|synced|completed)$")
    syncedTo: Optional[str] = None # "notion", "jira", or null
    externalTaskId: Optional[str] = None
