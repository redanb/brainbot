import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
from alpha_factory import BrainAPI

try:
    api = BrainAPI()
    if api.session.cookies.get('BRAIN_SESSION'):
        print("SUCCESS: BRAIN_SESSION cookie found.")
    else:
        # Check for browser session file
        session_file = Path(r"C:\Users\admin\.antigravity\master\browser_sessions\wqb_session.json")
        if session_file.exists():
            print(f"INFO: Browser session file exists at {session_file}")
        else:
            print("FAILURE: No session cookie and no session file found.")
except Exception as e:
    print(f"ERROR: {e}")
