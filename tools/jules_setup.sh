#!/usr/bin/env bash
# Jules（及任何干净的 Linux 机器）环境搭建脚本。
# 用法：在仓库根目录执行 `bash tools/jules_setup.sh`
# 作用：装 Python 3.14 与依赖到 .venv/，设置 UTF-8 locale，然后跑一次冒烟测试。
set -euo pipefail

cd "$(dirname "$0")/.."

# 1. uv：用它装指定版本的 Python，比依赖系统 Python 可靠
if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user --quiet uv || pip install --quiet uv
  export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Python 3.14 虚拟环境（本仓库在 3.14 上开发与验收）
uv python install 3.14
uv venv .venv --python 3.14 --allow-existing
uv pip install --python .venv/bin/python -r requirements-dev.txt

# 3. 测试需要 UTF-8 locale（LC_ALL=C 下有已知误报）
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# 4. 冒烟：账本包能跑通即说明环境可用
.venv/bin/python --version
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | tail -3
echo "环境就绪。跑测试前请先 export LC_ALL=C.UTF-8"
