#!/usr/bin/env bash
# m5-evidence-gate 验收脚本（规格 §19.0）
#
# 用法：bash openspec/acceptance/m5-evidence-gate.sh
# 环境变量：FIXTURE_DIR 待验收 fixture 根目录（默认仓库内 mini_ed01）
#
# 退出码：0=全 PASS / 1=有 FAIL / 2=无 FAIL 有 BLOCKED / 3=宿主或依赖缺失。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01}"
case "$FIXTURE_DIR" in
  /*) : ;;
  *) FIXTURE_DIR="$REPO_ROOT/$FIXTURE_DIR" ;;
esac

PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "BLOCKED m5_evidence_gate 前置缺失: 测试宿主匮乏；.venv 缺失"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

# 宿主校验：永远调用仓库内规范脚本，绝不执行 FIXTURE_DIR 自带的 verify.sh
VERIFY_SH="$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh"
verify_out="$(FIXTURE_DIR="$FIXTURE_DIR" bash "$VERIFY_SH" 2>&1)"
verify_rc=$?
if [ "$verify_rc" -ne 0 ] && [ "$verify_rc" -ne 3 ]; then
  first_fail="$(printf '%s\n' "$verify_out" | grep -m1 '^FAIL ' || true)"
  echo "FAIL fixture_host ${first_fail:-verify.sh exit=$verify_rc}"
  echo "SUMMARY pass=0 fail=1 blocked=0"
  exit 1
fi

cd "$REPO_ROOT" || exit 3
"$PY" -m pipeline.validation.acceptance --fixture "$FIXTURE_DIR"
exit $?
