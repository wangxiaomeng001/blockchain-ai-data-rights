#!/usr/bin/env bash
# 一键答辩演示启动脚本
# 用法：bash run-demo.sh
# 打开浏览器: http://localhost:8501

set -e
cd "$(dirname "$0")"

echo "═══════════════════════════════════════════════"
echo "  基于区块链的 AI 数据确权系统 · 答辩演示"
echo "  宁波工程学院 · AI221 · 王孝萌"
echo "═══════════════════════════════════════════════"

PY="${PYTHON:-python3.12}"

echo ""
echo "[1/3] 运行单元测试 ..."
"$PY" test_registry.py | tail -5

echo ""
echo "[2/3] 运行真实 EVM 测试 ..."
"$PY" test_evm.py | tail -5

echo ""
echo "[3/3] 启动 Streamlit 前端 ..."
echo "      浏览器将打开 http://localhost:8501"
echo "      关闭请按 Ctrl+C"
echo ""
"$PY" -m streamlit run app.py
