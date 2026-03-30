import os
import json
import requests
import logging

def call_failsafe_gemini(system_prompt: str, user_prompt: str):
    """
    Direct HTTPS call to Gemini API. Zero local dependencies.
    Used when llm_router.py is broken.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"text": "ERROR: No GEMINI_API_KEY found in environment."}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Simple construction to avoid complex JSON objects that might fail in restricted envs
    full_prompt = f"{system_prompt}\n\nCONTEXT FROM BROKEN PIPELINE:\n{user_prompt}"
    
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        
        # Extract text safely
        try:
            text = data['candidates'][0]['content']['parts'][0]['text']
            return {"text": text, "provider": "failsafe_gemini"}
        except (KeyError, IndexError):
            return {"text": f"ERROR: Malformed API response: {data}"}
            
    except Exception as e:
        return {"text": f"ERROR: Failsafe API connection failed: {e}"}

if __name__ == "__main__":
    # Test
    print(call_failsafe_gemini("You are a helpful assistant.", "Hello world."))
