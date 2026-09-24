#!/usr/bin/env bash
# Windows 环境搭建脚本。必须在 **Git Bash** 里运行（不要用 PowerShell、不要用 WSL）。
# 用法：在仓库根目录执行 `bash tools/setup_windows.sh`
# 作用：
#   1. 关掉 CRLF 转换（金标逐字节比对）
#   2. 用 uv 装 Python 3.14 与依赖到 .venv/
#   3. 建目录联接 .venv/bin -> .venv/Scripts（仓库里的脚本与测试都写的是 .venv/bin/python）
#   4. 冒烟测试
set -euo pipefail
cd "$(dirname "$0")/.."

git config core.autocrlf false

if ! command -v uv >/dev/null 2>&1; then
  py -3 -m pip install --user --quiet uv 2>/dev/null || python -m pip install --user --quiet uv
  export PATH="$APPDATA/Python/Scripts:$HOME/.local/bin:$PATH"
  for d in "$APPDATA"/Python/Python3*/Scripts; do export PATH="$d:$PATH"; done
fi

uv python install 3.14
uv venv .venv --python 3.14 --allow-existing
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt

if [ ! -e .venv/bin ]; then
  cmd //c "mklink /J .venv\\bin .venv\\Scripts" >/dev/null
fi

export PYTHONUTF8=1 LC_ALL=C.UTF-8 LANG=C.UTF-8
.venv/bin/python --version
.venv/bin/python -m unittest discover -s pipeline/intake/tests -t . 2>&1 | tail -3
echo "环境就绪。之后每次开 Git Bash 先执行：export PYTHONUTF8=1 LC_ALL=C.UTF-8 LANG=C.UTF-8"
