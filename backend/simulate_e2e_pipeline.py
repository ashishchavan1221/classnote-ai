import os
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def run_simulation():
    print("=" * 60)
    print("        ClassNote AI - E2E Simulation Orchestrator")
    print("=" * 60)

    # 1. Register User
    print("[Simulator] Registering user account...")
    reg_data = {
        "name": "Simulated Professor",
        "email": "prof_simulator@test.com",
        "password": "password123",
        "role": "teacher",
        "institution": "ClassNote Simulator Academy"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
        if r.status_code == 200:
            token = r.json()["access_token"]
            print("[Simulator] Registration successful.")
        else:
            # Try login if already registered
            print("[Simulator] Account exists. Logging in...")
            r = requests.post(f"{BASE_URL}/auth/login", json={
                "email": reg_data["email"],
                "password": reg_data["password"]
            })
            token = r.json()["access_token"]
            print("[Simulator] Log in successful.")
    except Exception as e:
        print(f"[Simulator] Failed to connect to server on port 8000: {e}")
        print("[Simulator] Ensure that 'python run.py' is running in your terminal!")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Meeting
    print("[Simulator] Scheduling a new class session...")
    meeting_payload = {
        "title": "E2E AI Automation Pipelines",
        "description": "Simulation of voice transcribing and ReportLab cursive PDF builders.",
        "scheduledAt": "2026-07-11T18:00:00Z"
    }
    r = requests.post(f"{BASE_URL}/meetings", json=meeting_payload, headers=headers)
    meeting = r.json()
    meeting_id = meeting["id"]
    print(f"[Simulator] Session created. Meeting ID: {meeting_id}")
    print(f"[Simulator] Jitsi Room link: {meeting['meetingLink']}")

    # 3. Start Meeting
    print("[Simulator] Starting meeting call...")
    requests.post(f"{BASE_URL}/meetings/{meeting_id}/start", headers=headers)

    # 4. End Meeting (Triggers pipeline)
    print("[Simulator] Ending meeting (triggering AI post-processing)...")
    requests.post(f"{BASE_URL}/meetings/{meeting_id}/end", headers=headers)

    # 5. Fetch Notes
    print("[Simulator] Fetching compiled structured notes...")
    r = requests.get(f"{BASE_URL}/notes/{meeting_id}", headers=headers)
    notes = r.json()
    print("[Simulator] Notes fetched successfully. Sections compiled:")
    for idx, sec in enumerate(notes["structuredContent"]):
        print(f"  {idx + 1}. {sec['heading']}")

    # 6. Fetch PDF
    print("[Simulator] Downloading handwriting PDF document...")
    r = requests.get(f"{BASE_URL}/notes/{meeting_id}/pdf", headers=headers)
    
    pdf_dir = os.path.join(os.getcwd(), "storage", "pdfs")
    pdf_path = os.path.join(pdf_dir, f"notes_{meeting_id}.pdf")
    
    with open(pdf_path, "wb") as f:
        f.write(r.content)
        
    print("=" * 60)
    print(f"[Simulator] SUCCESS! Notes PDF has been generated on your system.")
    print(f"[Simulator] Path: {pdf_path}")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation()
