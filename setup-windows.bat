@echo off
chcp 65001 >nul
REM 一键安装依赖 · Windows 版
REM 用法：双击运行，约需 5-10 分钟（取决于网速）

cd /d "%~dp0"

echo ===============================================
echo  Windows 环境一键安装
echo  适配：Python 3.12（建议）或 Python 3.11
echo ===============================================
echo.

REM 检查 Python
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ 没有检测到 Python。请先去 https://www.python.org/downloads/ 下载安装 Python 3.12
    echo    安装时记得勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [Python 版本]
python --version
echo.

echo [1/4] 升级 pip ...
python -m pip install --upgrade pip
echo.

echo [2/4] 安装基础依赖 ...
python -m pip install -r requirements.txt
echo.

echo [3/4] 安装真实 EVM 相关依赖 ...
python -m pip install py-solc-x web3 eth-tester py-evm
echo.

echo [4/4] 预下载 Solidity 编译器 0.8.20 ...
python -c "from solcx import install_solc; install_solc('0.8.20')"
echo.

echo ===============================================
echo  ✅ 安装完成。下一步：
echo       双击 run-demo.bat 启动演示
echo ===============================================
pause
