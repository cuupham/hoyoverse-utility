"""Giá trị mặc định không phụ thuộc module khác - tránh circular import.

Các constant dùng tại runtime bởi utils (vd: headers) khi config chưa load
nên đặt tại đây. Config tập trung các setting còn lại.
"""
# Fallback khi không parse được version từ User-Agent (Chrome/xx)
DEFAULT_CHROME_VERSION = "142"

# JSON compact separators - dùng chung cho get_page_info, source_info (tránh import config từ game)
JSON_SEPARATORS = (",", ":")

# Default x-rpc-source_info khi không cần source (fetch CDKeys, v.v.) - single source cho build_rpc_headers
DEFAULT_SOURCE_INFO = '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}'
