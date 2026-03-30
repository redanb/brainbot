import sys
from pathlib import Path

# Fix module resolution for local imports
sys.path.append(str(Path(__file__).resolve().parent))

import os
import re
import json
import logging
try:
    from llm_router import route_query
except ImportError:
    try:
        from failsafe_llm import call_failsafe_gemini as route_query
    except ImportError:
        def route_query(*args, **kwargs): return {"text": "Import Error"}

import env_discovery

# Paths
BRAIN_DIR = str(Path(__file__).resolve().parent)
SKILLS_DIR = str(Path(BRAIN_DIR) / ".agents" / "workflows")
MASTER_DIR = str(env_discovery.get_master_dir())

# Log dir is session specific, ideally passed but let's assume it can be discovered or defaults to the first artifact dir found
def find_log_dir():
    # If in a session, we might have a specific log dir. For now, fallback to the current BRAIN artifact dir.
    expected = Path.home() / ".gemini" / "antigravity" / "brain"
    if expected.exists():
        dirs = [d for d in expected.iterdir() if d.is_dir()]
        if dirs:
            return str(dirs[-1]) # Use latest session dir
    return str(MASTER_DIR)

LOG_DIR = find_log_dir()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SkillFactory")

def extract_skills():
    """
    Scrapes history and uses LLM to identify reusable skills.
    """
    if not os.path.exists(SKILLS_DIR):
        os.makedirs(SKILLS_DIR, exist_ok=True)

    # Gather data
    context = ""
    paths = [
        os.path.join(MASTER_DIR, "RESUME_CONTEXT.md"),
        os.path.join(LOG_DIR, "walkthrough.md"),
        os.path.join(LOG_DIR, "task.md")
    ]
    
    for p in paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                content = str(f.read())
                context = str(context) + f"\n--- {os.path.basename(p)} ---\n" + content

    if not context:
        logger.warning("No context found to extract skills from.")
        return

    system_prompt = """
You are the Agent Skill Architect. 
Your goal is to extract REUSABLE workflow patterns from the provided logs.
A "Skill" is a multi-step process that solved a specific technical problem (e.g., Fixing a specific error type, configuring a new provider).

Output Format:
A JSON list of skills, each with:
- "name": PascalCase skill name.
- "description": Short 1-sentence purpose.
- "steps": List of specific markdown-formatted steps.
- "filename": skill_name_lowercase.md

Only extract skills that were SUCCESSFULLY completed.
"""
    
    user_prompt = f"Analyze the following logs and extract reusable Agent Skills:\n\n{context}"
    
    logger.info("Calling LLM for skill extraction...")
    try:
        response = route_query(system_prompt, user_prompt, depth="REASONING")
    except Exception as e:
        logger.error(f"Primary route_query failed: {e}. Falling back...")
        from failsafe_llm import call_failsafe_gemini
        response = call_failsafe_gemini(system_prompt, user_prompt)
    
    text = str(response.get("text", ""))
    
    # Even MORE robust extraction: strip markdown backticks first
    text = re.sub(r"```json|```", "", text)
    
    json_blocks = re.findall(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if not json_blocks:
        # Try finding individual objects if the list is missing
        json_blocks = re.findall(r"\{\s*\"name\".*?\}", text, re.DOTALL)
        if not json_blocks:
            logger.error(f"Failed to find any JSON-like blocks in LLM response: {text[:200]}...")
            # Bootstrap manual core skills if extraction fails
            bootstrap_core_skills()
            return []

    processed_skills = []
    for block in json_blocks:
        try:
            # Simple cleanup for common LLM JSON errors (trailing commas, etc.)
            block = re.sub(r",\s*([\]\}])", r"\1", block)
            data = json.loads(block)
            if isinstance(data, list):
                processed_skills.extend(data)
            else:
                processed_skills.append(data)
        except Exception as e:
            logger.warning(f"Failed to parse a specific JSON block: {e}")
            continue

    if not processed_skills:
        bootstrap_core_skills()
    else:
        for skill in processed_skills:
            save_skill(skill)

def bootstrap_core_skills():
    """Manually defines critical skills if LLM fails."""
    logger.info("Bootstrapping core skills...")
    core_skills = [
        {
            "name": "NumeraiAuthFix",
            "description": "Diagnostic and fix path for Numerai permission 'read_user_info' errors.",
            "steps": [
                "Run `test_numerai_auth.py` to confirm permission levels.",
                "Verify `.env` in `C:\\Users\\admin\\.antigravity\\master` contains correct credentials.",
                "Ensure keys have 'read_user_info' and 'upload_submissions' scopes checked on Numerai dashboard."
            ],
            "filename": "numerai_auth_fix.md"
        },
        {
            "name": "PathAgnosticRefactor",
            "description": "Standardize paths using `get_master_dir` to avoid Windows/Linux cross-env failures.",
            "steps": [
                "Import `env_discovery` and use `get_master_dir()`.",
                "Replace hardcoded strings like 'C:\\\\' with dynamic path joining.",
                "Verify cross-os compatibility before commit."
            ],
            "filename": "path_agnostic_refactor.md"
        }
    ]
    for skill in core_skills:
        save_skill(skill)

def save_skill(skill):
    """Saves a skill to the workflows directory."""
    filepath = os.path.join(SKILLS_DIR, skill['filename'])
    
    content = f"---\ndescription: {skill['description']}\n---\n\n"
    content += "\n".join([f"{i+1}. {step}" for i, step in enumerate(skill['steps'])])
    
    with open(filepath, "w") as f:
        f.write(content)
    logger.info(f"Saved skill: {skill['name']} to {filepath}")

if __name__ == "__main__":
    extract_skills()
