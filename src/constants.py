"""Giá trị mặc định không phụ thuộc module khác - tránh circular import.

Các constant dùng tại runtime bởi utils (vd: headers) khi config chưa load
nên đặt tại đây. Config tập trung các setting còn lại.
"""
# Fallback khi không parse được version từ User-Agent (Chrome/xx)
DEFAULT_CHROME_VERSION = "142"
