# 💡 BRIEF DRAFT: HoYoLab Auto Tool Evolution

**Ngày tạo:** 2026-01-31
**Trình trạng:** Đang Brainstorm

---

## 1. TỔNG QUAN HIỆN TẠI
- **Dự án:** HoYoLab Auto Tool.
- **Tính năng chính:** Tự động điểm danh & nhập code cho Genshin Impact, Honkai: Star Rail, Zenless Zone Zero.
- **Nền tảng:** Python CLI, chạy qua GitHub Actions.
- **Ưu điểm:** Song song hóa (Parallel), hỗ trợ nhiều tài khoản, logic skip code thông minh.

## 2. CÁC HƯỚNG MỞ RỘNG TIỀM NĂNG (Gợi ý)
Dựa trên kiến trúc hiện tại, đây là một số hướng chúng ta có thể thảo luận:

### A. Notification & Integration
- [ ] **Notifier:** Gửi kết quả qua Telegram, Discord, hoặc Pushback sau khi chạy xong.
- [ ] **Health Check:** Cảnh báo khi cookie hết hạn hoặc bị lỗi.

### B. New Content Support
- [ ] **Honkai Impact 3rd:** Thêm hỗ trợ cho game cũ nhưng vẫn còn cộng đồng lớn.
- [ ] **Hoyolab Community Features:** Tự động like/share bài viết để lấy exp Hoyolab.

### C. UX & UI Evolution
- [ ] **Web Dashboard:** Một giao diện web đơn giản (Vite/NextJS) để user dán cookie và quản lý các account mà không cần sờ vào GitHub Secrets.
- [ ] **Dockerization:** Đóng gói tool để chạy trên NAS, VPS dễ dàng hơn.

---

## ❓ CÂU HỎI BRAINSTORM
1. Bạn muốn tập trung vào hướng nào trong các hướng trên, hoặc có ý tưởng nào hoàn toàn khác không?
2. Bạn muốn giữ tool là một script cá nhân hay muốn biến nó thành một dịch vụ cho nhiều người dùng hơn?
