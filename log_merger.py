"""
log_merger.py — Consolidated Artifact Merger for Trinity Pulse
Part of the God-Level Autonomous GHA Pipeline.

This script merges multiple evolution_log.json artifacts from parallel
batches into a single source of truth for the submission_burst.py.
"""
import json
import os
from pathlib import Path
from datetime import datetime

def merge_logs(input_dir: str, output_file: str):
    print(f"--- 🌀 TRINITY LOG MERGER: CONSOLIDATING BATCHES 🌀 ---")
    
    merged_data = {"brain": [], "numerai": []}
    
    # 1. Look for all .json files in the input directory
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Input directory {input_dir} not found. Skipping merge.")
        return

    log_files = list(input_path.glob("**/evolution_log.json"))
    print(f"Found {len(log_files)} batch logs to merge.")

    # 2. Extract and Deduplicate
    seen_ids = set()
    for lf in log_files:
        try:
            content = json.loads(lf.read_text(encoding="utf-8"))
            
            # Merge Brain entries
            for entry in content.get("brain", []):
                # Use expression + status + date as a proxy for uniqueness if ID is missing
                unique_key = entry.get("alpha_id") or f"{entry.get('expression')}_{entry.get('status')}"
                if unique_key not in seen_ids:
                    merged_data["brain"].append(entry)
                    seen_ids.add(unique_key)
            
            # Merge Numerai entries
            for entry in content.get("numerai", []):
                merged_data["numerai"].append(entry)
                
        except Exception as e:
            print(f"Error reading {lf}: {e}")

    # 3. Sort by timestamp
    merged_data["brain"].sort(key=lambda x: x.get("timestamp", ""))
    
    # 4. Limit to last 100 entries (prevent log bloat)
    merged_data["brain"] = merged_data["brain"][-100:]
    merged_data["numerai"] = merged_data["numerai"][-100:]

    # 5. Save Output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged_data, indent=2))
    
    print(f"Successfully merged {len(merged_data['brain'])} Brain alphas into {output_file}.")
    print("--- 🏁 MERGE COMPLETE 🏁 ---")

if __name__ == "__main__":
    # In GHA, artifacts are often downloaded into subdirectories of an 'artifacts' folder
    # Usage: python log_merger.py <input_dir> <output_file>
    import sys
    inp = sys.argv[1] if len(sys.argv) > 1 else "artifacts"
    out = sys.argv[2] if len(sys.argv) > 2 else "/home/runner/work/brainbot/brainbot/.antigravity/master/evolution_log.json"
    merge_logs(inp, out)
