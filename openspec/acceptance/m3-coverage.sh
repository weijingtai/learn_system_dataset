#!/usr/bin/env bash
# m3-coverage.sh — M3 验收脚本（规格 §19.0 判据）
#
# 两条路线并存、显式分流、互不回落（G7-RULINGS 第 97 条）：
#   设了 ELECTRONIC_TEXT_FIXTURE_DIR 环境变量 → **只走电子文本路线**；
#       宿主目录缺失 → BLOCKED exit 2；**绝不**回落到 OCR 路线的 mini_ed01。
#   未设该变量                          → 走 OCR 路线，既有语义逐字保持：
#       FIXTURE_DIR 默认 pipeline/corpus/_fixture/mini_ed01、
#       只调用**仓库内规范** verify.sh（不执行被验目录自带的副本）、
#       rc==1 判 `FAIL fixture_host` 并 exit 1。
#
# 退出码：0 全部 PASS；1 有 FAIL；2 有 BLOCKED 或不可判定；3 OCR 路线 .venv 缺失。
#
# 纪律（G7-RULINGS 第 94 条 D2/D3）：
#   - 电子文本路线默认宿主**不得**回落 OCR 路线的 mini_ed01（D2）；
#   - 电子文本路线 rc != 0，或解析不到任何 PASS/FAIL/BLOCKED 行时，一律不得 exit 0（D3）；
#   - 脚本先 cd "$REPO_ROOT" 再运行，并回显逐项结果。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 无论从哪个 cwd 调用，都先切到仓库根，保证 `python -m pipeline.*` 可解析
if ! cd "$REPO_ROOT"; then
  echo "BLOCKED m3_coverage 前置缺失: 无法进入仓库根目录 $REPO_ROOT"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 2
fi

PY="$REPO_ROOT/.venv/bin/python"

# ------------------------------------------------------------------ 电子文本路线
if [ -n "${ELECTRONIC_TEXT_FIXTURE_DIR:-}" ]; then
  FIXTURE_DIR="$ELECTRONIC_TEXT_FIXTURE_DIR"

  # 电子文本验收宿主目录（README §7.2；P4 独占 fixture ACT 安排，本脚本不创建）
  if [ ! -d "$FIXTURE_DIR" ]; then
    echo "BLOCKED m3_coverage 前置缺失: 电子文本验收宿主不存在（README §7.2《乾元秘旨》片段；P4 独占 fixture ACT 尚未落地）；ELECTRONIC_TEXT_FIXTURE_DIR=$FIXTURE_DIR"
    echo "SUMMARY pass=0 fail=0 blocked=1"
    exit 2
  fi

  out="$("$PY" -m pipeline.corpus_compiler.acceptance --electronic-text-fixture "$FIXTURE_DIR" 2>&1)"
  rc=$?

  pass=0; fail=0; blocked=0; parsed=0
  while IFS= read -r line; do
    case "$line" in
      PASS\ *) pass=$((pass + 1)); parsed=$((parsed + 1)) ;;
      FAIL\ *) fail=$((fail + 1)); parsed=$((parsed + 1)) ;;
      BLOCKED\ *) blocked=$((blocked + 1)); parsed=$((parsed + 1)) ;;
    esac
  done < <(printf '%s\n' "$out")

  # 回显逐项结果（不吞掉明细）
  printf '%s\n' "$out"

  if [ "$rc" -ne 0 ]; then
    echo "BLOCKED m3_coverage 不可判定: 验收入口非零退出 rc=$rc"
    echo "SUMMARY pass=$pass fail=$fail blocked=$((blocked + 1))"
    exit 2
  fi

  if [ "$parsed" -eq 0 ]; then
    echo "BLOCKED m3_coverage 不可判定: 验收入口未输出任何 PASS/FAIL/BLOCKED 行"
    echo "SUMMARY pass=$pass fail=$fail blocked=$((blocked + 1))"
    exit 2
  fi

  echo "SUMMARY pass=$pass fail=$fail blocked=$blocked"

  if [ "$blocked" -gt 0 ]; then
    exit 2
  elif [ "$fail" -gt 0 ]; then
    exit 1
  else
    exit 0
  fi
fi

# ------------------------------------------------------------------ OCR 路线（既有语义，逐字保持）
FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01}"
case "$FIXTURE_DIR" in
  /*) ;;
  *)  FIXTURE_DIR="$(cd "$FIXTURE_DIR" && pwd)" ;;
esac

if [ ! -x "$PY" ]; then
  echo "BLOCKED m3_coverage 前置缺失: 测试宿主匮乏；.venv 缺失"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 3
fi

# 宿主校验：永远调用仓库内规范脚本，不执行副本脚本
FIXTURE_DIR="$FIXTURE_DIR" bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 1 ]; then
  first_fail="$(FIXTURE_DIR="$FIXTURE_DIR" bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" 2>&1 | grep '^FAIL' | head -1)"
  echo "FAIL fixture_host $first_fail"
  echo "SUMMARY pass=0 fail=1 blocked=0"
  exit 1
elif [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
  echo "FAIL fixture_host verify.sh 退出码 $rc"
  echo "SUMMARY pass=0 fail=1 blocked=0"
  exit 1
fi

cd "$REPO_ROOT" && "$PY" -m pipeline.corpus_compiler.acceptance --fixture "$FIXTURE_DIR"
exit $?
