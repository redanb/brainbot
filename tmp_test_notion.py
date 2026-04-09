import os
import requests
from dotenv import load_dotenv

load_dotenv(r"C:\Users\admin\.antigravity\master\.env")

print("--- Notion API connectivity test ---")

token = os.getenv("NOTION_TOKEN")
if not token:
    print("[-] NOTION_TOKEN not found in .env")
else:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    try:
        r = requests.get("https://api.notion.com/v1/users/me", headers=headers, timeout=10)
        if r.status_code == 200:
            print("[PASS] Notion Token is WORKING.")
            print(f"User Info: {r.json().get('name')} ({r.json().get('type')})")
        else:
            print(f"[FAIL] Notion API Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[FAIL] Notion Request Error: {e}")
