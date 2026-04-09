import os
import json
from dotenv import load_dotenv

env_path = r"C:\Users\admin\.antigravity\master\.env"
mcp_path = r"C:\Users\admin\.gemini\antigravity\mcp_config.json"

print(f"Syncing MCP Config with .env...")

load_dotenv(env_path)
notion_token = os.getenv("NOTION_TOKEN")

if not notion_token:
    print("[-] NOTION_TOKEN not found in .env")
    exit(1)

try:
    with open(mcp_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Inject specifically to notion-mcp-server
    if "mcpServers" in config and "notion-mcp-server" in config["mcpServers"]:
        if "env" not in config["mcpServers"]["notion-mcp-server"]:
            config["mcpServers"]["notion-mcp-server"]["env"] = {}
        
        old_token = config["mcpServers"]["notion-mcp-server"]["env"].get("NOTION_TOKEN", "NONE")
        config["mcpServers"]["notion-mcp-server"]["env"]["NOTION_TOKEN"] = notion_token
        
        with open(mcp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
        print(f"[+] Successfully synced NOTION_TOKEN.")
        print(f"    OLD: {old_token[:15]}...")
        print(f"    NEW: {notion_token[:15]}...")
    else:
        print("[-] notion-mcp-server not configured in mcp_config.json")
except Exception as e:
    print(f"[-] Error syncing mcp_config.json: {e}")
