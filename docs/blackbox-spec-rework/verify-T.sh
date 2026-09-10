#!/usr/bin/env bash
# T 类返工项的机器判据。逐条打印 PASS / FAIL，退出码 = FAIL 条数。
# 用法: bash docs/blackbox-spec-rework/verify-T.sh
# 现在跑应当大面积 FAIL —— 那是基线，不是脚本坏了。
cd "$(dirname "$0")/../.." || exit 99
SPEC="${SPEC:-openspec/learn-system-blackbox-architecture.md}"
FAILED=0

chk() {  # chk <编号> <说明> <期望> <实得>
  if [ "$3" = "$4" ] || { [ "${3:0:2}" = ">=" ] && [ "$4" -ge "${3:2}" ]; } \
     || { [ "${3:0:2}" = "<=" ] && [ "$4" -le "${3:2}" ]; }; then
    printf 'PASS  %-6s %s\n' "$1" "$2"
  else
    printf 'FAIL  %-6s %s (期望 %s, 实得 %s)\n' "$1" "$2" "$3" "$4"; FAILED=$((FAILED+1))
  fi
}
c() { local n; n=$(grep -c "$1" "$SPEC" 2>/dev/null); echo "${n:-0}"; }   # grep -c 无匹配时 stdout 已是 0，退出码非 0 需吞掉

echo "=== T 类返工判据 (基线: 未返工时应大面积 FAIL) ==="
chk T-01 "三层术语已写入"           ">=3"  "$(c 'co_shared_\|homograph_id\|schemas/shared/canon')"
chk T-02 "§8.1 标识规范存在"        ">=1"  "$(c '8.1')"
chk T-02b "已冻结 ID 格式已搬运"     ">=4"  "$(c 'src_<work>\|ss_<work>\|ku_<technique>\|as_<technique>')"

miss=0; for v in source_verified machine_extracted cross_model_reviewed disputed needs_expert expert_verified deprecated; do
  grep -q "$v" "$SPEC" 2>/dev/null || miss=$((miss+1)); done
chk T-03 "内容状态七值齐备(缺失数)"  "0"    "$miss"
chk T-03b "错误码已搬运"             ">=3"  "$(c 'SRC_001\|TXT_001\|SEM_001')"
chk T-03c "八类审核已落枚举"         ">=3"  "$(c '来源忠实度\|流派归属\|案例真实性')"

gmiss=0; for g in G1 G2 G3 G4 G5 G6 G7; do grep -q "$g" "$SPEC" 2>/dev/null || gmiss=$((gmiss+1)); done
chk T-04 "G1-G7 已接线(缺失数)"      "0"    "$gmiss"
chk T-04b "三级消费级别已写入"       ">=3"  "$(c 'INTERNAL_DEMO\|DEV_SEARCH\|PUBLIC_RELEASE')"
chk T-04c "fail-closed 已声明"       ">=1"  "$(c 'fail-closed')"

