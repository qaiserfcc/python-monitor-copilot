#!/usr/bin/env python3
"""
Permission checker for AllowButtonClickApp.
Helps users set up required macOS permissions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils import check_macos_permissions, display_permission_help


def main():
    """Check and guide user through permission setup."""
    print("=== AllowButtonClickApp Permission Checker ===\n")
    
    print("Checking macOS permissions...")
    
    if check_macos_permissions():
        print("✅ Permissions appear to be granted!")
        print("You should be able to run the app successfully.\n")
        print("To test: python src/allow_clicker.py --test")
    else:
        print("❌ Missing required permissions.")
        print("Please grant the following permissions:\n")
        display_permission_help()
        print("\nAfter granting permissions:")
        print("1. Restart this application")
        print("2. Run: python check_permissions.py")
        print("3. If successful, run: python src/allow_clicker.py --test")


if __name__ == "__main__":
    main()