@echo off
chcp 65001 >nul
REM 一键答辩演示启动脚本 · Windows 版
REM 用法：双击运行，或在 cmd / PowerShell 里执行 run-demo.bat
REM 浏览器会自动打开 http://localhost:8501

cd /d "%~dp0"

echo ===============================================
echo  基于区块链的 AI 数据确权系统 · 答辩演示
echo  宁波工程学院 · AI221 · 王孝萌
echo ===============================================
echo.

REM 优先用 python3.12，没有则降级到 python
where python3.12 >nul 2>nul
if %errorlevel%==0 (
    set PY=python3.12
) else (
    set PY=python
)

echo [Python 解释器]: %PY%
%PY% --version
echo.

echo [1/3] 运行 registry 单元测试 ...
%PY% test_registry.py
if errorlevel 1 (
    echo.
    echo ❌ registry 测试失败。检查依赖是否安装：pip install -r requirements.txt
    pause
    exit /b 1
)
echo.

echo [2/3] 运行真实 EVM 测试 ...
%PY% test_evm.py
if errorlevel 1 (
    echo.
    echo ❌ EVM 测试失败。可能是 py-solc-x 没装好。运行 setup-windows.bat 修复。
    pause
    exit /b 1
)
echo.

echo [3/3] 启动 Streamlit 前端 ...
echo       浏览器将自动打开 http://localhost:8501
echo       关闭请按 Ctrl+C，然后关掉这个窗口
echo.
%PY% -m streamlit run app.py
pause
