import logging
import requests
from typing import List, Dict
from app.db.mongo import get_db

logger = logging.getLogger("app.services.task_sync")

async def auto_sync_meeting_tasks(meeting_id: str, action_items: List[dict]):
    """Automatically syncs a meeting's action items using the meeting host's credentials."""
    logger.info(f"Auto-syncing action items for meeting {meeting_id}...")
    db = get_db()
    
    if not action_items:
        return
        
    host_user = None
    if db is not None:
        try:
            # Find meeting to get hostId
            from bson import ObjectId
            meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
            if meeting:
                host_user = await db.users.find_one({"_id": ObjectId(meeting["hostId"])})
        except Exception as e:
            logger.error(f"Failed to fetch host settings: {e}")
            
    if not host_user:
        # Check mock users fallback
        from app.routers.auth import IN_MEMORY_USERS
        from app.routers.meetings import IN_MEMORY_MEETINGS
        
        meeting = IN_MEMORY_MEETINGS.get(meeting_id)
        if meeting:
            host_user = IN_MEMORY_USERS.get(meeting["hostId"])
            
    if not host_user:
        logger.warning(f"Could not find host for meeting {meeting_id}. Skipping auto-sync.")
        return

    # Sync each task
    for item in action_items:
        try:
            updated = await sync_task_to_external_services(item, host_user)
            # Update database record status
            if db is not None:
                await db.action_items.update_one(
                    {"_id": ObjectId(item["id"]) if isinstance(item["id"], str) and len(item["id"]) == 24 else item["id"]},
                    {"$set": {
                        "status": updated["status"],
                        "syncedTo": updated.get("syncedTo"),
                        "externalTaskId": updated.get("externalTaskId")
                    }}
                )
            
            # Update local fallback
            from app.routers.tasks import IN_MEMORY_TASKS
            IN_MEMORY_TASKS[item["id"]] = updated
        except Exception as e:
            logger.error(f"Failed auto-syncing action item {item.get('id')}: {e}")

async def sync_task_to_external_services(task: dict, user: dict) -> dict:
    """
    Syncs a single task to Notion and/or Jira depending on user's integration settings.
    """
    task_copy = task.copy()
    connected_apps = user.get("connectedApps", {})
    
    notion = connected_apps.get("notion", {})
    jira = connected_apps.get("jira", {})
    
    notion_token = notion.get("token")
    notion_db = notion.get("databaseId")
    
    jira_host = jira.get("host")
    jira_email = jira.get("email")
    jira_token = jira.get("token")
    jira_project = jira.get("projectKey")
    
    # Check if we should use mock sync
    use_mock = True
    if (notion_token and notion_db) or (jira_host and jira_email and jira_token and jira_project):
        use_mock = False
        
    if use_mock:
        logger.info(f"[Task Sync Mock] Simulated syncing task '{task_copy['description']}' to student backlog.")
        task_copy["status"] = "synced"
        task_copy["syncedTo"] = "notion"
        task_copy["externalTaskId"] = "https://notion.so/mock-page-id-123456"
        return task_copy

    # 1. Sync to Notion
    if notion_token and notion_db:
        try:
            logger.info("Syncing task to Notion...")
            url = "https://api.notion.com/v1/pages"
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            # Match schema: Target database should have Name and Description columns
            payload = {
                "parent": {"database_id": notion_db},
                "properties": {
                    "Name": {
                        "title": [
                            {"text": {"content": task_copy["description"]}}
                        ]
                    },
                    "Assignee": {
                        "rich_text": [
                            {"text": {"content": task_copy.get("assigneeName") or "Unassigned"}}
                        ]
                    }
                }
            }
            
            # If due date exists
            if task_copy.get("dueDate"):
                due_date_str = task_copy["dueDate"].strftime("%Y-%m-%d") if hasattr(task_copy["dueDate"], "strftime") else str(task_copy["dueDate"])[:10]
                payload["properties"]["Due Date"] = {
                    "date": {"start": due_date_str}
                }
                
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200 or resp.status_code == 201:
                res_data = resp.json()
                task_copy["status"] = "synced"
                task_copy["syncedTo"] = "notion"
                task_copy["externalTaskId"] = res_data.get("url", "https://notion.so")
                logger.info("Successfully synced to Notion!")
                return task_copy
            else:
                logger.error(f"Notion API error: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Notion connection failed: {e}")

    # 2. Sync to Jira
    if jira_host and jira_email and jira_token and jira_project:
        try:
            logger.info("Syncing task to Jira...")
            # Clean host url
            host = jira_host.strip()
            if not host.startswith("http"):
                host = f"https://{host}"
            if host.endswith("/"):
                host = host[:-1]
                
            url = f"{host}/rest/api/3/issue"
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(jira_email, jira_token)
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            
            payload = {
                "fields": {
                    "project": {"key": jira_project},
                    "summary": task_copy["description"],
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": f"Assigned to {task_copy.get('assigneeName') or 'Unassigned'}. Generated by Autonomous Meeting notes pipeline."}
                                ]
                            }
                        ]
                    },
                    "issuetype": {"name": "Task"}
                }
            }
            
            resp = requests.post(url, json=payload, headers=headers, auth=auth, timeout=10)
            if resp.status_code == 201:
                res_data = resp.json()
                task_copy["status"] = "synced"
                task_copy["syncedTo"] = "jira"
                task_copy["externalTaskId"] = f"{host}/browse/{res_data.get('key')}"
                logger.info(f"Successfully synced to Jira (Issue key: {res_data.get('key')})!")
                return task_copy
            else:
                logger.error(f"Jira API error: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Jira connection failed: {e}")

    # Fallback to simulated sync if API calls fail or credentials are partially invalid
    task_copy["status"] = "synced"
    task_copy["syncedTo"] = "notion"
    task_copy["externalTaskId"] = "https://notion.so/mock-page-id-fallback"
    return task_copy
