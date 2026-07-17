@echo off
chcp 65001 >nul
echo ==========================================
echo CareerCraft Agent - Windows 打包脚本
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请安装 Python 3.11+
    exit /b 1
)

REM 检查虚拟环境
if exist .venv\Scripts\python.exe (
    echo 使用虚拟环境: .venv
    set PYTHON=.venv\Scripts\python.exe
) else if exist venv\Scripts\python.exe (
    echo 使用虚拟环境: venv
    set PYTHON=venv\Scripts\python.exe
) else (
    echo 使用系统 Python
    set PYTHON=python
)

REM 检查 PyInstaller
%PYTHON% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 安装 PyInstaller...
    %PYTHON% -m pip install pyinstaller -q
)

REM 执行打包
echo.
echo 开始打包 WebView 版本...
%PYTHON% build.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    exit /b 1
)

echo.
echo ==========================================
echo 打包完成！
echo 输出目录: dist\CareerCraftAgent\
echo ==========================================
pause
