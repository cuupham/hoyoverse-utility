# Error handling and CLI results

## Result boundaries

The executable contracts live in [results.py](../src/models/results.py):

- `HttpCallResult.success`: the HTTP request succeeded and its body was decoded as JSON. Its data is still an unparsed provider envelope.
- `ProviderResult.success`: envelope and endpoint-specific data are usable. Empty successful collections differ from errors. `error_kind` preserves transport/schema/provider provenance.
- `CookieValidationResult.status`: valid, invalid_credentials, or check_failed. A timeout is a failed validation attempt, not proof that credentials are invalid.
- `CheckinResult.status`: claimed, already_claimed, no_character, challenge, or failed. `action_required` is set for a provider challenge.
- `RedemptionData`: usable codes, per-account UID mappings, and unrecovered fetch errors.
- `AccountValidationResult`: usable accounts plus account validation failures.

`message` and `retcode` preserve provider detail. Numeric redemption retcodes are not a published per-game contract in this project; they must not infer global expiry or region eligibility. The same rejected code remains eligible for an independent request in another region.

## Exit status

[main.py](../src/main.py) lets healthy independent work finish, then closes the session before the final status:

| Outcome | Run status |
|---|---|
| No configured/usable accounts | Exit 1 |
| Any malformed account or failed account validation, including partial failures | Exit 1; valid accounts continue |
| Unrecovered code/UID fetch error | Exit 1; usable data remains available |
| Check-in transport/schema/provider failure | Exit 1 |
| Check-in challenge requiring user action | Exit 1; no challenge bypass |
| Known check-in no-character response | Report separately; does not fail an otherwise healthy run |
| Already claimed or newly claimed check-in | Success |
| Redemption transport/schema failure | Exit 1; independent codes/regions continue |
| Provider-level redemption rejection | Preserve message/retcode; does not fail an otherwise healthy run |
| Codes exist but no account has any matching code/game/UID combination | Report the condition; does not fail an otherwise healthy run |
| Some accounts/games have no character, while other combinations are eligible | Skip the unmatched combinations; redeem eligible ones normally |
| Healthy reads with no available codes | Exit 0 |

Provider rejection and operational failure remain distinct even when both have success=false. Internal callers and tests must preserve error_kind and status rather than reconstruct them from message text.

## Ambiguous sign outcomes

Sign POST is never automatically retried. Timeout/network/HTTP/JSON/schema failures and an already-claimed race trigger an info reconciliation read. Invalid inner sign data or malformed nested risk data follow the same rule. If the read confirms signed state, report already_claimed with the confirmed day; otherwise retain failure. A provider challenge is reported as action-required and never becomes success.

## Retry and timeout policy

[client.py](../src/api/client.py) owns transport behavior; [config.py](../src/config.py) owns limits.

- MAX_ATTEMPTS includes the first attempt and must be at least one.
- Automatic retries apply only to safe GET/HEAD requests when retry is enabled. The mutating redeem GET explicitly disables retry.
- HTTP 429/500/502/503/504 and connection/payload/timeout failures use bounded retry behavior.
- Retry-After seconds or HTTP dates take precedence over default backoff. A delay exceeding REQUEST_TIMEOUT_SECONDS returns the failure instead of retrying early or waiting indefinitely.
- Timeouts bound individual attempts, not the entire sequence including backoff. The existing per-attempt timeout floor is preserved.
- JSON/envelope failures have separate owners: transport decodes JSON, the provider parser validates envelope/retcode, and endpoint wrappers validate inner data.

## Presentation and logging

[display.py](../src/utils/display.py) owns tables. Check-in labels use status, independent of provider-message language. Redemption failures show retcode/provider message within table width. Common labels and fallback messages are owned by SYSTEM_MESSAGES in config; provider messages remain provider-owned. Layout widths are local presentation concerns.

API operations return results instead of printing concurrent progress lines. The CLI logs accounts, check-in and redemption sections in order. The named logger and execution context live in [logger.py](../src/utils/logger.py). Cookies/headers are never directly logged; unexpected exception text is sanitized. This is not a claim that arbitrary provider text has been fully scrubbed of every possible identifier.
