#!/usr/bin/env bash
# contract-registry.sh — Contract Registry §20.10 验收入口（§19.0 判据）
#
# 退出码：0 全 PASS；1 任一判定 FAIL；2 无 FAIL 有 BLOCKED；3 宿主缺失。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "BLOCKED contract_registry 前置缺失: 测试宿主匮乏；.venv 缺失"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

cd "$REPO_ROOT" && "$PY" -m pipeline.contract_registry.acceptance "$@"
exit $?
