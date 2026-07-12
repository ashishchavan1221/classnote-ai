from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict

class NotionConnection(BaseModel):
    token: Optional[str] = None
    databaseId: Optional[str] = None

class JiraConnection(BaseModel):
    host: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None
    projectKey: Optional[str] = None

class ConnectedApps(BaseModel):
    notion: Optional[NotionConnection] = Field(default_factory=NotionConnection)
    jira: Optional[JiraConnection] = Field(default_factory=JiraConnection)

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(teacher|student)$")
    institution: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    institution: Optional[str] = None
    connectedApps: ConnectedApps = Field(default_factory=ConnectedApps)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
