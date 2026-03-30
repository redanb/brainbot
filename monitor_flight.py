import subprocess
import sys
import time
import os

cmd = [
    sys.executable, 
    r"C:\Users\admin\.antigravity\master\antigravity_shell.py", 
    f"python c:\\Users\\admin\\Downloads\\medsumag1\\brainbot\\alpha_factory.py --max_calls 3 --parallel 1"
]

print(f"Launching: {' '.join(cmd)}")
# Using unbuffered output
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

# Write to a local file we can tail
log_path = r"c:\Users\admin\Downloads\medsumag1\brainbot\test_flight.log"
with open(log_path, "w", encoding="utf-8") as f:
    f.write(f"--- TEST FLIGHT STARTED {time.ctime()} ---\n")

for line in process.stdout:
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)

process.wait()
print(f"Process exited with code {process.returncode}")
