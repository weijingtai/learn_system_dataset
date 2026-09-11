#!/usr/bin/env bash
# D-18：§20「黑箱完成标准」十一条的可执行判据。
#
# 用法：bash openspec/acceptance/run_all.sh [20.N ...]
#   无参数：按 20.1 → 20.11 顺序执行全部条目。
#   带编号：只执行给定条目。
#
# 环境：
#   export LC_ALL=en_US.UTF-8 由本脚本自行设置。
#   FIXTURE_DIR 透传给 fixture 的 verify.sh（默认 pipeline/corpus/_fixture/mini_ed01）。
#
# 输出（每条恰一行，状态与编号之间两个空格）：
#   PASS  20.N  <说明>
#   FAIL  20.N  <说明>: <原因>
#   BLOCKED  20.N  前置缺失: <§19 差距行名>；<说明>
# 末行：SUMMARY pass=<n> fail=<n> blocked=<n>；退出码 = fail 条数。
#
# 语义约束：允许 BLOCKED（依赖能力尚未实现），不允许「无法执行」；
# 绝不把不可判定项写成 PASS；BLOCKED 的差距行名逐字取自规格 §19 主表第一列。
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if ! cd "$REPO_ROOT"; then
  echo "FAIL  20.0  运行环境: 无法进入仓库根目录 $REPO_ROOT"
  exit 1
fi

SPEC="openspec/learn-system-blackbox-architecture.md"
FIXTURE_DIR="${FIXTURE_DIR:-$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01}"
CANON_VERIFY="$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh"
PY="$REPO_ROOT/.venv/bin/python"
export FIXTURE_DIR
DB="pattern_knowledge_workbench/assets/ge_ju_database.sqlite"
IMPORT_TOOL="pipeline/tools/import_legacy_candidates.py"

pass_n=0
fail_n=0
blocked_n=0

pass_line() { printf 'PASS  %s  %s\n' "$1" "$2"; pass_n=$((pass_n + 1)); }
fail_line() { printf 'FAIL  %s  %s: %s\n' "$1" "$2" "$3"; fail_n=$((fail_n + 1)); }
block_line() { printf 'BLOCKED  %s  前置缺失: %s；%s\n' "$1" "$2" "$3"; blocked_n=$((blocked_n + 1)); }

# ---------------------------------------------------------------- fixture 子检查
# 运行统一验收宿主的自校验：0 → 宿主 OK；3 → 宿主 OK 但素材缺失（记录）；
# 1 → 宿主 FAIL（取其 FAIL 行作为原因）；脚本缺失 → MISSING。
FX_STATUS=""
FX_REASON=""
fx() {
  FX_STATUS=""
  FX_REASON=""
  # 一律调用仓库内规范脚本，绝不执行被验目录自带的 verify.sh：
  # 验收脚本不应信任被验对象自带的脚本，且仓库外副本的脚本推不出仓库根。
  if [ ! -f "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" ]; then
    FX_STATUS="MISSING"
    return 0
  fi
  local out rc
  out="$(FIXTURE_DIR="$FIXTURE_DIR" bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh" 2>&1)"
  rc=$?
  case "$rc" in
    0) FX_STATUS="OK" ;;
    3) FX_STATUS="OK_NO_ASSET" ;;
    1) FX_STATUS="FAIL"
       FX_REASON="$(printf '%s\n' "$out" | grep -m1 '^FAIL ' | sed 's/^FAIL //')" ;;
    *) FX_STATUS="FAIL"
       FX_REASON="verify.sh 退出码 $rc" ;;
  esac
  return 0
}

# ------------------------------------------------- 20.1 / 20.3 / 20.4 的解析探针
PROBE_OUT=""
if [ -x "$PY" ]; then
  PROBE_OUT="$(FIXTURE_DIR="$FIXTURE_DIR" "$PY" - <<'PYEOF' 2>/dev/null
import os
import sys

import yaml

fix = os.environ["FIXTURE_DIR"]


