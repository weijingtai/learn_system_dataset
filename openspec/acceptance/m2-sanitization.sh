#!/usr/bin/env bash
# m2-sanitization.sh — M2 电子文本清洗验收脚本（规格 §19.0）
#
# 验收宿主：README §7.2 约定的《乾元秘旨》电子文本片段。该宿主由主 Agent 另行以
# 独占 fixture ACT 安排（P4），本脚本**不自建宿主**，因此宿主不存在是正常状态——
# 此时打印缺失前置并 exit 2（BLOCKED）。
#
# 退出码：0 全部 PASS；1 有 FAIL；2 有 BLOCKED 或不可判定。
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

# 电子文本验收宿主目录（README §7.2；P4 独占 fixture ACT 安排，本脚本不创建）
FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/qianyuan_ed01_text}"

if [ ! -d "$FIXTURE_DIR" ]; then
  echo "BLOCKED m2_sanitization 前置缺失: 电子文本验收宿主不存在（README §7.2《乾元秘旨》片段；P4 独占 fixture ACT 尚未落地）；FIXTURE_DIR=$FIXTURE_DIR"
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
