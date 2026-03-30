---
description: Diagnostic and fix path for Numerai permission 'read_user_info' errors.
---

1. Run `test_numerai_auth.py` to confirm permission levels.
2. Verify `.env` in `C:\Users\admin\.antigravity\master` contains correct credentials.
3. Ensure keys have 'read_user_info' and 'upload_submissions' scopes checked on Numerai dashboard.