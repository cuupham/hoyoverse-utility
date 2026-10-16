"""Shared JSON serialization and browser fallback constants."""

# Fallback khi không parse được version từ User-Agent (Chrome/xx)
DEFAULT_CHROME_VERSION = "142"

# Compact JSON shared by page-info and source-info request fields.
JSON_SEPARATORS = (",", ":")
