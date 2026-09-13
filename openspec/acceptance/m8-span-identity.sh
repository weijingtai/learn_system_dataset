#!/usr/bin/env bash
# m8-span-identity 验收入口（§19.0 判据：7 PASS + mentions_mapping BLOCKED，exit 2）
#
# 退出码：0 全 PASS；1 任一判定 FAIL 或宿主校验失败；2 无 FAIL 有 BLOCKED；3 宿主缺失。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01}"
FIXTURE_ASSET_ROOT="${FIXTURE_ASSET_ROOT:-$REPO_ROOT/ocr/data_work/sanche_pages}"

# 环境变量覆盖时先解析为绝对路径
case "$FIXTURE_DIR" in
  /*) ;;
  *) FIXTURE_DIR="$(cd "$FIXTURE_DIR" 2>/dev/null && pwd || printf '%s' "$FIXTURE_DIR")" ;;
esac
case "$FIXTURE_ASSET_ROOT" in
  /*) ;;
  *) FIXTURE_ASSET_ROOT="$(cd "$FIXTURE_ASSET_ROOT" 2>/dev/null && pwd || printf '%s' "$FIXTURE_ASSET_ROOT")" ;;
esac

PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "BLOCKED m8_acceptance 前置缺失: 测试宿主匮乏；.venv 缺失"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

# 宿主校验：永远调用仓库内规范脚本，绝不执行副本目录内的 verify 脚本
HOST_OUT="$(FIXTURE_DIR="$FIXTURE_DIR" FIXTURE_ASSET_ROOT="$FIXTURE_ASSET_ROOT" \
  bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" 2>&1)"
HOST_CODE=$?

if [ "$HOST_CODE" -eq 3 ]; then
  MISSING_REFS="$(printf '%s\n' "$HOST_OUT" | sed -n 's/^BLOCKED_SOURCE_ASSET_MISSING //p' | tr '\n' ' ')"
  if [ -n "$MISSING_REFS" ]; then
    echo "BLOCKED m8_acceptance BLOCKED_SOURCE_ASSET_MISSING ${MISSING_REFS% }"
  else
    echo "BLOCKED m8_acceptance BLOCKED_SOURCE_ASSET_MISSING"
  fi
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

if [ "$HOST_CODE" -ne 0 ]; then
  FAIL_LINE="$(printf '%s\n' "$HOST_OUT" | grep -m1 '^FAIL' || true)"
  if [ -n "$FAIL_LINE" ]; then
    echo "FAIL fixture_host $FAIL_LINE"
  else
    echo "FAIL fixture_host verify.sh 退出码 $HOST_CODE"
  fi
  echo "SUMMARY pass=0 fail=1 blocked=0"
  exit 1
fi

cd "$REPO_ROOT" || exit 1
"$PY" -m pipeline.dataset_compiler.acceptance --fixture "$FIXTURE_DIR" --check span_identity
exit $?
