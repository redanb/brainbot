import os
import requests
import json

key = os.environ.get("CEREBRAS_API_KEY")
url = "https://api.cerebras.ai/v1/models"
headers = {"Authorization": f"Bearer {key}"}

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"Connection Error: {str(e)}")
