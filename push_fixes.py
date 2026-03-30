import subprocess
import sys

def run_git(cmd_list):
    print(f"Running: {' '.join(cmd_list)}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

if __name__ == "__main__":
    files_to_add = [
        ".github/workflows/trinity_hyperscale.yml",
        "alpha_factory.py",
        "health_check.py",
        "verify_task.py",
        "update_state.py"
    ]
    
    if run_git(["git", "add"] + files_to_add):
        if run_git(["git", "commit", "-m", "chore: Trinity Pulse Stability Fixes (Node 24, Pathing)"]):
            if run_git(["git", "push", "origin", "master"]):
                print("Successfully pushed fixes to GitHub.")
                sys.exit(0)
    
    print("Failed to push fixes.")
    sys.exit(1)
