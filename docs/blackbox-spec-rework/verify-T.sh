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

# D-07 语义门禁：TechniqueProfilePack / QueryContractPack / RuleIndexPack 三份契约
# 必须各自在专属段内闭合。§16 其余文字（如 ReleaseManifest 的「Schema/Profile 版本」）
# 不得跨块代偿，因此先按专属段导语切片，再逐块断言，而不是对整节做关键词 grep。
sec13=$(sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")

tp_anchor='承载各术数领域确定性事实结构与规则语法标准'
qc_anchor='规范发布包对外暴露的确定性只读查询契约'
ri_anchor='承载确定性适用规则索引'

d07_blocks=$(awk -v tp="$tp_anchor" -v qc="$qc_anchor" -v ri="$ri_anchor" '
  /^#/ { cur = "" }
  index($0, tp) > 0 { cur = "TP" }
  index($0, qc) > 0 { cur = "QC" }
  index($0, ri) > 0 { cur = "RI" }
  cur != "" { print cur "\t" $0 }
' "$SPEC")

d07_block() { printf '%s\n' "$d07_blocks" | awk -F'\t' -v k="$1" '$1 == k { sub(/^[^\t]*\t/, ""); print }'; }
d07_f() { printf '%s\n' "$1" | grep -Fq "$2"; }
d07_e() { printf '%s\n' "$1" | grep -Eq "$2"; }

for d07_pair in "TP:$tp_anchor" "QC:$qc_anchor" "RI:$ri_anchor"; do
  d07_key=${d07_pair%%:*}; d07_anchor=${d07_pair#*:}
  if [ -n "$(d07_block "$d07_key" | grep -v '^$')" ] && [ "$(grep -Fc "$d07_anchor" "$SPEC")" = "1" ]; then
    printf 'PASS  D-07s %s dedicated block located\n' "$d07_key"
  else
    printf 'FAIL  D-07s %s dedicated block missing or ambiguous\n' "$d07_key"; FAILED=$((FAILED+1))
  fi
done

d07_tp=$(d07_block TP); d07_qc=$(d07_block QC); d07_ri=$(d07_block RI)

for tp_elem in 'FactSet Profile' 'operator 集合' 'AST schema 版本'; do
  if d07_f "$d07_tp" "$tp_elem"; then
    printf 'PASS  D-07s TechniqueProfilePack element: %s\n' "$tp_elem"
  else
    printf 'FAIL  D-07s TechniqueProfilePack missing element: %s\n' "$tp_elem"; FAILED=$((FAILED+1))
  fi
done

if d07_f "$d07_tp" '事实字段与枚举' && d07_f "$d07_tp" '闭集枚举' \
  && ! d07_e "$d07_tp" '客户端自由猜测|不列.*事实字段|由客户端.*猜|无需列出.*枚举'; then
  printf 'PASS  D-07s TechniqueProfilePack mandates fact fields and closed enum values\n'
else
  printf 'FAIL  D-07s TechniqueProfilePack fact fields / closed enums missing or negated\n'; FAILED=$((FAILED+1))
fi

if d07_e "$d07_tp" '禁止.*(可执行|模型生成).*Python'; then
  printf 'PASS  D-07s TechniqueProfilePack forbids executable or model-generated Python\n'
else
  printf 'FAIL  D-07s TechniqueProfilePack Python ban missing\n'; FAILED=$((FAILED+1))
fi

for query_iface in 'getEntry' 'getSourceSpan' 'searchKnowledge' 'matchFacts'; do
  if d07_f "$d07_qc" "$query_iface"; then
    printf 'PASS  D-07s QueryContractPack interface: %s\n' "$query_iface"
  else
    printf 'FAIL  D-07s QueryContractPack missing interface: %s\n' "$query_iface"; FAILED=$((FAILED+1))
  fi
done

if d07_f "$d07_qc" '向后兼容'; then
  printf 'PASS  D-07s QueryContractPack declares backward compatibility\n'
else
  printf 'FAIL  D-07s QueryContractPack missing backward compatibility\n'; FAILED=$((FAILED+1))
fi

if d07_f "$d07_ri" '每条规则' && d07_f "$d07_ri" '显式声明' \
  && d07_f "$d07_ri" 'profile_version' && d07_f "$d07_ri" 'AST schema 版本'; then
  printf 'PASS  D-07s RuleIndexPack binds every rule to profile_version and AST schema version\n'
else
  printf 'FAIL  D-07s RuleIndexPack per-rule profile_version / AST schema version missing\n'; FAILED=$((FAILED+1))
fi

if d07_f "$d07_ri" '结构化 AST/YAML/JSON'; then
  printf 'PASS  D-07s RuleIndexPack keeps rules declarative AST/YAML/JSON\n'
else
  printf 'FAIL  D-07s RuleIndexPack rules not declarative AST/YAML/JSON\n'; FAILED=$((FAILED+1))
fi

if printf '%s\n' "$sec13" | grep -Fq 'FactSet' \
  && printf '%s\n' "$sec13" | grep -Fq '可执行性' \
  && printf '%s\n' "$sec13" | grep -Fq 'G6' \
  && printf '%s\n' "$sec13" | grep -Fq '不负责生产'; then
  printf 'PASS  D-07s M5 verifies FactSet executability under G6 and produces no contract\n'
else
  printf 'FAIL  D-07s M5 FactSet executability or non-producer boundary missing\n'; FAILED=$((FAILED+1))
fi

sec16=$(sed -n '/^## 16[. ]/,/^## 17[. ]/p' "$SPEC")
if printf '%s\n' "$sec16" | grep -Fq 'TechniqueProfilePack' \
  && printf '%s\n' "$sec16" | grep -Fq 'QueryContractPack'; then
  printf 'PASS  D-07s PublicationPackage lists TechniqueProfilePack and QueryContractPack\n'
else
  printf 'FAIL  D-07s PublicationPackage missing TechniqueProfilePack or QueryContractPack\n'; FAILED=$((FAILED+1))
fi

# T-07 语义门禁：§16.2 KnowledgePack 双向映射表精确解析。
# 右列必须是唯一落点：既不能缺少正确归属，也不能在正确归属之后追加第二个子包，
# 因此改为规范化后精确相等，而不是子串匹配。
sec162=$(sed -n '/^### 16\.2 /,/^### 16\.3 /p' "$SPEC")
t07_errs=$(printf '%s\n' "$sec162" | awk -F'|' '
  function nz(s) { gsub(/`/, "", s); gsub(/[[:space:]]/, "", s); return s }
  BEGIN {
    wanted["release-manifest"]=1
    wanted["schema"]=1
    wanted["concepts"]=1
    wanted["entries"]=1
    wanted["assertions"]=1
    wanted["applicability-rules"]=1
    wanted["school-views"]=1
    wanted["evidence-links"]=1
    wanted["source-spans"]=1
    wanted["source-anchors"]=1
    wanted["scan-assets-or-references"]=1
    wanted["exact-search-index"]=1
    wanted["fulltext-index"]=1
    wanted["optional-vector-index"]=1
    wanted["query-contract"]=1
  }
  /^\|/ && $0 !~ /^\|---/ && $0 !~ /早期.*目录/ {
    c1=nz($2)
    c2=nz($3)
    if (c1 in wanted) {
      seen[c1]++
      target[c1]=c2
    }
    total++
  }
  END {
    err=""
    if (total != 15) err=err "行数!=15(" total "); "
    for (k in wanted) {
      if (seen[k] != 1) err=err k "=" seen[k] "; "
    }
    if (target["query-contract"] != "QueryContractPack（查询契约与接口定义）") err=err "query-contract归属[" target["query-contract"] "]，期望[QueryContractPack（查询契约与接口定义）]; "
    if (target["optional-vector-index"] != "本期不产出（依据§21非目标）") err=err "optional-vector-index归属[" target["optional-vector-index"] "]，期望[本期不产出（依据§21非目标）]; "
    if (err == "") print "OK"
    else print err
  }
')

if [ "$t07_errs" = "OK" ]; then
  printf 'PASS  T-07s §16.2 映射表15项唯一且query-contract正确归属QueryContractPack\n'
else
  printf 'FAIL  T-07s §16.2 映射表不合规: %s\n' "$t07_errs"; FAILED=$((FAILED+1))
fi

# 取代声明必须是同一句肯定语义：同一行内同时出现 PublicationPackage、KnowledgeDataPack、
# 正式取代、KnowledgePack；「不得取代」等否定句一律判失败。
t07_decl=0
if printf '%s\n' "$sec162" | grep -F '正式取代' | grep -F 'PublicationPackage' \
  | grep -F 'KnowledgeDataPack' | grep -Fq 'KnowledgePack'; then
  t07_decl=1
fi
if printf '%s\n' "$sec162" | grep -Eq '不得取代|不予取代|禁止取代|未予取代|不取代'; then
  t07_decl=0
fi
if [ "$t07_decl" = "1" ]; then
  printf 'PASS  T-07s §16.2 affirmative replacement statement with PublicationPackage and KnowledgeDataPack\n'
else
  printf 'FAIL  T-07s §16.2 replacement statement missing or negated\n'; FAILED=$((FAILED+1))
fi

# T-08 语义门禁：Tag 三接口供给包、五字段 owner/package、M5 生产者排除及 G4 命名空间。
# 生产 Module 与归属子包必须逐字段精确匹配：只校验字段唯一和 M5 缺席会漏掉错误归属。
sec163=$(sed -n '/^### 16\.3 /,/^## 17/p' "$SPEC")
sec1631=$(sed -n '/^#### 16\.3\.1 /,/^#### 16\.3\.2 /p' "$SPEC")
sec01=$(sed -n '/^## 1\.[[:space:]]/,/^## 2\.[[:space:]]/p' "$SPEC")

# 1. 三接口承接与“不含规则 DSL”
for tag_iface in '最小盘面概念字典' 'MarkContentBinding' 'EvidenceBundle'; do
  if printf '%s\n' "$sec163" | grep -Fq "$tag_iface" && printf '%s\n' "$sec01" | grep -Fq "$tag_iface"; then
    printf 'PASS  T-08s Tag interface present in §1 and §16.3: %s\n' "$tag_iface"
  else
    printf 'FAIL  T-08s Tag interface missing: %s\n' "$tag_iface"; FAILED=$((FAILED+1))
  fi
done

if printf '%s\n' "$sec163" | grep -Fq '不含规则 DSL' && printf '%s\n' "$sec01" | grep -Fq '不含规则 DSL'; then
  printf 'PASS  T-08s concept dictionary preserves rule DSL restriction\n'
else
  printf 'FAIL  T-08s concept dictionary missing rule DSL restriction\n'; FAILED=$((FAILED+1))
fi

# 2. 三接口供给子包精确校验：§16.3.1 的「供给子包」行与 §1 的「由 … 供给」片段必须同时正确
t08_supply_1631() {
  printf '%s\n' "$sec1631" | awk -v name="$1" '
    function nz(s){ gsub(/`/,"",s); gsub(/[*]/,"",s); gsub(/[-]/,"",s); gsub(/[[:space:]]/,"",s); gsub(/：/,"",s); gsub(/；/,"",s); return s }
    /^[0-9]+\.[[:space:]]+\*\*/ { inb = (index($0, name) > 0) }
    inb && nz($0) ~ /供给子包/ { print nz($0); exit }
  '
}
t08_supply_sec01() {
  printf '%s\n' "$sec01" | grep -F "$1" | head -1 \
    | sed -n 's/^[^由]*由[[:space:]]*\([^供]*\)供给.*$/\1/p' \
    | sed -e 's/`//g' -e 's/[[:space:]]//g'
}
for t08_iface_pair in '最小盘面概念字典:KnowledgeDataPack' 'MarkContentBinding:KnowledgeDataPack与RuleIndexPack' 'EvidenceBundle:EvidenceMapPack'; do
  t08_iface=${t08_iface_pair%%:*}; t08_pkg=${t08_iface_pair#*:}
  if [ "$(t08_supply_1631 "$t08_iface")" = "供给子包由${t08_pkg}供给" ] \
    && [ "$(t08_supply_sec01 "$t08_iface")" = "$t08_pkg" ]; then
    printf 'PASS  T-08s interface supply package: %s -> %s\n' "$t08_iface" "$t08_pkg"
  else
    printf 'FAIL  T-08s interface supply package mismatch: %s (期望 %s)\n' "$t08_iface" "$t08_pkg"; FAILED=$((FAILED+1))
  fi
done

# 3. Tag 侧 G4 命名空间消歧
if printf '%s\n' "$sec01" | grep -Eq 'TAG_SYSTEM_DESIGN\.md §12\.2.*G4' \
  && printf '%s\n' "$sec163" | grep -Eq 'TAG_SYSTEM_DESIGN\.md §12\.2.*G4' \
  && ! printf '%s\n' "$sec163" | grep -Eq '解除.*（G4）'; then
  printf 'PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2\n'
else
  printf 'FAIL  T-08s Tag G4 missing TAG_SYSTEM_DESIGN.md namespace\n'; FAILED=$((FAILED+1))
fi

# 4. §16.3.2 字段表格：五字段各恰好一次，生产 Module 与归属子包逐字段精确相等，生产列不得含 M5
t08_table_res=$(printf '%s\n' "$sec163" | awk -F'|' '
  function nz(s){ gsub(/`/,"",s); gsub(/[[:space:]]/,"",s); return s }
  BEGIN {
    want["omen_carrying"]="M4|KnowledgeDataPack"
    want["condition_affordance"]="M4|RuleIndexPack与KnowledgeDataPack"
    want["school_variance_display"]="M4/M6|KnowledgeDataPack"
    want["concept_id"]="M4|KnowledgeDataPack"
    want["是否改变当前判断"]="M4/M7/M6|KnowledgeDataPack（MarkContentBinding）"
  }
  /^\|/ && $0 !~ /^\|---/ && $0 !~ /字段名.*语义定义/ {
    name=nz($2); prod=nz($4); pack=nz($5)
    rows++
    if (name in want) {
      seen[name]++
      if ((prod "|" pack) != want[name]) err=err name "实际[" prod "|" pack "]，期望[" want[name] "]; "
      if (prod ~ /M5/) err=err name "生产列包含M5; "
    }
  }
  END {
    if (rows != 5) err=err "数据行=" rows "; "
    for (k in want) if (seen[k] != 1) err=err k "出现" seen[k] "次; "
    print (err == "" ? "OK" : err)
  }
')

if [ "$t08_table_res" = "OK" ]; then
  printf 'PASS  T-08s §16.3 table 5 fields with exact producer ownership and no M5 producer\n'
else
  printf 'FAIL  T-08s §16.3 table issue: %s\n' "$t08_table_res"; FAILED=$((FAILED+1))
fi

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
