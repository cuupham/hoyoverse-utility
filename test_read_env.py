import os

SECRET_KEYS = [
    "HOYOVERSE_COOKIE_1",
    "HOYOVERSE_COOKIE_2",
]

for key in SECRET_KEYS:
    value = os.getenv(key)
    if value is None:
        print(f"{key}=<MISSING>")
    else:
        # in độ dài + vài ký tự đầu/cuối cho debug
        prefix = value[:5]
        suffix = value[-5:] if len(value) > 5 else ""
        print(f"{key} exists: len={len(value)}, preview={prefix}...{suffix}")
