"""
debug_telegram.py
Diagnostic tool to verify Telegram bot credentials and identify the User Chat ID.
"""
import os
import sys
import requests
from pathlib import Path

# Local imports
sys.path.append(str(Path.cwd()))
import env_discovery

def debug_telegram():
    print("=== 🔍 Telegram Diagnostic Tool ===")
    
    # 1. Load Environment
    loaded_files = env_discovery.initialize_environment()
    print(f"Loaded .env from: {loaded_files}")
    
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "NOT_SET")
    
    if not token:
        print("❌ ERROR: TELEGRAM_TOKEN is missing!")
        print("Please add 'TELEGRAM_TOKEN=your_bot_token' to your .env file.")
        return

    safe_token = str(token)
    print(f"✅ Token: {safe_token[:5]}...{safe_token[-5:]}")
    print(f"✅ Chat ID (Env): {chat_id}")

    # 2. Test Connection
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            bot_data = resp.json().get("result", {})
            print(f"✅ Connection successful! Bot Name: @{bot_data.get('username')}")
        else:
            print(f"❌ Connection failed: {resp.status_code} {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return

    # 3. Fetch Latest Updates (to find Chat ID)
    print("\n--- 🕵️ Searching for your Chat ID ---")
    print("Please send a message to your bot on Telegram NOW.")
    print("Waiting 15 seconds for updates...")
    
    url_updates = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url_updates, timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("result", [])
            if not results:
                print("⚠️ No recent messages found. Make sure you've sent a message to the bot.")
                print(f"Falling back to test message to: {chat_id}")
            else:
                last_update = results[-1]
                msg = last_update.get("message", {})
                found_id = msg.get("chat", {}).get("id")
                from_user = msg.get("from", {}).get("username", "Unknown")
                print(f"🎯 FOUND IT! Chat ID: {found_id} (from @{from_user})")
                print(f"Add this to your .env: TELEGRAM_CHAT_ID={found_id}")
                chat_id = str(found_id)
        else:
            print(f"❌ Failed to fetch updates: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error fetching updates: {e}")

    # 4. Send Test Message
    if chat_id != "NOT_SET":
        print(f"\n--- 📤 Sending Test Message to {chat_id} ---")
        url_send = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🛡️ **Sentinel Diagnostic**: If you see this, your Telegram alerts are FIXED! 🚀",
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url_send, json=payload, timeout=10)
            if resp.status_code == 200:
                print("💎 SUCCESS! Check your Telegram.")
            else:
                print(f"❌ Send failed: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"❌ Send error: {e}")

if __name__ == "__main__":
    debug_telegram()
