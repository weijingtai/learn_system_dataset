#!/usr/bin/env bash
# m8-span-identity 验收入口（§19.0 判据：7 PASS + mentions_mapping BLOCKED，exit 2）
#
# 退出码：0 全 PASS；1 任一判定 FAIL 或宿主校验失败；2 无 FAIL 有 BLOCKED；3 宿主缺失。
#
# 路线分派（D-W8-16，2026-09-21）：
#   判定执行者仍是 `pipeline.dataset_compiler.acceptance`；本脚本只负责「宿主校验用哪个
#   规范脚本」与「页图默认值是否适用」。路线权威 = 夹具目录内 spans.yaml 的
#   evidence_level（**不**按目录名猜、**不**新增环境变量指定路线）：
#     glyphbox_level → OCR 夹具（页图默认 ocr/data_work/sanche_pages）
#     offset_level   → 电子文本夹具（不读任何页图，FIXTURE_ASSET_ROOT 不适用）
#   两档都只执行仓库内规范脚本 `$REPO_ROOT/pipeline/corpus/_fixture/<夹具名>/verify.sh`，
#   **绝不执行 `$FIXTURE_DIR` 副本目录内的 verify 脚本**（裁定 44 的性质）。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01}"

# 环境变量覆盖时先解析为绝对路径
case "$FIXTURE_DIR" in
  /*) ;;
  *) FIXTURE_DIR="$(cd "$FIXTURE_DIR" 2>/dev/null && pwd || printf '%s' "$FIXTURE_DIR")" ;;
esac

PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "BLOCKED m8_acceptance 前置缺失: 测试宿主匮乏；.venv 缺失"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

# 路线判定：权威 = 夹具目录内 spans.yaml 的 evidence_level（D-W8-16 三）
ROUTE="$("$PY" - "$FIXTURE_DIR" <<'PY'
import sys
from pathlib import Path

import yaml

fixture = Path(sys.argv[1])
spans = fixture / "spans.yaml"
if not spans.is_file():
    print("缺 fixture spans.yaml")
    raise SystemExit
try:
    document = yaml.safe_load(spans.read_bytes())
except Exception:  # noqa: BLE001
    print("无法判定证据级别")
    raise SystemExit
level = document.get("evidence_level") if isinstance(document, dict) else None
print({"glyphbox_level": "GLYPHBOX", "offset_level": "OFFSET"}.get(level, "无法判定证据级别"))
PY
)"

case "$ROUTE" in
  GLYPHBOX)
    FIXTURE_ASSET_ROOT="${FIXTURE_ASSET_ROOT:-$REPO_ROOT/ocr/data_work/sanche_pages}"
    VERIFY="$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh"
    ;;
  OFFSET)
    # 电子文本路线不读任何页图：不设页图默认值，也不校验页图（ACT 16 四）
    FIXTURE_ASSET_ROOT="${FIXTURE_ASSET_ROOT:-}"
    VERIFY="$REPO_ROOT/pipeline/corpus/_fixture/qianyuan_ed01_text/verify.sh"
    ;;
  *)
    echo "BLOCKED m8_acceptance 宿主缺失: $ROUTE"
    echo "SUMMARY pass=0 fail=0 blocked=1"
    exit 3
    ;;
esac

case "$FIXTURE_ASSET_ROOT" in
  "") ;;
  /*) ;;
  *) FIXTURE_ASSET_ROOT="$(cd "$FIXTURE_ASSET_ROOT" 2>/dev/null && pwd || printf '%s' "$FIXTURE_ASSET_ROOT")" ;;
esac

# 宿主校验：永远调用仓库内规范脚本，绝不执行副本目录内的 verify 脚本
HOST_OUT="$(FIXTURE_DIR="$FIXTURE_DIR" FIXTURE_ASSET_ROOT="$FIXTURE_ASSET_ROOT" \
  bash "$VERIFY" 2>&1)"
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
