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
pip install -r requirements.txt

# Tests use mock data — no cookie required
pip install pytest pytest-asyncio pytest-cov
python -m pytest --cov=src --cov-report=term-missing
```

Live API-health tests additionally need real cookies — set `ACC_1` in your environment or create `tests/auth/.env.ps1`. Never commit yours (see [`tests/auth/cookies.ps1.example`](tests/auth/cookies.ps1.example)).

## Code style

- Format with **black** (`pip install black; black src tests`)
- **Type hints required** on all functions (matches existing codebase)
- Keep modules small and focused; shared constants go in `src/constants.py`, config in `src/config.py`

## Pull requests

Use the PR template. CI must pass (tests + coverage gate). One logical change per PR keeps review fast.

## Reporting issues

Use the issue templates. **Never paste cookies, account IDs, or emails** into issues or logs — run logs already mask emails, keep it that way.
