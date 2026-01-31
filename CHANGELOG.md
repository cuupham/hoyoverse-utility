# Changelog

## [2026-01-31]
### Added
- **ZZZ Stealth Mode**: Optimized headers (`x-rpc-app_version`, `x-rpc-page_info`, `priority`, `x-rpc-timezone`) to match real App behavior.
- **Dynamic Page Info**: Added `get_page_info` to `GameInfo` model to support game-specific `gameId` and `pageType`.
- **ZZZ Audit & Bug Fix**: Improved retcode handling in `redeem.py` to prioritize server messages and fixed `-2017` translation mismatch ("Already redeemed" vs "Code chưa active").
- **Log Optimization**: Main display now hides accounts without character/UIDs in the Redeem section for a cleaner report.

### Changed
- Default timezone updated to `Asia/Saigon` to match user environment.
- Headers now include `priority: u=1, i`.

### Planned
- **Advanced Stealth**: Dynamic version detection via iTunes Search API and automated system timezone detection.