def load(rel):
    with open(os.path.join(fix, rel), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def emit(item, ok, reason=""):
    if ok:
        print("%s\tOK" % item)
    else:
        print("%s\tFAIL\t%s" % (item, reason))


try:
    pkgs = {s: load("expected/%s.stage_package.yaml" % s) for s in ("m1", "m2", "m3")}
    errs = []
    if [pkgs[s]["stage"] for s in ("m1", "m2", "m3")] != ["m1", "m2", "m3"]:
        errs.append("stage 未按 m1→m2→m3 递增")
    for prev, cur in (("m1", "m2"), ("m2", "m3")):
        want = pkgs[prev]["manifest"]["output_artifacts"][0]["artifact_revision_id"]
        got = pkgs[cur]["lineage"]["transformations"][0]["input_artifact_revision_ids"]
        if got != [want]:
            errs.append("%s 的 lineage 输入 %s != %s 的输出 %s" % (cur, got, prev, want))
    emit("20.1", not errs, "; ".join(errs))
except Exception as exc:
    emit("20.1", False, "读取 expected 阶段包失败: %s" % exc)

try:
    errs = []
    for s in ("m1", "m2", "m3"):
        doc = load("expected/%s.stage_package.yaml" % s)
        trs = doc["lineage"]["transformations"]
        if len(trs) != 1:
            errs.append("%s 的 transformations 数量 %d != 1" % (s, len(trs)))
            continue
        if not trs[0].get("configuration_artifact_revision_id"):
            errs.append("%s 缺 configuration_artifact_revision_id" % s)
    emit("20.3", not errs, "; ".join(errs))
except Exception as exc:
    emit("20.3", False, "读取 expected 阶段包失败: %s" % exc)

try:
    man = load("manifest.yaml")
    spans = load("spans.yaml")["spans"]
    sha = {a["page"]: a["sha256"] for a in man["source_assets"]}
    bad = [sp["span_id"] for sp in spans if sp["source_anchor"]["image_sha256"] != sha.get(sp["page"])]
    emit("20.4", not bad, "锚点哈希不一致: %s" % ", ".join(bad[:3]))
except Exception as exc:
    emit("20.4", False, "读取 spans/manifest 失败: %s" % exc)
PYEOF
)"
fi

probe_status() {
  printf '%s\n' "$PROBE_OUT" | awk -F'\t' -v i="$1" '$1 == i { print $2; exit }'
}

probe_reason() {
  printf '%s\n' "$PROBE_OUT" | awk -F'\t' -v i="$1" '$1 == i { print $3; exit }'
}

