# TLMTool 2.1.2 — 1:1 compatibility clone

Repository phát triển lại TLMTool 2.1.2 theo **bề mặt chức năng và hành vi quan sát được**, dựa trên bộ TLMTool 2.1.2, source 12.4.2 và knowledge base `clinent-game-than-long-DATA-2222` do chủ dự án cung cấp.

## Nguyên tắc cố định

- Target sản phẩm: **TLMTool 2.1.2**, không tự thêm tab/chức năng người dùng ngoài baseline 2.1.2.
- Không tự lược bỏ control, tùy chọn hay workflow đã được xác minh từ binary/screenshot/runtime evidence.
- `BUILD PASS` không được ghi thành `RUNTIME PASS`.
- Mỗi PID game có state riêng; tối đa một mutable action đang chạy trên một PID.
- Captcha chỉ dừng/chờ người dùng xử lý; không tự giải/bypass.
- Ưu tiên semantic game API và state proof; không coi sleep/"đã gửi lệnh" là bằng chứng thành công.

## Chạy source UI

```powershell
py -3.10 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

## Build Windows

Workflow GitHub Actions `build-windows.yml` tạo bản standalone bằng Nuitka, phù hợp cách đóng gói Python/Tkinter của TLMTool gốc.

## Tài liệu bắt buộc trước khi sửa

1. `PROJECT_KNOWLEDGE.md`
2. `TASKS.md`
3. `CHANGELOG.md`
4. docs feature tương ứng.

Trạng thái hiện tại: **BUILD/SYNTAX VALIDATED; RUNTIME UNTESTED** cho phần clone mới.
