"""
WanderOn dev runner — starts backend + opens browser UI.
Use this for development WITHOUT needing Rust/Tauri installed.
"""

import subprocess
import sys
import os
import time
import webbrowser
import threading

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")

def run_backend():
    print("[WanderOn] Starting Python backend on http://127.0.0.1:7291 ...")
    subprocess.run(
        [sys.executable, "main.py"],
        cwd=BACKEND_DIR,
        env={**os.environ, "WANDERON_PORT": "7291"}
    )

def main():
    print("=" * 50)
    print("  WanderOn — Development Mode")
    print("=" * 50)
    print("This starts the backend only.")
    print("Open the UI by running: npm run dev  (in another terminal)")
    print("Then open: http://localhost:1420")
    print()
    print("OR just run the backend and configure your Telegram bot directly.")
    print("Press Ctrl+C to stop.\n")

    run_backend()

if __name__ == "__main__":
    main()
