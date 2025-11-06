#!/usr/bin/env python3
"""
Simple runner script for AllowButtonClickApp.
Handles virtual environment activation and provides easy commands.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("AllowButtonClickApp Runner")
        print("\nUsage:")
        print("  python run.py setup     - Install dependencies")
        print("  python run.py check     - Check permissions")
        print("  python run.py test      - Test detection (safe)")
        print("  python run.py start     - Start the app")
        print("  python run.py tests     - Run test suite")
        return
    
    command = sys.argv[1].lower()
    
    # Base commands that work with virtual environment
    venv_cmd = "source venv/bin/activate &&"
    
    if command == "setup":
        print("🚀 Setting up AllowButtonClickApp...")
        
        # Create virtual environment if it doesn't exist
        if not Path("venv").exists():
            if not run_command("python3 -m venv venv", "Creating virtual environment"):
                return
        
        # Install dependencies
        run_command(f"{venv_cmd} pip install --upgrade pip setuptools wheel", "Upgrading pip")
        run_command(f"{venv_cmd} pip install -r requirements.txt", "Installing dependencies")
        
        print("\n✨ Setup complete!")
        print("Next steps:")
        print("1. python run.py check  (check permissions)")
        print("2. python run.py test   (test detection)")
        print("3. python run.py start  (run the app)")
    
    elif command == "check":
        run_command(f"{venv_cmd} python check_permissions.py", "Checking permissions")
    
    elif command == "test":
        run_command(f"{venv_cmd} python src/allow_clicker.py --test", "Testing button detection")
    
    elif command == "start":
        print("🎯 Starting AllowButtonClickApp...")
        print("Press ESC to stop the app at any time.")
        try:
            subprocess.run(f"{venv_cmd} python src/allow_clicker.py", shell=True)
        except KeyboardInterrupt:
            print("\n👋 App stopped by user")
    
    elif command == "tests":
        run_command(f"{venv_cmd} python tests/test_detection.py", "Running test suite")
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'python run.py' to see available commands")


if __name__ == "__main__":
    main()