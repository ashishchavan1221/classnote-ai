import logging
from fastapi import APIRouter, HTTPException, Depends, status
try:
    from bson import ObjectId
except ImportError:
    class ObjectId:
        def __init__(self, val=None):
            self.val = val or "000000000000000000000000"
        def __str__(self):
            return str(self.val)


from app.db.mongo import get_db
from app.routers.auth import get_current_user, IN_MEMORY_USERS
from app.models.user import NotionConnection, JiraConnection, UserOut, ConnectedApps

logger = logging.getLogger("app.routers.integrations")
router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

@router.post("/notion/connect", response_model=UserOut)
async def connect_notion(notion_data: NotionConnection, current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["id"]
    
    # Clean token values
    token = notion_data.token.strip() if notion_data.token else None
    database_id = notion_data.databaseId.strip() if notion_data.databaseId else None
    
    # Update profile in memory
    if user_id in IN_MEMORY_USERS:
        IN_MEMORY_USERS[user_id]["connectedApps"]["notion"] = {
            "token": token,
            "databaseId": database_id
        }
        
    # Update profile in MongoDB
    if db is not None:
        try:
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "connectedApps.notion.token": token,
                    "connectedApps.notion.databaseId": database_id
                }}
            )
            # Refresh current_user content
            updated = await db.users.find_one({"_id": ObjectId(user_id)})
            if updated:
                updated["id"] = str(updated["_id"])
                IN_MEMORY_USERS[user_id] = updated
                current_user = updated
        except Exception as e:
            logger.error(f"Failed to update Notion connection in mongo: {e}")
            
    # Return updated user
    user_dict = IN_MEMORY_USERS.get(user_id, current_user)
    conn_apps = user_dict.get("connectedApps", {})
    notion_conn = conn_apps.get("notion", {})
    jira_conn = conn_apps.get("jira", {})
    
    return UserOut(
        id=user_dict["id"],
        name=user_dict["name"],
        email=user_dict["email"],
        role=user_dict["role"],
        institution=user_dict.get("institution"),
        connectedApps=ConnectedApps(
            notion=NotionConnection(
                token=notion_conn.get("token"),
                databaseId=notion_conn.get("databaseId")
            ),
            jira=JiraConnection(
                host=jira_conn.get("host"),
                email=jira_conn.get("email"),
                token=jira_conn.get("token"),
                projectKey=jira_conn.get("projectKey")
            )
        )
    )

@router.post("/jira/connect", response_model=UserOut)
async def connect_jira(jira_data: JiraConnection, current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["id"]
    
    # Clean token values
    host = jira_data.host.strip() if jira_data.host else None
    email = jira_data.email.strip() if jira_data.email else None
    token = jira_data.token.strip() if jira_data.token else None
    project_key = jira_data.projectKey.strip() if jira_data.projectKey else None
    
    # Update profile in memory
    if user_id in IN_MEMORY_USERS:
        IN_MEMORY_USERS[user_id]["connectedApps"]["jira"] = {
            "host": host,
            "email": email,
            "token": token,
            "projectKey": project_key
        }
        
    # Update profile in MongoDB
    if db is not None:
        try:
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "connectedApps.jira.host": host,
                    "connectedApps.jira.email": email,
                    "connectedApps.jira.token": token,
                    "connectedApps.jira.projectKey": project_key
                }}
            )
            # Refresh current_user content
            updated = await db.users.find_one({"_id": ObjectId(user_id)})
            if updated:
                updated["id"] = str(updated["_id"])
                IN_MEMORY_USERS[user_id] = updated
                current_user = updated
        except Exception as e:
            logger.error(f"Failed to update Jira connection in mongo: {e}")
            
    # Return updated user
    user_dict = IN_MEMORY_USERS.get(user_id, current_user)
    conn_apps = user_dict.get("connectedApps", {})
    notion_conn = conn_apps.get("notion", {})
    jira_conn = conn_apps.get("jira", {})
    
    return UserOut(
        id=user_dict["id"],
        name=user_dict["name"],
        email=user_dict["email"],
        role=user_dict["role"],
        institution=user_dict.get("institution"),
        connectedApps=ConnectedApps(
            notion=NotionConnection(
                token=notion_conn.get("token"),
                databaseId=notion_conn.get("databaseId")
            ),
            jira=JiraConnection(
                host=jira_conn.get("host"),
                email=jira_conn.get("email"),
                token=jira_conn.get("token"),
                projectKey=jira_conn.get("projectKey")
            )
        )
    )