# ---------------------------------------------------------------------- 条目规则
run_item() {
  local n="$1"
  case "$n" in
    20.1)
      fx
      if [ "$FX_STATUS" = "MISSING" ]; then
        block_line "$n" "M3 Corpus Compilation" "fixture 缺失"
        return 0
      fi
      if [ "$FX_STATUS" = "FAIL" ]; then
        fail_line "$n" "统一验收宿主校验未通过" "$FX_REASON"
        return 0
      fi
      if [ ! -x "$PY" ]; then
        block_line "$n" "测试宿主匮乏" ".venv 缺失"
        return 0
      fi
      case "$(probe_status "$n")" in
        OK) block_line "$n" "Local Orchestrator" "M4–M6 Gate 未实现" ;;
        FAIL) fail_line "$n" "三包 stage 递增与 lineage 串联不成立" "$(probe_reason "$n")" ;;
        *) block_line "$n" "测试宿主匮乏" "判据探针无输出" ;;
      esac
      ;;
    20.2)
      fx
      if [ "$FX_STATUS" = "MISSING" ]; then
        block_line "$n" "M3 Corpus Compilation" "fixture 缺失"
        return 0
      fi
      if [ "$FX_STATUS" = "FAIL" ]; then
        fail_line "$n" "统一验收宿主校验未通过" "$FX_REASON"
        return 0
      fi
      block_line "$n" "Artifact Ledger" "StageCheckpoint §17.1 未实现"
      ;;
    20.3)
      fx
      if [ "$FX_STATUS" = "MISSING" ]; then
        block_line "$n" "M3 Corpus Compilation" "fixture 缺失"
        return 0
      fi
      if [ "$FX_STATUS" = "FAIL" ]; then
        fail_line "$n" "统一验收宿主校验未通过" "$FX_REASON"
        return 0
      fi
      if [ ! -x "$PY" ]; then
        block_line "$n" "测试宿主匮乏" ".venv 缺失"
        return 0
      fi
      case "$(probe_status "$n")" in
        OK) block_line "$n" "Artifact Ledger" "真实 StepRun 记录未实现" ;;
        FAIL) fail_line "$n" "语义转换记录不完整" "$(probe_reason "$n")" ;;
        *) block_line "$n" "测试宿主匮乏" "判据探针无输出" ;;
      esac
      ;;
    20.4)
      fx
      if [ "$FX_STATUS" = "MISSING" ]; then
        block_line "$n" "M3 Corpus Compilation" "fixture 缺失"
        return 0
      fi
      if [ "$FX_STATUS" = "FAIL" ]; then
        fail_line "$n" "统一验收宿主校验未通过" "$FX_REASON"
        return 0
      fi
      if [ ! -x "$PY" ]; then
        block_line "$n" "测试宿主匮乏" ".venv 缺失"
        return 0
      fi
      case "$(probe_status "$n")" in
        OK) block_line "$n" "M8 Dataset Compilation" "PublicationPackage 反向追溯未实现" ;;
        FAIL) fail_line "$n" "字框锚点哈希与 manifest 资产不一致" "$(probe_reason "$n")" ;;
        *) block_line "$n" "测试宿主匮乏" "判据探针无输出" ;;
      esac
      ;;
    20.5)
      block_line "$n" "M7 Incremental Assembly" "增量汇编未实现"
      ;;
    20.6)
      if [ "$(grep -c 'not_captured' "$SPEC")" -lt 1 ]; then
        fail_line "$n" "Pattern 补全语义缺失" "$SPEC 中不含 not_captured 语义约定"
        return 0
      fi
      block_line "$n" "M8 Dataset Compilation" "KnowledgeEntry 编译未实现"
      ;;
    20.7)
      if ! command -v sqlite3 >/dev/null 2>&1; then
        block_line "$n" "测试宿主匮乏" "sqlite3 不可用"
        return 0
      fi
      if [ ! -f "$DB" ]; then
        block_line "$n" "测试宿主匮乏" "$DB 缺失"
        return 0
      fi
      local total="" eligible=""
      total="$(sqlite3 "$DB" "select count(*) from ge_ju_rules;" 2>/dev/null)"
      eligible="$(sqlite3 "$DB" "select count(*) from ge_ju_rules where trim(coalesce(original_text,''))<>'';" 2>/dev/null)"
      if [ -z "${total}" ] || [ -z "${eligible}" ]; then
        block_line "$n" "测试宿主匮乏" "sqlite3 查询 ge_ju_rules 失败"
        return 0
      fi
      case "${total}:${eligible}" in
        *[!0-9:]*) block_line "$n" "测试宿主匮乏" "sqlite3 查询 ge_ju_rules 返回非数字"
                   return 0 ;;
      esac
      if [ "${eligible}" -eq 0 ]; then
        fail_line "$n" "准入阈值不满足" "ge_ju_rules original_text 非空 ${eligible}/${total}；original_text 全空，准入阈值不满足"
        return 0
      fi
      if [ ! -f "$IMPORT_TOOL" ]; then
        block_line "$n" "M6 Review Workbench" "legacy_candidate 导入流程未实现"
        return 0
      fi
      pass_line "$n" "官方 Candidate 准入可用（original_text 非空 ${eligible}/${total}，导入工具存在）"
      ;;
    20.8)
      block_line "$n" "M8 Dataset Compilation" "SourceAssetPack 未实现"
      ;;
    20.9)
      block_line "$n" "M8 Dataset Compilation" "GraphProjectionPack 未实现"
      ;;
    20.10)
      if ! bash openspec/schemas/verify.sh >/dev/null 2>&1; then
        fail_line "$n" "契约不稳定" "openspec/schemas/verify.sh 未以退出码 0 通过"
        return 0
      fi
      block_line "$n" "Contract Registry" "无第二 Adapter 可做替换验证"
      ;;
    20.11)
      block_line "$n" "M8 Dataset Compilation" "尚无两个 Release 可比，IdentityMigrationMap 未产出"
      ;;
    *)
      fail_line "$n" "未知条目" "run_all.sh 未定义该编号"
      ;;
  esac
  return 0
}

# ---------------------------------------------------------------------- 主流程
if [ "$#" -eq 0 ]; then
  ITEMS="20.1 20.2 20.3 20.4 20.5 20.6 20.7 20.8 20.9 20.10 20.11"
else
  ITEMS="$*"
fi

for n in $ITEMS; do
  run_item "$n"
done

printf 'SUMMARY pass=%d fail=%d blocked=%d\n' "$pass_n" "$fail_n" "$blocked_n"
exit "$fail_n"
