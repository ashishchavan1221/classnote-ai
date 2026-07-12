import os
import sys
import subprocess
import threading
import time

def print_banner():
    print("=" * 60)
    print("         ClassNote AI - Live Launch Orchestrator")
    print("=" * 60)
    print("  Starting backend FastAPI (Port 8000) & frontend Vite (Port 5173)...")
    print("  Press Ctrl+C to terminate both servers concurrently.")
    print("=" * 60)

# Track active subprocesses to terminate them on exit
active_processes = []

def run_command_in_thread(name, command, working_dir):
    try:
        # Use shell=True for windows environment matching
        p = subprocess.Popen(
            command,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=True
        )
        active_processes.append(p)
        
        # Read lines and output with namespaced prefixes
        for line in iter(p.stdout.readline, ""):
            print(f"[{name}] {line.strip()}")
            
        p.stdout.close()
        p.wait()
    except Exception as e:
        print(f"[{name}] Error executing process: {e}")

if __name__ == "__main__":
    print_banner()
    
    backend_dir = os.path.join(os.getcwd(), "backend")
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    
    # Python executable command
    python_exec = sys.executable
    backend_cmd = f'"{python_exec}" app_pure.py'
    frontend_cmd = "npm run dev"
    
    # Create threads
    t_backend = threading.Thread(
        target=run_command_in_thread, 
        args=("FastAPI-Backend", backend_cmd, backend_dir),
        daemon=True
    )
    t_frontend = threading.Thread(
        target=run_command_in_thread, 
        args=("React-Frontend", frontend_cmd, frontend_dir),
        daemon=True
    )
    
    # Start threads
    t_backend.start()
    time.sleep(1.5) # Give backend a head start
    t_frontend.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Orchestrator] Termination signal received (Ctrl+C). Cleaning up servers...")
        for p in active_processes:
            try:
                p.terminate()
                p.kill()
            except Exception:
                pass
        print("[Orchestrator] Both servers shut down successfully. Goodbye!")
