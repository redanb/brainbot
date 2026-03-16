"""
task_broker.py — Antigravity Task Classification & Delegation Logic
RULE-030: Governor-compliant parallelization.
"""
from enum import Enum
import sys
import os

class TaskCategory(Enum):
    SERIAL = "serial"      # Must run one at a time, blocks scheduler
    PARALLEL = "parallel"  # Can run in background threads/subprocesses
    CLOUD = "cloud"        # Delegated to external APIs/Agents

# Registry of tasks and their preferred execution model
TASK_REGISTRY = {
    "perplexity_auto_sync": TaskCategory.CLOUD,
    "hackathon_scanner":    TaskCategory.PARALLEL,
    "numerai_daily":        TaskCategory.SERIAL,    # High priority, needs local stability
    "intelligence_orchestrator": TaskCategory.PARALLEL,
    "alpha_factory":        TaskCategory.PARALLEL,
    "alpha_factory_hub":    TaskCategory.CLOUD,     # High CPU, delegate to cloud
    "numerai_smart_run":    TaskCategory.CLOUD,     # High CPU, delegate to cloud
    "digital_worker":      TaskCategory.PARALLEL
}

def get_task_category(task_name: str) -> TaskCategory:
    """Returns the category for a given task name."""
    return TASK_REGISTRY.get(task_name, TaskCategory.PARALLEL)

def should_delegate_to_cloud(task_name: str) -> bool:
    """Check if task can be offloaded to minimize local CPU load."""
    return get_task_category(task_name) == TaskCategory.CLOUD

if __name__ == "__main__":
    for t in TASK_REGISTRY:
        print(f"Task: {t:25} | Category: {get_task_category(t).value}")
