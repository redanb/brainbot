
import os
import sys
import time
import requests
import logging
from pathlib import Path
import json
import subprocess

# Local imports
sys.path.append(str(Path.cwd()))
import env_discovery
from llm_router import route_query

log = logging.getLogger("AutoFixer")

class ContinuousFeedbackFixer:
    """
    Watches GitHub Actions for failures, analyzes logs via LLM, 
    and applies self-healing code patches autonomously.
    """
    def __init__(self, owner="redanb", repo="brainbot"):
        env_discovery.initialize_environment()
        self.github_token = os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            raise EnvironmentError("GITHUB_TOKEN is missing. Auto-fixer cannot read pipeline logs.")
        
        self.owner = owner
        self.repo = repo
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        
        setup_logging()

    def get_latest_failed_run(self):
        """Finds the most recent workflow run that failed."""
        url = f"{self.api_base}/actions/runs?status=failure&per_page=1"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("workflow_runs"):
                return data["workflow_runs"][0]
            return None
        except Exception as e:
            log.error(f"Error fetching GHA runs: {e}")
            return None

    def get_run_logs(self, run_id):
        """Fetches the log for a specific run and extracts the failure traces."""
        url = f"{self.api_base}/actions/runs/{run_id}/logs"
        log.info(f"Downloading ZIP logs for run {run_id}...")
        try:
            resp = requests.get(url, headers=self.headers, allow_redirects=True)
            resp.raise_for_status()
            
            import zipfile
            import io
            
            # Extract the zip in memory to find failed steps
            error_traces = []
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                # Often there are folders per job, look for text files
                for filename in z.namelist():
                    if filename.endswith(".txt"):
                        content = z.read(filename).decode("utf-8", errors="replace")
                        # Simple heuristic: grab the last 100 lines of any log that has 'Error:' or 'Exit code 1'
                        if "Error:" in content or "exit code 1" in content.lower() or "traceback" in content.lower():
                            lines = content.splitlines()[-100:]  # last 100 lines should have the trace
                            error_traces.append(f"--- Log File: {filename} ---\n" + "\n".join(lines))
                            if len(error_traces) >= 3:
                                break # Cap at 3 error logs to prevent massive prompts
            
            if not error_traces:
                return "No identifiable error stack traces found in ZIP, but the job failed."
                
            return "\n\n".join(error_traces)
        except Exception as e:
            log.error(f"Error fetching logs ZIP: {e}")
            return None

    def analyze_and_fix(self, run_data, summary):
        """Uses LLM to analyze the failure and generate a patch."""
        log.info("Analyzing failure via AI Router...")
        
        system_prompt = """You are an elite DevOps Autonomous Agent. 
Your goal is to analyze CI/CD pipeline failures and provide a DIRECT python script 
that fixes the issue.
DO NOT provide explanations. ONLY output valid Python code enclosed in ```python...``` markers.
The python code when executed locally MUST fix the code files (e.g. by using file reading/writing or regex replace)."""

        user_prompt = f"""
Pipeline failed!
Run ID: {run_data['id']}
Head Branch: {run_data['head_branch']}
Commit Message: {run_data['head_commit']['message']}

Failure Summary:
{summary}

Write a python script that will locally edit the necessary files to fix this issue.
Assume the script runs in the repository root.
"""
        response = route_query(system_prompt, user_prompt, depth="REASONING", preferred_provider="openrouter")
        text = response.get("text", "")
        
        # Extract python code
        import re
        match = re.search(r"```python(.*?)```", text, re.DOTALL)
        if match:
            fix_code = match.group(1).strip()
            log.info("Generated fix payload. Applying...")
            
            fix_script_path = Path.cwd() / "emergency_fix.py"
            fix_script_path.write_text(fix_code, encoding="utf-8")
            
            # Execute the fix
            try:
                subprocess.run([sys.executable, "emergency_fix.py"], check=True)
                log.info("Fix applied successfully. Committing and pushing...")
                
                # Commit and push
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(["git", "commit", "-m", f"Auto-Fix: Corrected pipeline failure {run_data['id']}"], check=True)
                subprocess.run(["git", "push"], check=True)
                log.info("Self-healing sequence complete.")
                
            except subprocess.CalledProcessError as e:
                log.error(f"Failed to apply or push fix: {e}")
            finally:
                if fix_script_path.exists():
                    fix_script_path.unlink()
        else:
            log.error("AI failed to generate a valid python fix script.")
            log.debug(f"AI Output: {text}")

    def run_cycle(self):
        log.info("Checking for new pipeline failures...")
        run = self.get_latest_failed_run()
        if not run:
            log.info("No failed runs found. Pipeline is healthy.")
            return
            
        # Check if we already tried to fix this
        last_fixed_file = Path.cwd() / ".last_autofix_run"
        if last_fixed_file.exists():
            last_id = last_fixed_file.read_text().strip()
            if str(run['id']) == last_id:
                log.info(f"Already attempted to fix run {run['id']}. Skipping to prevent loop.")
                return
                
        summary = self.get_run_logs(run['id'])
        if summary:
            self.analyze_and_fix(run, summary)
            last_fixed_file.write_text(str(run['id']))

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    fixer = ContinuousFeedbackFixer()
    # Can be run in a loop or via cron
    fixer.run_cycle()
