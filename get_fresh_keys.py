import webbrowser
import os
import time

def open_portals():
    portals = [
        ("Google AI Studio (Gemini 2.5/3)", "https://aistudio.google.com/"),
        ("Anthropic Console (Claude 3.7)", "https://console.anthropic.com/"),
        ("OpenRouter (Multi-Model Hub)", "https://openrouter.ai/keys"),
        ("Groq Cloud (Llama 4 Speed)", "https://console.groq.com/keys"),
        ("DeepSeek Platform (DeepSeek V3)", "https://platform.deepseek.com/api_keys"),
        ("Cerebras Cloud (Fast Inference)", "https://cloud.cerebras.ai/"),
        ("GitHub Models Marketplace", "https://github.com/marketplace/models")
    ]
    
    print("\n" + "="*50)
    print("      --- 10x KEY ACQUISITION DASHBOARD ---")
    print("="*50)
    print("\nThis script will open the 7 core developer portals for 2026.")
    print("1. Login to each portal.")
    print("2. Create a 'Trial' or 'Free Tier' API Key.")
    print("3. Paste them into your .env file in C:\\Users\\admin\\.antigravity\\master\\.env")
    input("\nPress ENTER to open all portals...")

    for name, url in portals:
        print(f"Opening: {name}...")
        webbrowser.open(url)
        time.sleep(1)

    print("\n" + "="*50)
    print("Keys successfully opened. Update your .env and run 'check_llm_status.py' to verify.")
    print("="*50)

if __name__ == "__main__":
    open_portals()
