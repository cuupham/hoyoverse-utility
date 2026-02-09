---
name: hoyoverse-refactor-selfcheck
description: Refactor và tự kiểm tra code trong project hoyoverse-utility (HoYoLab Auto Tool). Áp dụng khi sửa/bổ sung code trong src/, thêm tính năng, hoặc khi user yêu cầu refactor hoặc kiểm tra theo DRY, single source, clean code.
---

# Refactor & Self-Check (hoyoverse-utility)

## Khi nào dùng

- Sửa hoặc thêm code trong `src/`
- User yêu cầu refactor / review / self-check
- Chuẩn bị kết thúc task viết code

## Refactor trong phạm vi ảnh hưởng

Mỗi lần sửa code:

1. **Trùng logic / pattern** → Trích thành hàm dùng chung (vd trong `utils/helpers.py` hoặc module liên quan).
2. **Chuỗi hoặc số xuất hiện ≥ 2 nơi** → Đưa vào `src/config.py` hoặc `src/constants.py`, thay thế toàn bộ chỗ dùng.
3. **Đã có hàm/class tương tự** → Dùng hoặc mở rộng, không tạo mới trùng chức năng.
4. **File bị gọi bởi file khác** → Đảm bảo API (hàm public, return shape) không bị phá vỡ; nếu đổi, cập nhật chỗ gọi.

Phạm vi: file đang sửa + các file gọi nó hoặc cùng tính năng (vd cùng API check-in hoặc redeem).

## Single source

- URL, act_id, game_biz, region codes → `config.URLS`, `models/game.Game`, `REGIONS`.
- Timeout, retry, delay → `config` (SEMAPHORE_LIMIT, REDEEM_DELAY, REQUEST_TIMEOUT, …).
- Message/retcode mapping → `config.REDEEM_MESSAGES`, `SKIP_*_RETCODES`.
- Không thêm default hardcode trong business logic; thiếu config thì báo lỗi rõ ràng.

## Bước tự kiểm tra (checklist)

Trước khi coi task là xong, chạy lần lượt:

1. **Literal:** Có chuỗi/số xuất hiện ≥ 2 nơi không? → Đưa vào config/constants và thay thế hết.
2. **Logic trùng:** Có đoạn logic giống chỗ khác không? → Trích thành hàm dùng chung.
3. **API/state:** Có truy cập state nội bộ (private, `_internal`) từ bên ngoài không? → Expose qua getter hoặc API công khai.
4. **SPEC:** Thay đổi có khớp `docs/SPEC.md` (flow, API, headers, output format) không?
5. **Phạm vi:** Đã xét file gọi file vừa sửa và các file cùng tính năng chưa?
6. **Test:** Logic mới hoặc thay đổi behavior đã có test tương ứng chưa? Đã chạy `pytest tests -v` và pass chưa?

Chỉ coi xong khi không còn vi phạm trong phạm vi ảnh hưởng và test pass.

## Tham chiếu

- Cấu trúc và luồng: `docs/SPEC.md`
- Config và constants: `src/config.py`, `src/constants.py`, `src/models/game.py`
- Rule Cursor: `core-principles.mdc`, `python-src-conventions.mdc`, `testing.mdc`, `api-security.mdc`
