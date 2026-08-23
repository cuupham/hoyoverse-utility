# Security Policy

## Reporting a vulnerability

Please use [GitHub's private vulnerability reporting](https://github.com/cuupham/hoyoverse-utility/security/advisories/new) to report security issues. This keeps details private until a fix is ready.

**Do not open a public issue for security problems.**

## ⚠️ CRITICAL — never share your cookies

HoYoLAB cookies (`ACC_*` values) are **full account credentials**. Anyone holding one can access and act on your game accounts.

- **NEVER paste cookies into issues, discussions, PRs, screenshots, or logs**
- If you accidentally exposed a cookie anywhere public, **log out of all sessions in HoYoLAB immediately** to invalidate it, then re-authenticate
- Run logs mask emails by design; keep it that way when attaching excerpts

## Scope

In scope:

- Cookie/credential leakage paths (logs, error messages, artifacts)
- Injection or unsafe handling of API responses
- Workflow privilege issues (e.g., secrets exposure via `toJSON(secrets)` patterns)
- Anything that could compromise a user's GitHub or HoYo account

Out of scope:

- HoYoLAB server-side vulnerabilities (report to HoYoverse)
- ToS questions (see the README disclaimer)

## Supported versions

Only the latest commit on `main` is supported — this project tracks live HoYoLAB APIs that change without notice.
