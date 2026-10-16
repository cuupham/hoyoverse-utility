# Tests

The test suite is split by purpose:

- `tests/unit/` covers models, API wrappers, orchestration, display, and
  session behavior with mocked responses.
- `tests/integration/` covers the mocked application flow across modules.
- `tests/api_health/` contains live, read-only checks for cookie validation,
  check-in info, CDKey fetch, UID fetch, and response shape. It does not submit
  a sign or redeem request.
- `tests/auth/cookies.ps1.example` is the local cookie template. Copy it to
  `tests/auth/.env.ps1`; the fixture reads that file only when `ACC_*`
  environment variables are not already set.

Do not commit `.env.ps1` or cookie values. `tests/support/accounts.py` owns local test/debug loading; `Account.from_cookie_string()` owns cookie validation. Loading is lazy, so default mocked tests do not read credentials. Invalid configured credentials fail explicitly instead of silently falling back to a different account.

Install developer tools with `pip install -r requirements-dev.txt`. Runtime pins are inherited from the root runtime manifest. CI also runs Black, Ruff and strict source mypy on Python 3.10/3.13.

Run mocked tests without credentials:

```powershell
python -m pytest tests/unit/ tests/integration/
```

Run read-only live checks with credentials loaded in the current PowerShell
session or from `tests/auth/.env.ps1`:

```powershell
python -m pytest tests/api_health/ -m live -v
```

The live suite may skip when no account is available. A live check confirms the
observed read response and wrapper contract; it is not proof of successful
check-in or redemption writes.

The debug script shares the live loader and production read wrappers. `python tests/scripts/debug_checkin_info.py --help` works without credentials and from another working directory. Its output contains region names and check-in state, never raw cookies, account IDs, nicknames or UIDs.

Unit files are grouped by owner: accounts, client, request builder/browser headers, metadata, environment/timekeeping, check-in, fetch, redemption, display, logging and orchestration. `test_provider_contracts.py` exercises provider-shaped fixtures; it is not a live provider certification. `test_operation_outcomes.py` covers error classification and run status.
