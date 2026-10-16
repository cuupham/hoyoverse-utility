# System Architecture & Flows

## Application boundary

This is a Python CLI application, run locally or by GitHub Actions. It has no web frontend, HTTP server or database. `src/api/` contains outbound HoYoLAB adapters. CLI formatting is the presentation layer.

| Responsibility | Source owner |
|---|---|
| Entry point, account fallback, scheduling independent tasks, exit status | [main.py](../src/main.py) |
| Endpoint routes, timeouts, attempt limits, shared display messages | [config.py](../src/config.py) |
| Serialization and browser fallback constants | [constants.py](../src/constants.py) |
| Immutable account/cookie representation | [account.py](../src/models/account.py) |
| Game/region metadata and derived reverse lookups | [game.py](../src/models/game.py) |
| Transport/provider/application result contracts | [results.py](../src/models/results.py) |
| HTTP/JSON transport, retries, semaphore, session isolation, provider envelope parsing | [client.py](../src/api/client.py) |
| Consistent browser headers, RPC headers, page info, sign headers/payload | [request_builder.py](../src/api/request_builder.py) |
| Check-in orchestration and response interpretation | [checkin.py](../src/api/checkin.py) |
| Read-only code/role fetches | [redeem_fetch.py](../src/api/redeem_fetch.py) |
| Code redemption and per-region sequencing | [redeem_exchange.py](../src/api/redeem_exchange.py) |
| CLI tables and short status labels | [display.py](../src/utils/display.py) |
| Runtime ACC_* discovery | [environment.py](../src/utils/environment.py) |
| Shared timezone/clock fields | [timekeeping.py](../src/utils/timekeeping.py) |
| Ordered report logging and execution context | [logger.py](../src/utils/logger.py) |

Models do not import HTTP builders or generate requests. `GameInfo` holds provider identifiers; the request builder consumes it. Display consumes structured statuses and does not infer business state from translated messages.

## Main flow

1. Read nonempty ACC_* values and parse accounts. Invalid configuration remains a run failure; healthy accounts can continue.
2. Validate cookies concurrently. Credential invalidity and validation outages have separate statuses. If no account is usable, exit with code 1 after session cleanup.
3. Run check-in and redemption-data fetching concurrently.
4. Display check-in, fetched codes/regions and unrecovered fetch errors.
5. Redeem available codes for accounts with UIDs in matching games. Display results after execution.
6. Close the shared session, then return exit 0 or exit 1 according to the [error policy](error_codes.md).

## Concurrency and request lifecycle

- Check-in runs concurrently across accounts/games.
- Code discovery uses one sequential account fallback per game. A nonempty success stops fallback for that game. A successful empty response remains distinct from failure.
- Role discovery uses one account-wide request per account, mapping provider game/region identifiers through derived lookups.
- Accounts and games can redeem concurrently. Regions within one account/game and codes within a region run sequentially, retaining the configured delay between codes.
- Rejection of one code never suppresses another code or region. No undocumented global-expiry cache exists.
- Request permits are shared within the active event loop and reset when a different loop is used. Jitter and retry backoff occur outside the semaphore.
- A single shared aiohttp session reuses connections. `DummyCookieJar` prevents response cookies from crossing accounts; each request supplies its account cookie explicitly.
- Safe GET/HEAD reads have bounded attempts. Sign POST and mutating redeem GET use one attempt. Ambiguous sign responses use an info read, never another POST.

## Single sources of truth

Game metadata and region values live in `game.py`; reverse mappings derive from them. Endpoint groups in `config.py` are typed. Browser headers are generated once from a Windows desktop Chrome profile that agrees with RPC system fields and client hints. `parse_provider_envelope()` alone validates provider envelopes; endpoint wrappers validate their own inner payloads.

Runtime dependencies are pinned in [requirements.txt](../requirements.txt). [requirements-dev.txt](../requirements-dev.txt) references that manifest and adds testing/quality tools. [pyproject.toml](../pyproject.toml) owns format, lint and strict source typing settings. The [test workflow](../.github/workflows/test.yml) checks Python 3.10 and 3.13.

## Local verification tools and privacy

[tests/support/accounts.py](../tests/support/accounts.py) is the shared live-test/debug loader. It prefers ACC_* environment values and lazily reads `tests/auth/.env.ps1` only when no values are configured. It parses declarations without executing PowerShell. Invalid configured credentials fail explicitly.

Default mocked tests do not load credentials. Live API health tests and the diagnostic script perform read operations only. Diagnostics use production wrappers and show account aliases, game/region names and check-in state; they do not print cookies, raw account IDs, nicknames or UIDs. Do not commit credential files or share private credentials in logs/issues.

The [daily workflow](../.github/workflows/hoyo-flow.yml) explicitly exposes ACC_1 through ACC_4. Local environment discovery supports all nonempty ACC_* names. Workflow manifests, not copied documentation snippets, own the executable configuration.
