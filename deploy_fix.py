#!/usr/bin/env python3
"""
Quick deployment fix script
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Command: {cmd}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    """Deploy the fix."""
    print("🔧 Deploying speech recognition fix...")
    
    # Add changes to git
    print("\n1️⃣ Adding changes to git...")
    if not run_command("git add ."):
        print("❌ Failed to add changes")
        return
    
    # Commit changes
    print("\n2️⃣ Committing changes...")
    if not run_command('git commit -m "Fix speech recognition dependency error"'):
        print("❌ Failed to commit changes")
        return
    
    # Push to trigger deployment
    print("\n3️⃣ Pushing to trigger deployment...")
    if not run_command("git push"):
        print("❌ Failed to push changes")
        return
    
    print("\n✅ Fix deployed! The bot should work now.")
    print("🕐 Wait 2-3 minutes for Render to rebuild and deploy.")
    print("🧪 Then test by sending a message to your bot.")

if __name__ == "__main__":
    main()
