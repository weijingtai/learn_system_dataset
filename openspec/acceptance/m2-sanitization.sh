#!/usr/bin/env bash
# m2-sanitization.sh — M2 电子文本清洗验收脚本（规格 §19.0；第 96 条 D2 / 第 101 条）
#
# 验收方式：对宿主原文**实跑 M1→M2**（临时 Ledger，用完即删），再把实跑结果与
# 宿主内独立金标（expected/golden_findings.yaml，独立分析 Agent 产出）按
# 第 98/99 条口径逐类比对。本脚本不读预计算产物，也不把宿主当成装着流水线
# 产物的 Ledger 目录。
#
# 三态（第 101 条）：
# - 宿主目录或原文缺失 → BLOCKED exit 2
# - 金标缺失或 SHA256SUMS 校验不符 → BLOCKED exit 2（期望不可信即不可判定）
# - 齐备 → 实跑后逐项比对 → PASS/FAIL，全 PASS exit 0，有 FAIL exit 1
#
# 纪律（G7-RULINGS 第 94 条 D3）：rc != 0，或解析不到任何 PASS/FAIL/BLOCKED 行时，
# 一律不得 exit 0——禁止「找不到就当通过」。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 无论从哪个 cwd 调用，都先切到仓库根，保证 `python -m pipeline.*` 可解析
if ! cd "$REPO_ROOT"; then
  echo "BLOCKED m2_sanitization 前置缺失: 无法进入仓库根目录 $REPO_ROOT"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 2
fi

PY="$REPO_ROOT/.venv/bin/python"

# 电子文本验收宿主目录（README §7.2；第 101 条随本 ACT 入库）
FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/qianyuan_ed01_text}"

if [ ! -d "$FIXTURE_DIR" ]; then
  echo "BLOCKED m2_sanitization 前置缺失: 电子文本验收宿主不存在（README §7.2《乾元秘旨》原文宿主）；FIXTURE_DIR=$FIXTURE_DIR"
  echo "SUMMARY pass=0 fail=0 blocked=1"
  exit 2
fi

out="$("$PY" -m pipeline.digitization.acceptance "$FIXTURE_DIR" 2>&1)"
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
  echo "BLOCKED m2_sanitization 不可判定: 验收入口非零退出 rc=$rc"
  echo "SUMMARY pass=$pass fail=$fail blocked=$((blocked + 1))"
  exit 2
fi

if [ "$parsed" -eq 0 ]; then
  echo "BLOCKED m2_sanitization 不可判定: 验收入口未输出任何 PASS/FAIL/BLOCKED 行"
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
