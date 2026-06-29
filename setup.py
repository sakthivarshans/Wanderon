"""
WanderOn setup script — run this once before starting the app.
Installs Python dependencies and prepares the data directory.
"""

import subprocess
import sys
import os

def main():
    """
    Validates environment prerequisites, downloads Python backend dependencies,
    and initializes local directories.
    """
    print("=" * 50)
    print("  WanderOn — Setup")
    print("=" * 50)

    # 1. Check Python version
    if sys.version_info < (3, 10):
        print("Python 3.10+ is required.")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")

    # 2. Install backend deps
    print("\nInstalling Python backend dependencies...")
    req = os.path.join(os.path.dirname(__file__), "backend", "requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req, "--quiet"],
        capture_output=False
    )
    if result.returncode != 0:
        print("pip install failed. Try: pip install -r backend/requirements.txt manually.")
        sys.exit(1)
    print("✓ Python dependencies installed")

    # 3. Create data dir
    data_dir = os.path.join(os.path.expanduser("~"), ".wanderon")
    os.makedirs(data_dir, exist_ok=True)
    print(f"✓ Data directory: {data_dir}")

    print("\nSetup complete!")
    print("\nNext steps:")
    print("  1. Install Node.js (https://nodejs.org) if not already installed")
    print("  2. Install Rust (https://rustup.rs) if not already installed")
    print("  3. Run:  npm install")
    print("  4. Run:  npm run tauri:dev   (development mode)")
    print("  OR")
    print("     Run backend manually: python backend/main.py")
    print("     Then open: http://localhost:1420 in your browser")

if __name__ == "__main__":
    main()
