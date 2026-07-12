import logging
from typing import List, Dict, Optional
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
from app.models.task import ActionItemOut
from app.routers.auth import get_current_user
from app.services.task_sync_service import sync_task_to_external_services

logger = logging.getLogger("app.routers.tasks")
router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# Fallback in-memory storage for action items
IN_MEMORY_TASKS: Dict[str, dict] = {}

@router.get("", response_model=List[ActionItemOut])
async def list_tasks(meetingId: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    tasks_list = []
    
    if db is not None:
        try:
            # Build query
            query = {}
            if meetingId:
                query["meetingId"] = meetingId
                
            # If user is a student, only show tasks assigned to them
            if user_role == "student":
                query["assigneeId"] = user_id
                
            cursor = db.action_items.find(query)
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                
                # Fetch meeting title context
                meeting = await db.meetings.find_one({"_id": ObjectId(doc["meetingId"])})
                if meeting:
                    doc["meetingTitle"] = meeting.get("title")
                
                # Fetch assignee name
                if doc.get("assigneeId"):
                    assignee = await db.users.find_one({"_id": ObjectId(doc["assigneeId"])})
                    if assignee:
                        doc["assigneeName"] = assignee.get("name")
                        
                tasks_list.append(doc)
        except Exception as e:
            logger.error(f"Failed to fetch tasks from mongo: {e}")
            
    # Fallback/merge with in-memory storage
    if not tasks_list:
        from app.routers.meetings import IN_MEMORY_MEETINGS
        from app.routers.auth import IN_MEMORY_USERS
        
        for t in IN_MEMORY_TASKS.values():
            # Apply filters
            if meetingId and t["meetingId"] != meetingId:
                continue
            if user_role == "student" and t["assigneeId"] != user_id:
                continue
                
            # Populate meeting title
            meeting = IN_MEMORY_MEETINGS.get(t["meetingId"])
            if meeting:
                t["meetingTitle"] = meeting["title"]
                
            # Populate assignee name
            if t.get("assigneeId"):
                assignee = IN_MEMORY_USERS.get(t["assigneeId"])
                if assignee:
                    t["assigneeName"] = assignee["name"]
                    
            tasks_list.append(t)
            
    # Map to schemas
    return [ActionItemOut(
        id=t["id"],
        meetingId=t["meetingId"],
        meetingTitle=t.get("meetingTitle"),
        description=t["description"],
        assigneeId=t.get("assigneeId"),
        assigneeName=t.get("assigneeName"),
        dueDate=t.get("dueDate"),
        status=t["status"],
        syncedTo=t.get("syncedTo"),
        externalTaskId=t.get("externalTaskId")
    ) for t in tasks_list]

@router.post("/{id}/sync", response_model=ActionItemOut)
async def sync_task(id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    task = None
    
    if db is not None:
        try:
            task = await db.action_items.find_one({"_id": ObjectId(id)})
            if task:
                task["id"] = str(task["_id"])
        except Exception:
            pass
            
    if not task and id in IN_MEMORY_TASKS:
        task = IN_MEMORY_TASKS[id]
        
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
        
    # Attempt to sync to connected integrations of the current user
    updated_task = await sync_task_to_external_services(task, current_user)
    
    # Save back
    if db is not None:
        try:
            await db.action_items.update_one(
                {"_id": ObjectId(id)},
                {"$set": {
                    "status": updated_task["status"],
                    "syncedTo": updated_task.get("syncedTo"),
                    "externalTaskId": updated_task.get("externalTaskId")
                }}
            )
        except Exception:
            pass
            
    IN_MEMORY_TASKS[id] = updated_task
    
    return ActionItemOut(
        id=updated_task["id"],
        meetingId=updated_task["meetingId"],
        meetingTitle=updated_task.get("meetingTitle"),
        description=updated_task["description"],
        assigneeId=updated_task.get("assigneeId"),
        assigneeName=updated_task.get("assigneeName"),
        dueDate=updated_task.get("dueDate"),
        status=updated_task["status"],
        syncedTo=updated_task.get("syncedTo"),
        externalTaskId=updated_task.get("externalTaskId")
    )
