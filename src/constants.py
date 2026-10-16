"""Shared JSON serialization and browser fallback constants."""

# Fallback khi không parse được version từ User-Agent (Chrome/xx)
DEFAULT_CHROME_VERSION = "142"

# Compact JSON shared by page-info and source-info request fields.
JSON_SEPARATORS = (",", ":")

# Default x-rpc-source_info khi không cần source (fetch CDKeys, v.v.) - single source cho build_rpc_headers
DEFAULT_SOURCE_INFO = '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}'
