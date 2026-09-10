#!/usr/bin/env bash
# T 类返工项的机器判据。逐条打印 PASS / FAIL，退出码 = FAIL 条数。
# 用法: bash docs/blackbox-spec-rework/verify-T.sh
# 现在跑应当大面积 FAIL —— 那是基线，不是脚本坏了。
cd "$(dirname "$0")/../.." || exit 99
SPEC="openspec/learn-system-blackbox-architecture.md"
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
chk T-12 "§19 施工顺序说明"          ">=1"  "$(c '非施工顺序\|前置层')"
chk T-13 "章节状态标签"              ">=16" "$(c '^状态：')"
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
