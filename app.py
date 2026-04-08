import subprocess
import threading

def start_inference():
    subprocess.Popen(["python", "inference.py"])

# start inference in background
threading.Thread(target=start_inference, daemon=True).start()

# start OpenEnv server
from server import app

def main():
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

