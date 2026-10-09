# EmailReader

[English](README.md) | [Tiếng Việt](README.vi.md) | **简体中文**

适用于 Windows 的多账号邮件阅读器，使用 Python 和 PySide6 构建。

## 主要功能

- 支持 Outlook/Hotmail 和自定义 IMAP 服务器。
- 单独添加账号，或从 TXT 文件导入账号列表。
- 阅读 HTML 邮件、搜索邮件和复制验证码。
- 保存账号和邮件缓存，启动时恢复上次会话。
- 每 10 秒自动刷新当前正在查看的账号。
- 深色界面，可自定义应用名称的文字颜色，并可选择阻止远程图片加载。
- 按 **Ctrl + W** 关闭应用。

## 从源码运行

需要 Windows 和 Python 3.11。

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 添加账号

选择 **Add accounts → Add single account**，或导入以下格式的 TXT 文件：

```text
email@example.com|password
```

Outlook 支持通过 Microsoft 设备代码登录。其他支持的 IMAP 服务器可在 **Advanced** 中配置。

## 使用 Nuitka 构建 Windows 可执行文件

```powershell
py -3.11 -m venv .build-venv
.build-venv\Scripts\python.exe -m pip install -r requirements.txt nuitka ordered-set zstandard
powershell -ExecutionPolicy Bypass -File .\build-nuitka.ps1
```

构建结果位于 `release/nuitka-*/main.dist/`。运行 `EmailReader.exe` 时，请保留整个文件夹及其内容。

## 数据

账号和邮件缓存保存在应用旁的 `data` 文件夹中。登录凭据通过 Windows DPAPI 保护，并与当前 Windows 用户绑定。升级时请保留 `data` 文件夹，以继续使用已保存的会话。

账号文件、邮件缓存、日志和构建产物已通过 `.gitignore` 排除，不会提交到 Git。
