---
description: Resolves critical errors preventing autonomous execution in GitHub Actions, including path errors, import shadowing, and NameErrors.
---

1. Identify `AttributeError` in `trigger_github_workflow` and `WinError 267` (invalid directory) in `alpha_factory_hub`.
2. Update `cowork_scheduler.py` to correct the `brainbot_dir` path, resolving `WinError 267`.
3. Resolve `trigger_github_workflow` shadowing/import issue by implementing dynamic module loading via `importlib`.
4. Fix `NameError: Optional` in `llm_router.py` by moving type imports to the top level.
5. Add pre-commit syntax checks to `auto_fixer.py` to catch similar regressions early.
6. Verify fixes with a synthetic run.
7. Commit and push changes to resolve GHA failures.