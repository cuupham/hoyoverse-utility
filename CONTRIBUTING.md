# Contributing

Thanks for your interest in improving **hoyoverse-utility**! This guide is deliberately short — please read it before opening an issue or PR.

## ⚠️ First, a boundary

This tool automates ToS-gray-area game actions. Contributions are welcome for:

- 🌍 New game **region** support (`REGIONS` mapping in `src/models/game.py`)
- 📖 Documentation improvements & translations
- 🐛 Bug fixes (especially after HoYoLAB API changes)
- ♻️ Refactors that reduce detection surface or improve reliability

Contributions that are **not** welcome: new automation features that increase ToS risk (e.g., auto-claiming events, posting, purchases).

## Local setup

Full instructions live in the [README](README.md#local-development) — they must work on first try; if they don't, that's a bug worth reporting.

```bash
python -m venv .venv
.\.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
```

Checks and test commands match [`.github/workflows/test.yml`](.github/workflows/test.yml); tests use mock data, no cookie required.

Live API-health tests additionally need real cookies — set `ACC_1` in your environment or create `tests/auth/.env.ps1`. Never commit yours (see [`tests/auth/cookies.ps1.example`](tests/auth/cookies.ps1.example)).

## Code style

- Format with **black** (`pip install black; black src tests`)
- Runtime code must pass strict source typechecking; keep required TypedDict fields compatible with Python 3.10.
- Keep modules small and focused. Game metadata belongs in `src/models/game.py`, shared results in `src/models/results.py`, request construction in `src/api/request_builder.py`, and settings/messages in `src/config.py`.
- Runtime dependency pins belong only in `requirements.txt`; `requirements-dev.txt` references that file.
- Keep provider wire keys and ACC_* names stable; internal names use snake_case. Tests should describe the behavior they assert, not coverage targets or historical audit labels.

## Pull requests

Use the PR template. CI must pass formatting, lint, strict source typing, tests and the coverage gate on Python 3.10 and 3.13. One logical change per PR keeps review fast.

## Reporting issues

Use the issue templates. **Never paste cookies, account IDs, or emails** into issues or logs — run logs already mask emails, keep it that way.
