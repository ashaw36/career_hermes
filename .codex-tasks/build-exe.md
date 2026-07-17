# CareerCraft Agent — Windows EXE 打包任务

## 目标
将 CareerCraft Agent 打包为 Windows 可执行文件 (.exe)。

## 项目路径
`D:\workplace_for_hermes\career-agent`

## 安装依赖
如果 .venv 不存在或缺少依赖：
```bash
cd D:\workplace_for_hermes\career-agent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install pyinstaller
```

## 打包命令
```bash
cd D:\workplace_for_hermes\career-agent
.venv\Scripts\python build.py
```

## 打包配置说明
build.py 已更新，关键配置：
- 入口: src/main_webview.py (WebView 版)
- 资源: prototype/ 目录 (HTML 原型 + qwebchannel.js)
- 隐藏导入: PySide6.QtWebEngineWidgets, PySide6.QtWebChannel, PySide6.QtWebEngineCore, sqlalchemy.ext.asyncio, jinja2, keyring, httpx, pydantic, yaml, fpdf
- 收集全部 PySide6 (确保 QtWebEngine 进程被包含)
- 模式: --onedir --windowed

## 验证步骤
1. 确保 dist\CareerCraftAgent\ 目录生成
2. 确保 dist\CareerCraftAgent\prototype\ 存在且包含 ui-prototype.html 和 qwebchannel.js
3. 确保 dist\CareerCraftAgent\CareerCraftAgent.exe 存在
4. 运行 dist\CareerCraftAgent\CareerCraftAgent.exe 验证能启动（可能需要 QtWebEngine，看到窗口即可，不必完整操作）

## 注意
- 打包时会打印大量 PySide6 文件，正常
- 如果报错缺少某个隐藏导入，请记录并更新 build.py
- 打包完成后报告输出目录结构和 exe 大小