# G3 R1 semantic gate: headings/keywords alone are insufficient. Each
# authoritative obligation must occur in the section that owns it.
sec13=$(sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")
sec16=$(sed -n '/^## 16[. ]/,/^## 17[. ]/p' "$SPEC")
for obligation in \
  '全链哈希' '确定性.*patch.*revision' 'source.*technique.*revision.*一致' \
  '适用域.*冲突' '逐 source.*technique' '全部且仅返回适用规则' \
  '已满足.*缺失.*例外' '风险簇全检'; do
  if printf '%s\n' "$sec13$sec16" | grep -Eiq "$obligation"; then
    printf 'PASS  T-04s  semantic obligation: %s\n' "$obligation"
  else
    printf 'FAIL  T-04s  semantic obligation missing: %s\n' "$obligation"; FAILED=$((FAILED+1))
  fi
done
for obligation in 'ReleaseManifest' '最低 APP 版本' 'source_release=dev'; do
  if printf '%s\n' "$sec16" | grep -Fq "$obligation"; then
    printf 'PASS  T-04s  §16 obligation: %s\n' "$obligation"
  else
    printf 'FAIL  T-04s  §16 obligation missing: %s\n' "$obligation"; FAILED=$((FAILED+1))
  fi
done
chk T-05 "evidence_level 两档"       ">=2"  "$(c 'offset_level\|glyphbox_level')"
chk T-06 "EvidenceMapPack 有说明"    ">=2"  "$(c 'EvidenceMapPack')"
evidence=$(sed -n '/`EvidenceMapPack` 提供/,/`SourceAssetPack` 按权利状态/p' "$SPEC")
# Only numbered chain entries count.  This prevents prose elsewhere in §16
# (or explanatory repeats after the chain) from satisfying an ordered check.
evidence_ok=$(printf '%s\n' "$evidence" | awk '
  BEGIN { n=0; ok=1 }
  /^[[:space:]]*[1-7]\.[[:space:]]*/ {
    n++
    if ($0 ~ /^[[:space:]]*1\.[[:space:]]*`KnowledgeEntry`[[:space:]]*[；。]?[[:space:]]*$/) hit1++
    else if ($0 ~ /^[[:space:]]*2\.[[:space:]]*`Assertion`[[:space:]]*[；。]?[[:space:]]*$/) hit2++
    else if ($0 ~ /^[[:space:]]*3\.[[:space:]]*`EvidenceLink`[[:space:]]*[；。]?[[:space:]]*$/) hit3++
    else if ($0 ~ /^[[:space:]]*4\.[[:space:]]*`SourceSpan`[[:space:]]*[；。]?[[:space:]]*$/) hit4++
    else if ($0 ~ /^[[:space:]]*5\.[[:space:]]*`SourceAnchor`[[:space:]]*[；。]?[[:space:]]*$/) hit5++
    else if ($0 ~ /^[[:space:]]*6\.[[:space:]]*`OcrPage \/ 字框坐标`[[:space:]]*[；。]?[[:space:]]*$/) hit6++
    else if ($0 ~ /^[[:space:]]*7\.[[:space:]]*`SourceAsset 页标识`[[:space:]]*[；。]?[[:space:]]*$/) hit7++
    else ok=0
  }
  END {
    if (n != 7 || hit1 != 1 || hit2 != 1 || hit3 != 1 || hit4 != 1 || hit5 != 1 || hit6 != 1 || hit7 != 1) ok=0
    print ok ? 1 : 0
  }')
chk T-06s "§16 证据链七项精确有序且闭合" "1" "$evidence_ok"

# D-07 语义门禁：TechniqueProfilePack 与 QueryContractPack
sec16=$(sed -n '/^## 16[. ]/,/^## 17[. ]/p' "$SPEC")
sec13=$(sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")

if printf '%s\n' "$sec16" | grep -Fq 'TechniqueProfilePack' \
  && printf '%s\n' "$sec16" | grep -Fq 'QueryContractPack'; then
  printf 'PASS  D-07s PublicationPackage contains TechniqueProfilePack and QueryContractPack\n'
else
  printf 'FAIL  D-07s PublicationPackage missing TechniqueProfilePack or QueryContractPack\n'; FAILED=$((FAILED+1))
fi

for query_iface in 'getEntry' 'getSourceSpan' 'searchKnowledge' 'matchFacts'; do
  if printf '%s\n' "$sec16" | grep -Fq "$query_iface"; then
    printf 'PASS  D-07s QueryContractPack interface: %s\n' "$query_iface"
  else
    printf 'FAIL  D-07s QueryContractPack missing interface: %s\n' "$query_iface"; FAILED=$((FAILED+1))
  fi
done

for tp_elem in 'FactSet Profile' 'operator 集合' 'AST schema 版本' 'Profile 版本'; do
  if printf '%s\n' "$sec16" | grep -Fq "$tp_elem"; then
    printf 'PASS  D-07s TechniqueProfile element: %s\n' "$tp_elem"
  else
    printf 'FAIL  D-07s TechniqueProfile missing element: %s\n' "$tp_elem"; FAILED=$((FAILED+1))
  fi
done

if grep -Eq '禁止.*(可执行|模型生成).*Python' "$SPEC" \
  && grep -Fq '结构化 AST/YAML/JSON' "$SPEC"; then
  printf 'PASS  D-07s rules require declarative AST and forbid executable Python\n'
else
  printf 'FAIL  D-07s rules declarative AST or Python ban missing\n'; FAILED=$((FAILED+1))
fi

if printf '%s\n' "$sec13" | grep -Fq 'FactSet' \
  && printf '%s\n' "$sec13" | grep -Fq '可执行性' \
  && printf '%s\n' "$sec13" | grep -Fq 'G6'; then
  printf 'PASS  D-07s M5 verifies FactSet rule executability under G6\n'
else
  printf 'FAIL  D-07s M5 missing FactSet rule executability under G6\n'; FAILED=$((FAILED+1))
fi

dmiss=0; for d in concepts entries assertions applicability-rules school-views evidence-links source-spans source-anchors query-contract; do
  grep -q "$d" "$SPEC" 2>/dev/null || dmiss=$((dmiss+1)); done
chk T-07 "KnowledgePack 映射表(缺失)" "0"   "$dmiss"
chk T-08 "Tag 三接口已承接"          ">=3"  "$(c 'MarkContentBinding\|EvidenceBundle\|盘面概念字典')"
chk T-08b "Tag 五字段已写入"          ">=3"  "$(c 'omen_carrying\|condition_affordance\|school_variance_display')"

qmiss=0; for q in RunStatus StageProgress PendingQueue BlockingReasons ReworkImpact ThroughputEstimate; do
  grep -q "$q" "$SPEC" 2>/dev/null || qmiss=$((qmiss+1)); done
chk T-09 "Orchestrator 六项查询(缺失)" "0"  "$qmiss"
chk T-10 "异常页终态三值"            ">=3"  "$(c 'manually_transcribed\|known_unrecognizable\|deferred')"
chk T-11 "§19 实测数字已写入"        ">=2"  "$(c '496\|148')"
# T-11 R1 semantic gates: the gap table must describe HEAD facts and use
# binary, path-sensitive criteria. Counts alone must not make stale prose pass.
sec19=$(sed -n '/^## 19[. ]/,/^## 20[. ]/p' "$SPEC")
sec190=$(printf '%s\n' "$sec19" | sed -n '/^### 19\.0 /,/^### 19\.1 /p')
if printf '%s\n' "$sec19" | grep -Fq 'pipeline/tools/ingest_epub.py' \
  && ! printf '%s\n' "$sec19" | grep -Eq '(^|[^/])tools/ingest_epub.py' ; then
  printf 'PASS  T-11s §19 uses the real ingest tool path\n'
else
  printf 'FAIL  T-11s §19 uses the real ingest tool path\n'; FAILED=$((FAILED+1))
fi
for historical in '已由 G2 修复' '历史缺口已遏制' '启动覆盖本地库' '保存即 verified'; do
  if printf '%s\n' "$sec19" | grep -Fq "$historical"; then
    printf 'PASS  T-11s historical fact: %s\n' "$historical"
  else
    printf 'FAIL  T-11s historical fact missing: %s\n' "$historical"; FAILED=$((FAILED+1))
  fi
done
if printf '%s\n' "$sec19" | grep -Fq 'git ls-files' \
  && printf '%s\n' "$sec19" | grep -Fq '.venv' \
  && printf '%s\n' "$sec19" | grep -Fq '为 3 个'; then
  printf 'PASS  T-11s tracked non-OCR test count and scope\n'
else
  printf 'FAIL  T-11s tracked non-OCR test count and scope\n'; FAILED=$((FAILED+1))
fi
for fact in '496 rules' 'original_text` 非空 0' 'is_verified=1` 为 0' 'ge_ju_versions` 0' 'conditions` 非空 404' 'chapter` 非空 486' '148 span' '18 键' '6 组碰撞'; do
  if printf '%s\n' "$sec19" | grep -Fq "$fact"; then
    printf 'PASS  T-11s HEAD fact: %s\n' "$fact"
  else
    printf 'FAIL  T-11s HEAD fact missing: %s\n' "$fact"; FAILED=$((FAILED+1))
  fi
done
criterion_rows=$(printf '%s\n' "$sec19" | awk '/^### 19\.0 /,/^### 19\.1 / { if ($0 ~ /^\|/ && $0 !~ /^\|---/) n++ } END { print n+0 }')
chk T-11s "§19 当前差距均列二元判据" ">=15" "$criterion_rows"
if printf '%s\n' "$sec190" | grep -Fq '当前失败' \
  && printf '%s\n' "$sec190" | grep -Fq '修复后判据'; then
  printf 'PASS  T-11s binary criteria are explicit\n'
else
  printf 'FAIL  T-11s binary criteria are explicit\n'; FAILED=$((FAILED+1))
fi
# Every 19.0 data row must contain executable commands on both sides.  A
# prose-only "修复后" cell must never satisfy the row-count gate.
bad_rows=$(printf '%s\n' "$sec190" | awk -F'`' '/^\|/ && $0 !~ /^\|---/ && $0 !~ /差距.*修复前/ {
  if (NF != 5 || index($0, "exit ") == 0 || $0 ~ /test \$\? -ne 0/ || $4 !~ /openspec\/acceptance\//) n++
} END { print n+0 }')
chk T-11s "§19.0 每行两侧均为命令且有期望退出码" "0" "$bad_rows"
chk T-12 "§19 施工顺序说明"          ">=1"  "$(c '非施工顺序\|前置层')"
# T-13 is deliberately structural: the label must be the first non-empty
# line after each exact §3–§18 heading, and must match the closed mapping.
# Counting labels alone lets a moved label or a mislabeled section go green.
t13_map=$(awk '
  BEGIN { want[3]="讨论候选"; want[4]="待验证假设"; want[5]="已确认设计"; want[6]="已确认设计"; want[7]="待验证假设"; want[8]="待验证假设"; want[9]="讨论候选"; want[10]="待验证假设"; want[11]="待验证假设"; want[12]="待验证假设"; want[13]="待验证假设"; want[14]="待验证假设"; want[15]="讨论候选"; want[16]="待验证假设"; want[17]="待验证假设"; want[18]="已确认设计"; ok=1 }
  /^## (3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18)\.[[:space:]]/ {
    n=$2; sub(/\..*/,"",n); seen[n]++ ; pending=n; next
  }
  pending && NF { if ($0 != "状态：" want[pending]) ok=0; pending=0 }
  END { for (i=3;i<=18;i++) if (seen[i] != 1) ok=0; print ok ? 1 : 0 }
' "$SPEC")
chk T-13 "§3–§18章节号→状态映射"      "1"    "$t13_map"
local_candidate=$(awk '
  /建议一个 Technique 一个 Release/ { found=1; if (prev == "状态：讨论候选") ok=1; while (getline after) { if (after ~ /[^[:space:]]/) { if (after == "状态：讨论候选") ok=1; break } } next }
  { prev=$0 }
  END { print (found && ok) ? 1 : 0 }
' "$SPEC")
chk T-13a "§16建议句局部讨论候选"      "1"    "$local_candidate"
chk T-13b "无节被标最终规范"          "0"    "$(c '^状态：最终规范')"

echo
echo "=== D 类前置(仅提示，不计入退出码) ==="
printf '  entity_id 拆分:        %s 处\n' "$(c 'entity_id')"
printf '  KnowledgeEntry 归位:   %s 处 (目标 >=3)\n' "$(c 'KnowledgeEntry')"
printf '  EditionPart 定义:      %s 处\n' "$(c 'EditionPart')"
printf '  失效传播改写:          残留「M3 至 M6 全部失效」%s 处 (目标 0)\n' "$(c 'M3 至 M6 全部失效')"
printf '  §20 判据脚本:          %s\n' "$([ -f openspec/acceptance/run_all.sh ] && echo 存在 || echo 缺失)"
printf '  fixture Edition:       %s\n' "$([ -d pipeline/corpus/_fixture/mini_ed01 ] && echo 存在 || echo 缺失)"
printf '  RN-1 旧完成标准残留:   %s 处 (目标 0)\n' "$(c 'PublicationPackage 同时包含结构化知识、原始资料')"
printf '  RN-2 身份拆分:         entity_id=%s / artifact_revision_id=%s\n' "$(c 'entity_id')" "$(c 'artifact_revision_id')"
printf '  RN-3 人工挂起态:       awaiting_human=%s / resume_token=%s\n' "$(c 'awaiting_human')" "$(c 'resume_token')"

echo
echo "FAIL 合计: $FAILED"
exit "$FAILED"
