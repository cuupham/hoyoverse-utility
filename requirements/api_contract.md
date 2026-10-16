# API contract and configuration

This document describes the client's current executable contract, not a published HoYoLAB API specification. Provider wire fields and route identifiers remain unchanged unless source evidence supports a deliberate update.

## Ownership

- [config.py](../src/config.py): typed endpoint groups, origins, static headers, RPC values and account-wide page metadata.
- [game.py](../src/models/game.py): game IDs, activity IDs, game_biz, sign_game and region mappings. Reverse lookups derive from these definitions.
- [request_builder.py](../src/api/request_builder.py): consistent Windows desktop Chrome headers, RPC metadata, page info and sign request construction.
- [client.py](../src/api/client.py): request_json HTTP/JSON transport and parse_provider_envelope provider validation.
- [results.py](../src/models/results.py): typed transport/provider/application outcomes.

Endpoint URLs and headers are linked to their source owner rather than copied into parallel implementations here. Browser profiles come from the installed fake-useragent dataset, constrained to Chrome/Windows/desktop; this does not promise the newest Chrome release. Client hints and RPC system version describe that same profile. Time headers use the configured timezone via [timekeeping.py](../src/utils/timekeeping.py).

## Provider envelope

Transport success means a successful HTTP status and decoded JSON. The provider parser then requires an object with an integer retcode; booleans and string numbers are invalid. Nonzero retcodes preserve a nonempty provider message or use a numeric fallback. A successful inner data payload must be an object, except redemption may explicitly allow null data. A malformed envelope/payload is an invalid_response error, not a successful empty collection.

## Cookie validation

Owner: [check_cookie](../src/api/checkin.py), URLS.check_cookie, GET.

Uses account-wide page information (build_page_info without a game) and source information for the account. It does not send an app-version header. A valid response requires retcode 0 and a nonempty string email_mask. The known login rejection (-100) produces invalid_credentials; transport/schema/other provider failures produce check_failed. Validation failures carry their message to the CLI and cannot silently disappear behind the valid-account list.

## Check-in information and sign

Owner: [checkin.py](../src/api/checkin.py), URLS.checkin_info / URLS.checkin_sign.

Info GET supplies act_id and RPC_LANGUAGE, with signgame derived from the selected game. It requires a real boolean is_sign and a nonnegative integer total_sign_day. The known no-character retcode (-10002) is classified at this API boundary; presentation never guesses from English text.

Sign POST is one attempt. Game-specific requests are built by build_sign_headers, build_sign_payload and build_sign_params:

- Genshin sends its activity ID in JSON and RPC_LANGUAGE as a query parameter, plus its existing specific content-type and empty app-version/device-name fields.
- Star Rail and ZZZ include the language in JSON.
- The game parameter determines both its metadata and signgame header; no second GameInfo argument can disagree with it.

Risk is read from gt_result for Genshin or the relevant Luna response fields. Risk/challenge results set status=challenge, action_required=true and success=false, without incrementing the day. Ambiguous transport or schema outcomes, including invalid inner/nested payloads, reconcile through info GET without resubmitting POST. See [error handling](error_codes.md).

## Code discovery

Owner: [fetch_cdkeys](../src/api/redeem_fetch.py), URLS.fetch_cdkeys, GET with game_id.

The wrapper requires a modules list. Missing/null exchange_group or bonuses and absent exchange_code contribute no code. Malformed present container types or non-string exchange_code are schema failures. Nonempty codes are trimmed and deduplicated.

Per-game fallback is owned by [main.py](../src/main.py): try accounts sequentially until a nonempty success, retaining successful empty results separately from errors. Different games remain concurrent. Publicly discovered codes are then shared across usable accounts.

## UID discovery

Owner: [fetch_all_uids](../src/api/redeem_fetch.py), URLS.fetch_uid, account-wide GET without region/game_biz parameters.

Requires a list of role objects. Supported roles need valid game_biz, string region and numeric-string game_uid. Unsupported games/regions are ignored; malformed supported role data fails explicitly. GAME_BY_BIZ and REGION_CODE_BY_VALUE map provider identifiers to Game and short region code. A successful empty mapping means no supported characters; a failed lookup is not interpreted as absence of characters.

## Redemption

Owner: [redeem_exchange.py](../src/api/redeem_exchange.py), URLS.redeem, mutating GET with retry=false.

Wire params remain cdkey, game_biz, lang, region, t and uid. REDEEM_LANG is distinct from RPC_LANGUAGE. Short region codes are resolved through REGIONS before calling the provider. Successful null data is allowed for this acknowledgment; nonzero retcodes preserve message/retcode with error_kind=provider.

Games/accounts may run concurrently. Regions for one account/game and codes for a region run sequentially; the configured delay between codes remains. No rejection suppresses other codes or later regions, and no global-expiry cache is inferred from undocumented retcodes.

## Verification boundary

[Unit tests](../tests/unit/) use provider-shaped fixtures; [integration tests](../tests/integration/) exercise mocked module interactions. [API health tests](../tests/api_health/) perform live read-only checks only when explicitly selected and configured. They do not submit sign or redeem writes. Test/diagnostic credential setup is described in [tests/README.md](../tests/README.md).

A passing mocked suite does not prove current provider acceptance. Historical live evidence remains in local reports; fresh live verification must be reported separately from source-contract checks.
