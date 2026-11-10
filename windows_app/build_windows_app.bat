@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   EasyColab Windows 一键本地编译打包脚本 (生成免装 Python 的独立 exe)
echo ============================================================

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\.."
set "PROJECT_ROOT=%CD%"

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 3.10~3.13，请先从 https://www.python.org/downloads/ 安装 Python 并勾选 Add Python to PATH。
    popd
    exit /b 1
)

set "VENV_DIR=%PROJECT_ROOT%\.venv_win"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] 正在创建隔离编译虚拟环境 .venv_win ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        popd
        exit /b 1
    )
)

echo [2/4] 正在安装 / 校验 PySide6 与打包依赖 ...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip -q
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%PROJECT_ROOT%\windows_app\requirements-windows.txt"
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接。
    popd
    exit /b 1
)

echo [3/4] 正在生成高清多尺寸应用图标 AppIcon.ico ...
"%VENV_DIR%\Scripts\python.exe" "%PROJECT_ROOT%\windows_app\generate_icon.py"
if errorlevel 1 (
    echo [错误] 生成应用图标失败。
    popd
    exit /b 1
)

echo [4/4] 正在使用 PyInstaller 编译独立可执行程序 EasyColab.exe ...
"%VENV_DIR%\Scripts\pyinstaller.exe" --noconfirm --clean ^
    --distpath "%PROJECT_ROOT%\dist" ^
    --workpath "%PROJECT_ROOT%\build\pyinstaller" ^
    "%PROJECT_ROOT%\windows_app\EasyColab.spec"
if errorlevel 1 (
    echo [错误] PyInstaller 编译失败。
    popd
    exit /b 1
)

set "ZIP_OUT=%PROJECT_ROOT%\EasyColab-Windows-x64.zip"
if exist "%ZIP_OUT%" del /f /q "%ZIP_OUT%"

echo 正在打包免安装绿色发行版压缩包 EasyColab-Windows-x64.zip ...
"%VENV_DIR%\Scripts\python.exe" -m zipfile -c "%ZIP_OUT%" "%PROJECT_ROOT%\dist\EasyColab"
if errorlevel 1 (
    echo [错误] 发行压缩包生成失败。
    popd
    exit /b 1
)

echo.
echo [完成] Windows 客户端编译成功！
echo   - 可直接运行目录版: %PROJECT_ROOT%\dist\EasyColab\EasyColab.exe
echo   - 免安装分发压缩包: %ZIP_OUT%
popd
endlocal
