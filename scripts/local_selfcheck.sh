#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Starting leakage-buster local self-check..."

# 1) 创建并激活虚拟环境（不污染 base）
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment .venv..."
  python3 -m venv .venv
fi

echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# 2) 升级基础工具
echo "⬆️ Upgrading pip, wheel, build, twine..."
python -m pip install -U pip wheel build twine

# 3) 安装开发依赖（可选）
echo "📥 Installing package in development mode..."
pip install -e .[dev] || pip install -e .

# 4) 运行单测（含覆盖率）
echo "🧪 Running tests with coverage..."
pytest -q --cov=leakage_buster --cov-report=term-missing

# 5) 构建发行物并做元数据检查
echo "🔨 Building distribution packages..."
python -m build
echo "✅ Checking distribution metadata..."
twine check dist/*

# 6) 纯净安装验证：在全新 venv 里从本地 wheel 安装并运行 CLI
echo "🧪 Testing clean installation from wheel..."
python -m venv .venv_install_test
source .venv_install_test/bin/activate
pip install -U pip
pip install dist/*.whl

# PDF/Polars 可选安装验证（不强制）：
echo "📦 Testing optional dependencies installation..."
pip install "leakage-buster[pdf,polars]" || echo "⚠️ Optional dependencies not available, continuing..."

# 7) 运行最小 CLI 演示（不会访问网络/不会写到系统路径）
echo "🚀 Running CLI demo..."
mkdir -p runs/self_demo
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/self_demo

echo ""
echo "✅ Local self-check passed: venv-only install & CLI run OK."
echo "📁 Generated files:"
echo "   - runs/self_demo/report.html"
echo "   - runs/self_demo/fix_transforms.py"
echo "   - runs/self_demo/meta.json"
echo ""
echo "🎉 All checks completed successfully!"
