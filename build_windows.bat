@echo off
chcp 65001 >nul
echo ========================================
echo  CareerCraft Agent Windows Build Script
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 创建虚拟环境
if not exist .venv\Scripts\python.exe (
    echo [创建虚拟环境] python -m venv .venv
    python -m venv .venv
)

REM 激活虚拟环境
set VENV_PYTHON=.venv\Scripts\python.exe
set VENV_PIP=.venv\Scripts\pip.exe

REM 安装依赖
echo [安装依赖] pip install -r requirements.txt
%VENV_PIP% install -r requirements.txt

REM 安装 PyInstaller
echo [安装 PyInstaller] pip install pyinstaller
%VENV_PIP% install pyinstaller

REM 运行测试
echo [运行测试] pytest tests/ -q
%VENV_PYTHON% -m pytest tests/ -q
if errorlevel 1 (
    echo [WARNING] 测试未通过，仍然继续打包...
)

REM 打包 WebView 版本（onedir，更稳定）
echo [开始打包] python build.py --onedir --skip-tests
%VENV_PYTHON% build.py --onedir --skip-tests

if errorlevel 1 (
    echo [ERROR] 打包失败
    pause
    exit /b 1
)

echo ========================================
echo  打包完成！输出在 dist\ 目录
echo ========================================
pause
