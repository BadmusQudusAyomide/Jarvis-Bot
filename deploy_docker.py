#!/usr/bin/env python3
"""
Docker deployment script for Jarvis Bot
"""

import subprocess
import sys
import time

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        print(f"🔄 Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.stdout:
            print(f"✅ Output: {result.stdout.strip()}")
        if result.stderr and result.returncode != 0:
            print(f"❌ Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    """Deploy the Docker fix."""
    print("🐳 Deploying Jarvis Bot Docker Fix")
    print("=" * 50)
    
    # Check if we're in the right directory
    import os
    if not os.path.exists("Dockerfile"):
        print("❌ Dockerfile not found. Please run this from the project root.")
        return
    
    # Add changes to git
    print("\n1️⃣ Adding changes to git...")
    if not run_command("git add ."):
        print("❌ Failed to add changes")
        return
    
    # Commit changes
    print("\n2️⃣ Committing changes...")
    if not run_command('git commit -m "Fix speech recognition dependency error for Docker deployment"'):
        print("⚠️ No changes to commit or commit failed")
    
    # Push to trigger Render rebuild
    print("\n3️⃣ Pushing to trigger Render rebuild...")
    if not run_command("git push"):
        print("❌ Failed to push changes")
        return
    
    print("\n✅ Docker deployment triggered!")
    print("\n📋 What happens next:")
    print("1. 🔄 Render will detect the git push")
    print("2. 🐳 Docker image will be rebuilt with fixed dependencies")
    print("3. 🚀 New container will be deployed (2-3 minutes)")
    print("4. 🧪 Test your bot by sending messages")
    
    print("\n🔗 Monitor deployment at: https://dashboard.render.com")
    print("📱 Test Telegram: @BadmusQudusbot")
    print("📱 Test WhatsApp: +1 (555) 142-0604")
    
    # Optional: Check deployment status
    print("\n⏰ Waiting 30 seconds, then checking health...")
    time.sleep(30)
    
    print("\n4️⃣ Checking deployment health...")
    if run_command("curl -s https://jarvis-bot-ftpp.onrender.com/ | grep healthy"):
        print("✅ Deployment appears healthy!")
    else:
        print("⚠️ Health check inconclusive - check Render dashboard")

if __name__ == "__main__":
    main()
