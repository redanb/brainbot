---
description: Standardize paths using `get_master_dir` to avoid Windows/Linux cross-env failures.
---

1. Import `env_discovery` and use `get_master_dir()`.
2. Replace hardcoded strings like 'C:\\' with dynamic path joining.
3. Verify cross-os compatibility before commit.