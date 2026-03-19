import os
import json
from google import genai

def list_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set")
        return

    client = genai.Client(api_key=api_key)
    print("Listing available models...")
    try:
        for model in client.models.list():
            print(f"- {model.name} (DisplayName: {model.display_name})")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
