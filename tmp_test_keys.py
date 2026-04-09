import os
import requests
from dotenv import load_dotenv

load_dotenv(r"C:\Users\admin\.antigravity\master\.env")

print("--- API Key Diagnostics ---")

# 1. Anthropic
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key:
    # Use headers required by Anthropic
    headers = {
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Hello"}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            print("[PASS] Anthropic API Key is WORKING.")
        else:
            print(f"[FAIL] Anthropic API Key Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[FAIL] Anthropic Request Error: {e}")
else:
    print("[-] ANTHROPIC_API_KEY not found in .env")

# 2. Mistral
mistral_key = os.getenv("MISTRAL_API_KEY")
if mistral_key:
    headers = {
        "Authorization": f"Bearer {mistral_key}",
        "Content-Type": "application/json"
    }
    data = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}
    try:
        r = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            print("[PASS] Mistral API Key is WORKING.")
        else:
            print(f"[FAIL] Mistral API Key Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[FAIL] Mistral Request Error: {e}")
else:
    print("[-] MISTRAL_API_KEY not found in .env")

# 3. xAI (Grok)
xai_key = os.getenv("XAI_API_KEY")
if xai_key:
    headers = {
        "Authorization": f"Bearer {xai_key}",
        "Content-Type": "application/json"
    }
    data = {"model": "grok-2-latest", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}
    try:
        # Note: xAI API endpoint is api.x.ai/v1/chat/completions
        r = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            print("[PASS] xAI (Grok) API Key is WORKING.")
        else:
            print(f"[FAIL] xAI (Grok) API Key Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[FAIL] xAI Request Error: {e}")
else:
    print("[-] XAI_API_KEY not found in .env")
