# EmailReader

[English](README.md) | **Tiếng Việt** | [简体中文](README.zh-CN.md)

Ứng dụng đọc email đa tài khoản trên Windows, xây dựng bằng Python và PySide6.

## Tính năng chính

- Hỗ trợ Outlook/Hotmail, Gmail, Yahoo và máy chủ IMAP tùy chỉnh.
- Thêm từng tài khoản hoặc nhập danh sách từ file TXT.
- Đọc thư HTML, tìm kiếm và sao chép mã xác minh.
- Lưu tài khoản, cache thư và khôi phục phiên khi mở lại app.
- Tự làm mới tài khoản đang xem mỗi 10 giây.
- Giao diện tối, chỉnh màu tên app và tùy chọn chặn ảnh từ xa.
- Nhấn **Ctrl + W** để đóng app.

## Chạy từ source

Yêu cầu Windows và Python 3.11.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Thêm tài khoản

Chọn **Add accounts → Add single account**, hoặc nhập file TXT theo định dạng:

```text
email@example.com|password
```

Outlook hỗ trợ đăng nhập bằng mã Microsoft. Với Gmail/Yahoo, sử dụng mật khẩu ứng dụng khi nhà cung cấp yêu cầu.

## Build exe bằng Nuitka

```powershell
py -3.11 -m venv .build-venv
.build-venv\Scripts\python.exe -m pip install -r requirements.txt nuitka ordered-set zstandard
powershell -ExecutionPolicy Bypass -File .\build-nuitka.ps1
```

Bản build nằm trong `release/nuitka-*/main.dist/`. Giữ nguyên toàn bộ thư mục khi chạy `EmailReader.exe`.

## Dữ liệu

Tài khoản và cache được lưu trong thư mục `data` cạnh app. Thông tin đăng nhập được bảo vệ bằng Windows DPAPI, gắn với người dùng Windows hiện tại. Khi nâng cấp, giữ lại thư mục `data` để tiếp tục dùng phiên đã lưu.

File tài khoản, cache, log và bản build được loại khỏi Git bằng `.gitignore`.
