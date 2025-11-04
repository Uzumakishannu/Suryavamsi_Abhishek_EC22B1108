# Starter script: launches backend streamer in background thread and starts Streamlit UI.
import threading, subprocess, time, sys, os

def start_backend():
    cmd = [sys.executable, '-u', '-m', 'backend.real_backend']
    subprocess.run(cmd)

if __name__ == '__main__':
    t = threading.Thread(target=start_backend, daemon=True)
    t.start()
    # give backend moment to initialize
    time.sleep(1.0)
    # launch streamlit
    try:
        subprocess.run(['streamlit', 'run', 'frontend/app.py', '--server.port=8501'])
    except FileNotFoundError:
        print('Streamlit not found. Install dependencies with: pip install -r requirements.txt')
