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
# 20.2 / 20.3 的宿主判定：在临时 Ledger 上经真实写路径灌入 mini_ed01 后跑场景判定。
ledger_check() {   # $1 条目号 $2 检查名(20_2|20_3) $3 说明
  if [ ! -x "$PY" ]; then block_line "$1" "测试宿主匮乏" ".venv 缺失"; return 0; fi
  out="$(cd "$REPO_ROOT" && "$PY" -m pipeline.ledger.acceptance --fixture "$FIXTURE_DIR" --check "$2" 2>&1)"; rc=$?
  case "$rc" in
    0) pass_line "$1" "$3" ;;
    1) fail_line "$1" "$3" "$(printf '%s\n' "$out" | grep -m1 '^FAIL' )" ;;
    *) block_line "$1" "测试宿主匮乏" "pipeline.ledger 不可用（退出码 $rc）" ;;
  esac
}
# 20.1 / 20.10 的编排判定：调用 acceptance，按其退出码与首个 BLOCKED 行落点。
accept_check() {   # $1 条目号 $2 python 模块 $3 PASS 说明；其余参数透传给模块
  local item="$1" mod="$2" desc="$3" out rc line rest row why
  shift 3
  out="$(cd "$REPO_ROOT" && "$PY" -m "$mod" "$@" 2>&1)"; rc=$?
  case "$rc" in
    0) pass_line "$item" "$desc" ;;
    1) fail_line "$item" "$desc" "$(printf '%s\n' "$out" | grep -m1 '^FAIL ')" ;;
    2) line="$(printf '%s\n' "$out" | grep -m1 '^BLOCKED ')"
       rest="${line#*前置缺失: }"; row="${rest%%；*}"; why="${rest#*；}"
       if [ -z "$line" ] || [ "$rest" = "$line" ] || [ "$row" = "$rest" ]; then
         block_line "$item" "测试宿主匮乏" "$mod 的 BLOCKED 行无法解析"
       else
         block_line "$item" "$row" "$why"
       fi ;;
    *) block_line "$item" "测试宿主匮乏" "$mod 不可用（退出码 $rc）" ;;
  esac
}
# 20.4 / 20.8 的 M8 判定：在临时 Ledger 上运行 M8 判定，返回三态字符串。
#   OK      判定无 FAIL 有 BLOCKED 或全 PASS（acceptance 退出 0 或 2）
#   FAIL    任一条目 FAIL（退出 1）
#   MISSING 宿主缺失（退出 3：缺 fixture、缺页图、缺 .venv/依赖）
M8_VERDICT_REASON=""
# TODO.md T02（2026-09-23）：20.4 / 20.6 / 20.8 / 20.9 / 20.11 一律由 M8 验收的实际判据行决定，不许写死。
M8_OUT_span_identity=""
M8_OUT_publication=""
m8_prime() {   # $1 check(span_identity|publication)：在当前 shell 里跑一次 M8 验收并缓存（不能在 $(...) 子进程里调，否则缓存丢失）
  local var="M8_OUT_$1"
  if [ -z "${!var}" ]; then
    printf -v "$var" '%s' "$(cd "$REPO_ROOT" && "$PY" -m pipeline.dataset_compiler.acceptance --fixture "$FIXTURE_DIR" --check "$1" 2>&1)"
  fi
}
m8_lines() {   # $1 check：打印已缓存的输出（调用前须先 m8_prime）
  local var="M8_OUT_$1"
  printf '%s\n' "${!var}"
}
m8_item_all() {   # $1 条目号 $2 check $3 说明：整组判据——任一 FAIL→FAIL；否则任一 BLOCKED→BLOCKED（理由取实测行）；否则 PASS
  local out fails blocks
  m8_prime "$2"
  out="$(m8_lines "$2")"
  fails="$(printf '%s\n' "$out" | grep '^FAIL ' | sed 's/^FAIL //' | paste -sd '；' -)"
  blocks="$(printf '%s\n' "$out" | grep '^BLOCKED ' | sed 's/^BLOCKED //' | paste -sd '；' -)"
  if [ -n "$fails" ]; then fail_line "$1" "M8 判定未通过" "$fails"
  elif [ -n "$blocks" ]; then block_line "$1" "M8 Dataset Compilation" "$blocks"
  elif printf '%s\n' "$out" | grep -q '^SUMMARY '; then pass_line "$1" "$3"
  else block_line "$1" "测试宿主匮乏" "M8 验收未输出 SUMMARY"
  fi
}
m8_item_one() {   # $1 条目号 $2 check $3 判据名 $4 PASS 时的说明：只看一条判据行
  local line
  m8_prime "$2"
  line="$(m8_lines "$2" | grep -m1 "^[A-Z_]* $3 ")"
  case "$line" in
    "PASS $3 "*) pass_line "$1" "$4" ;;
    "FAIL $3 "*) fail_line "$1" "M8 判定未通过" "${line#FAIL $3 }" ;;
    "BLOCKED $3 "*) block_line "$1" "M8 Dataset Compilation" "${line#BLOCKED $3 }" ;;
    *) block_line "$1" "测试宿主匮乏" "M8 验收未输出判据 $3" ;;
  esac
}
m8_host_ok() {   # 20.x 共用的宿主前置：fixture 与 .venv
  fx
  if [ "$FX_STATUS" = "MISSING" ]; then block_line "$1" "M3 Corpus Compilation" "fixture 缺失"; return 1; fi
  if [ "$FX_STATUS" = "FAIL" ]; then fail_line "$1" "统一验收宿主校验未通过" "$FX_REASON"; return 1; fi
  if [ ! -x "$PY" ]; then block_line "$1" "测试宿主匮乏" ".venv 缺失"; return 1; fi
  return 0
}
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
        OK) accept_check "$n" pipeline.orchestrator.acceptance "一个 EditionPart 严格按 M1–M6 阶段 Gate 完成（宿主 mini_ed01 真实 Ledger）" --fixture "$FIXTURE_DIR" ${FIXTURE_ASSET_ROOT:+--asset-root "$FIXTURE_ASSET_ROOT"} ;;
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
      ledger_check "$n" 20_2 "最近 StageCheckpoint 可恢复且历史失败保留（宿主 mini_ed01 真实 Ledger）"
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
        OK) ledger_check "$n" 20_3 "每个语义转换的输入/输出/工具/配置/校验/人工决定记录齐全（宿主 mini_ed01 真实 Ledger）" ;;
        FAIL) fail_line "$n" "语义转换记录不完整" "$(probe_reason "$n")" ;;
        *) block_line "$n" "测试宿主匮乏" "判据探针无输出" ;;
      esac
      ;;
    20.4)
      m8_host_ok "$n" || return 0
      m8_item_all "$n" span_identity "原始数据至发布物的片段级双向追溯全部判据通过（宿主 mini_ed01）"
      ;;
    20.5)
      # CHARTER §3.3 A′：20.5 的结论由 m7-assembler.sh 的**真实退出码**决定——
      # 0 → PASS；1 → FAIL；2 → BLOCKED；3 → BLOCKED（宿主缺失）。不许写死任何一种结果。
      local m7out="" m7rc="" m7first=""
      if [ ! -f "$REPO_ROOT/openspec/acceptance/m7-assembler.sh" ]; then
        block_line "$n" "测试宿主匮乏" "m7-assembler.sh 缺失"
        return 0
      fi
      m7out="$(bash "$REPO_ROOT/openspec/acceptance/m7-assembler.sh" 2>&1)"; m7rc=$?
      case "$m7rc" in
        0) pass_line "$n" "M7 Incremental Assembly 判定全 PASS（$(printf '%s\n' "$m7out" | grep -m1 '^SUMMARY')"） ;;
        1) fail_line "$n" "M7 Incremental Assembly 判定未通过" "$(printf '%s\n' "$m7out" | grep -m1 '^FAIL ')" ;;
        2) m7first="$(printf '%s\n' "$m7out" | grep -m1 '^BLOCKED ')"
           block_line "$n" "M7 Incremental Assembly" "${m7first:-m7-assembler.sh 退出码 2 但无 BLOCKED 行}" ;;
        3) m7first="$(printf '%s\n' "$m7out" | grep -m1 '^BLOCKED ')"
           block_line "$n" "测试宿主匮乏" "${m7first:-m7-assembler.sh 退出码 3 但无 BLOCKED 行}" ;;
        *) fail_line "$n" "M7 Incremental Assembly 退出码未知" "m7-assembler.sh 退出码 $m7rc" ;;
      esac
      ;;
    20.6)
      if [ "$(grep -c 'not_captured' "$SPEC")" -lt 1 ]; then
        fail_line "$n" "Pattern 补全语义缺失" "$SPEC 中不含 not_captured 语义约定"
        return 0
      fi
      m8_host_ok "$n" || return 0
      m8_prime publication
      # 前提是 KnowledgeDataPack 真的产出；产出后 not_captured 补全的专项判据尚未实现，不许据此判 PASS
      case "$(m8_lines publication | grep -m1 '^[A-Z_]* knowledge_chain ')" in
        "PASS knowledge_chain "*) fail_line "$n" "判据未实现" "KnowledgeDataPack 已产出，但 not_captured 逐项补全的专项判据尚未实现（TODO.md T05c）" ;;
        *) m8_item_one "$n" publication knowledge_chain "-" ;;
      esac
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
      m8_host_ok "$n" || return 0
      m8_item_all "$n" publication "PublicationPackage 含结构化知识与 SourceAssetPack 且全部判据通过（宿主 mini_ed01）"
      ;;
    20.9)
      m8_host_ok "$n" || return 0
      m8_item_one "$n" publication graph_projection "GraphProjectionPack 与移动端数据同源、往返无损"
      ;;
    20.10)
      if ! bash openspec/schemas/verify.sh >/dev/null 2>&1; then
        fail_line "$n" "契约不稳定" "openspec/schemas/verify.sh 未以退出码 0 通过"
        return 0
      fi
      if [ ! -x "$PY" ]; then block_line "$n" "测试宿主匮乏" ".venv 缺失"; return 0; fi
      accept_check "$n" pipeline.contract_registry.acceptance "更换 OCR/模型/索引/存储 Adapter 不改变相邻 Module 的 Interface"
      ;;
    20.11)
      m8_host_ok "$n" || return 0
      m8_item_one "$n" publication identity_migration "IdentityMigrationMap 产出且注解锚点可迁移率达标"
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
