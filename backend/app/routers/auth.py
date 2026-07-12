import uuid
from datetime import timedelta
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
try:
    from bson import ObjectId
except ImportError:
    class ObjectId:
        def __init__(self, val=None):
            self.val = val or "000000000000000000000000"
        def __str__(self):
            return str(self.val)


from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.db.mongo import get_db
from app.models.user import UserRegister, UserLogin, UserOut, Token, ConnectedApps, NotionConnection, JiraConnection

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

# In-memory database fallback
IN_MEMORY_USERS: Dict[str, dict] = {}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload["sub"]
    db = get_db()
    
    if db is not None:
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["id"] = str(user["_id"])
                return user
        except Exception:
            pass # fallback to memory search if db error
            
    if user_id in IN_MEMORY_USERS:
        return IN_MEMORY_USERS[user_id]
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found.",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister):
    db = get_db()
    email_lower = user_data.email.lower()
    
    # Check duplicate
    user_exists = False
    if db is not None:
        try:
            existing = await db.users.find_one({"email": email_lower})
            if existing:
                user_exists = True
        except Exception:
            pass
            
    if not user_exists:
        for u in IN_MEMORY_USERS.values():
            if u["email"] == email_lower:
                user_exists = True
                break
                
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already registered."
        )
        
    hashed_pwd = hash_password(user_data.password)
    user_dict = {
        "name": user_data.name,
        "email": email_lower,
        "passwordHash": hashed_pwd,
        "role": user_data.role,
        "institution": user_data.institution,
        "connectedApps": {
            "notion": {"token": None, "databaseId": None},
            "jira": {"host": None, "email": None, "token": None, "projectKey": None}
        }
    }
    
    user_id_str = ""
    if db is not None:
        try:
            result = await db.users.insert_one(user_dict)
            user_id_str = str(result.inserted_id)
        except Exception as e:
            # Fallback to local memory if insertion fails
            user_id_str = str(uuid.uuid4())
    else:
        user_id_str = str(uuid.uuid4())
        
    user_dict["id"] = user_id_str
    IN_MEMORY_USERS[user_id_str] = user_dict
    
    # Create Access Token
    access_token = create_access_token(data={"sub": user_id_str, "role": user_data.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    email_lower = credentials.email.lower()
    db = get_db()
    
    user = None
    if db is not None:
        try:
            user = await db.users.find_one({"email": email_lower})
            if user:
                user["id"] = str(user["_id"])
        except Exception:
            pass
            
    if not user:
        for u in IN_MEMORY_USERS.values():
            if u["email"] == email_lower:
                user = u
                break
                
    if not user or not verify_password(credentials.password, user["passwordHash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
        
    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    # Map raw mongo dict or mock dict to UserOut format safely
    connected_apps = current_user.get("connectedApps", {})
    
    notion_data = connected_apps.get("notion", {})
    jira_data = connected_apps.get("jira", {})
    
    return UserOut(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        institution=current_user.get("institution"),
        connectedApps=ConnectedApps(
            notion=NotionConnection(
                token=notion_data.get("token"),
                databaseId=notion_data.get("databaseId")
            ),
            jira=JiraConnection(
                host=jira_data.get("host"),
                email=jira_data.get("email"),
                token=jira_data.get("token"),
                projectKey=jira_data.get("projectKey")
            )
        )
    )
