import os
import json
from pymongo import MongoClient

# Database configuration
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
MONGODB_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "meeting_notes_db"

if os.path.exists(ENV_FILE):
    try:
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    if key.strip() == "MONGODB_URI":
                        MONGODB_URI = val.strip()
                    elif key.strip() == "MONGO_DB_NAME":
                        MONGO_DB_NAME = val.strip()
    except Exception as e:
        print(f"Error parsing env file: {e}")

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

# 1. Seed MongoDB Atlas
print(f"[Seeder] Seeding MongoDB Atlas database '{MONGO_DB_NAME}'...")
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
    db = client[MONGO_DB_NAME]
    db.users.update_one({"email": teacher_user["email"]}, {"$set": teacher_user}, upsert=True)
    db.users.update_one({"email": student_user["email"]}, {"$set": student_user}, upsert=True)
    print("[Seeder] Successfully seeded MongoDB Atlas.")
except Exception as e:
    print(f"[Seeder] Skip MongoDB seed: {e}")

# 2. Seed Local JSON Database (storage/db.json)
print("[Seeder] Seeding local file storage/db.json...")
db_file = os.path.join(BACKEND_DIR, "storage", "db.json")
os.makedirs(os.path.join(BACKEND_DIR, "storage"), exist_ok=True)

db_data = {"users": {}, "meetings": {}, "notes": {}, "tasks": {}}
if os.path.exists(db_file):
    try:
        with open(db_file, "r") as f:
            db_data = json.load(f)
    except Exception:
        pass

# Update accounts in json memory
db_data["users"][teacher_user["id"]] = teacher_user
db_data["users"][student_user["id"]] = student_user

try:
    with open(db_file, "w") as f:
        json.dump(db_data, f, indent=2)
    print("[Seeder] Successfully seeded local storage/db.json.")
except Exception as e:
    print(f"[Seeder] Failed to write local JSON DB: {e}")

print("\nSUCCESS! Ready-to-use logins are now configured everywhere.")
print(f"  Teacher Email: {teacher_user['email']} / Password: {teacher_user['password']}")
print(f"  Student Email: {student_user['email']} / Password: {student_user['password']}")
