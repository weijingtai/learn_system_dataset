#!/usr/bin/env bash
# m7-assembler.sh — M7 创世汇编验收脚本（规格 §19.0 判据）
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "BLOCKED m7_acceptance 前置缺失: 测试宿主匮乏；.venv 缺失"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

# 宿主校验：永远调用仓库内规范脚本，不接受 FIXTURE_* 环境改写，不执行副本脚本
unset FIXTURE_DIR FIXTURE_ASSET_ROOT
bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 1 ]; then
  first_fail="$(bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" 2>&1 | grep '^FAIL' | head -1)"
  echo "FAIL fixture_host mini_ed01 $first_fail"
  echo "SUMMARY pass=0 fail=1 blocked=0"
  exit 1
elif [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
  echo "FAIL fixture_host mini_ed01 verify.sh 退出码 $rc"
  echo "SUMMARY pass=0 fail=1 blocked=0"
  exit 1
fi

cd "$REPO_ROOT" && "$PY" -m pipeline.assembly.acceptance "$@"
exit $?
