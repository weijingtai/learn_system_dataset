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

# G3 R3 精确结构门禁：D-07 / T-07 / T-08
# ---------------------------------------------------------------------
# 本段所有 sed / grep / awk 一律通过 g3_sed / g3_grep / g3_awk 包一层 LC_ALL=C。
# 原因：macOS BSD awk 在 en_US.UTF-8 下会把两个无关的中文串判为相等
# （实测 "是否改变当前判断" == "字段名" 返回真），sed/grep 的多字节类也不确定。
# LC_ALL=C 使比较退化为逐字节比较，精确且可复现。
# 注意：不能全局 export LC_ALL=C —— 脚本其他段落（T-06s、T-08s 历史判据）依赖
# en_US.UTF-8 下的多字节括号表达式与 `[^由]` 这类字符类，全局切换会让它们误报。
g3_sed()  { LC_ALL=C sed "$@"; }
g3_grep() { LC_ALL=C grep "$@"; }
g3_awk()  { LC_ALL=C awk "$@"; }

# 规范化只删除 Markdown 反引号、星号、空格、Tab 与 CR；其余字符（含否定词、
# 标点、数字、斜杠、§ 与标识符）全部保留。期望值全部硬编码自权威常量文件，
# 绝不从 $SPEC 动态生成。判定不做否定词枚举：任何改写都因「完整规范行不再
# 精确出现且仅出现一次」而被拒绝，因此未知的否定句式同样无法绕过。
g3n() { g3_sed -e 's/`//g' -e 's/\*//g' -e 's/[[:space:]]//g'; }
g3cnt() { printf '%s\n' "$2" | g3_grep -Fxc -- "$1"; }   # $1 已规范化规范行, $2 已规范化段落
g3norm() { printf '%s\n' "$1" | g3n; }

g3_exact() {   # g3_exact <FAIL-ID> <段落> <标签> <规范行> [<标签> <规范行> ...]
  local id="$1" body; body=$(printf '%s\n' "$2" | g3n); shift 2
  local bad="" label line n
  while [ $# -gt 0 ]; do
    label="$1"; line="$2"; shift 2
    n=$(g3cnt "$(g3norm "$line")" "$body")
    [ "$n" = "1" ] || bad="$bad ${label}(x$n)"
  done
  if [ -z "$bad" ]; then
    printf 'PASS  %s\n' "$id"
  else
    printf 'FAIL  %s  规范行未精确出现一次:%s\n' "$id" "$bad"; FAILED=$((FAILED+1))
  fi
}

g3_packs() { g3_grep -oE '[A-Za-z][A-Za-z0-9]*Pack' | LC_ALL=C sort -u \
  | g3_awk 'BEGIN{ORS=""} {print (NR>1?",":"") $0}'; }

# ---- 权威规范行（照抄自 work-items/g3-r3/CANONICAL.md，硬编码） ----
C_D07_TP_START='`TechniqueProfilePack` 承载各术数领域确定性事实结构与规则语法标准，消除跨技法匹配歧义：'
C_D07_TP_PROFILE='- **FactSet Profile**：针对不同术数体系定义专用事实切片 Profile，包括八字 `BaziFactSet`、七政 `QizhengFactSet`、紫微 `ZiweiFactSet`、奇门 `QimenFactSet`、六壬 `LiuRenFactSet`；依 2026-09-08 用户裁定，首纵切内部验收包采用 `QizhengFactSet`；'
C_D07_TP_FIELDS='- **事实字段与枚举**：严格列出各 Profile 允许的事实键名、数据类型及闭集枚举值，禁止非受控字段参与确定性匹配；'
C_D07_TP_OPERATORS='- **operator 集合**：规范规则条件所允许的确定性比较与集合操作符全集（如 `eq`、`neq`、`in`、`not_in`、`gt`、`gte`、`lt`、`lte`、`all`、`any`、`none`）；'
C_D07_TP_AST='- **AST schema 版本**：定义规则 AST 的结构化模式版本（如 `ast_schema_version: "1.0"`），规则纯声明式表达，**禁止使用任何可执行或模型生成的 Python 规则**。'
C_D07_QC_START='`QueryContractPack` 规范发布包对外暴露的确定性只读查询契约与客户端调用接口，定义四个核心接口及兼容声明：'
C_D07_QC_ENTRY='- **`getEntry(entry_id)`**：按稳定实体标识获取对应 `KnowledgeEntry` 条目及其主张和上下文；'
C_D07_QC_SPAN='- **`getSourceSpan(span_id)`**：按片段标识获取底层 `SourceSpan` 原文、校勘与定位引用；'
C_D07_QC_SEARCH='- **`searchKnowledge(query, filters)`**：执行跨条目/术语的精确与全文知识检索；'
C_D07_QC_MATCH='- **`matchFacts(fact_set)`**：输入版本化 FactSet，执行确定性规则匹配并返回全部且仅返回适用规则，明确报告已满足条件、缺失条件与触发例外；任一条件不全或例外成立时不得输出肯定判断；'
C_D07_QC_COMPAT='- **向后兼容声明**：明确规定查询契约接口必须保持向后兼容演进，客户端只依赖稳定接口契约，不直接绑定底层文件存储形式。'
C_D07_RI_START='`RuleIndexPack` 承载确定性适用规则索引：'
C_D07_RI_VERSION='- **Profile 版本声明**：`RuleIndexPack` 中每条规则必须显式声明其所依据的 `Profile 版本`（如 `profile_version: "qizheng_v1.0"`）及 `AST schema 版本`；'
C_D07_RI_DECLARATIVE='- **规则纯声明式结构**：所有适用规则必须使用纯声明式的 `结构化 AST/YAML/JSON` 表达，禁止包含任何动态 Python 逻辑或自由文本代码块。'

C_T07_REPLACEMENT='黑箱架构规格以多子包组合的 `PublicationPackage`（特别是其中的结构化知识主体 `KnowledgeDataPack`）正式取代早期草案中单一扁平的 `KnowledgePack` 概念。'

C_T08_S1_01='1. `最小盘面概念字典`：规模约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅包含稳定 `concept_id` + 名称 + 基础类象，**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题；'
C_T08_S1_02='2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，为 UI 标记提供内容与分歧数据；'
C_T08_S1_03='3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为解盘与证据高亮提供底层的无损证据链切片。'
C_T08_B1_HEAD='1. **`最小盘面概念字典`**：'
C_T08_B1_SUPPLY='   - **供给子包**：由 `KnowledgeDataPack` 供给；'
C_T08_B1_LIMIT='   - **硬限制约束**：**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题。规则 DSL 属于后续阶段的 RuntimeFeature 范围，不在最小概念字典中承载。'
C_T08_B2_HEAD='2. **`MarkContentBinding` 内容供给**：'
C_T08_B2_SUPPLY='   - **供给子包**：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给；'
C_T08_B3_HEAD='3. **`EvidenceBundle` 服务**：'
C_T08_B3_SUPPLY='   - **供给子包**：由 `EvidenceMapPack` 供给；'
C_T08_P01='- `omen_carrying`（吉凶承载性）：指示该标记是否承载吉凶定性，由 M4 生产，归入 `KnowledgeDataPack`（由 M5 负责校验其合规性，M5 不得作为字段生产者）；'
C_T08_P02='- `condition_affordance`（条件可供性）：指示该标记可承载的条件槽位，由 M4 结构化生产，归入 `RuleIndexPack` 与 `KnowledgeDataPack`（由 M5 负责校验其可执行性，M5 不得作为字段生产者）；'
C_T08_P03='- `school_variance_display`（流派分歧展示）：指示各流派对此标记的不同定性或观点分歧，由 M4/M6 审核产出，归入 `KnowledgeDataPack`；'
C_T08_P04='- `concept_id`（概念标识）：全局稳定的概念 ID，由 M4 术语判层确定，归入 `KnowledgeDataPack`；'
C_T08_P05='- 「是否改变当前判断」：明确规定属于 `MarkContentBinding` 的核心内容状态字段，必须由知识层（M4/M7/M6）通过判定状态供给，**UI 不得猜测**。'
C_T08_R01='| `omen_carrying` | 吉凶承载性：指示该标记是否承载吉凶定性 | M4 | `KnowledgeDataPack` | 满足吉凶标定标准（`canonical` / `none`），严禁 UI 自行推导吉凶；M5 仅作为 Validator 负责检验标定合规性，不得作为生产者 |'
C_T08_R02='| `condition_affordance` | 条件可供性：指示该标记可承载的条件槽位 | M4 | `RuleIndexPack` 与 `KnowledgeDataPack` | 结构化输出条件依赖；当 `omen_carrying=canonical` 时必填；M5 仅作为 Validator 负责校验规则可执行性，不得作为生产者 |'
C_T08_R03='| `school_variance_display` | 流派分歧展示：指示各流派对此标记的不同定性或观点分歧 | M4 / M6 | `KnowledgeDataPack` | 存在流派分歧的知识点强制展示多流派对照，严禁单一流派静默覆盖 |'
C_T08_R04='| `concept_id` | 概念标识：全局稳定的概念 ID | M4 | `KnowledgeDataPack` | 术语判层产出的稳定概念 ID，盘面语义物种必须绑定 |'
C_T08_R05='| 是否改变当前判断 | 指示分歧是否导致格局或断语定性翻转 | M4 / M7 / M6 | `KnowledgeDataPack`（`MarkContentBinding`） | 核心内容状态字段，必须由知识层通过判定状态与 ReviewDecision 供给，**UI 不得猜测** |'

sec16=$(g3_sed -n '/^## 16[. ]/,/^## 17[. ]/p' "$SPEC")
sec162=$(g3_sed -n '/^### 16\.2 /,/^### 16\.3 /p' "$SPEC")
sec01=$(g3_sed -n '/^## 1\.[[:space:]]/,/^## 2\.[[:space:]]/p' "$SPEC")
sec1631=$(g3_sed -n '/^#### 16\.3\.1 /,/^#### 16\.3\.2 /p' "$SPEC")
sec1632=$(g3_sed -n '/^#### 16\.3\.2 /,/^## 17/p' "$SPEC")
sec13=$(g3_sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")

# ---------------- D-07：三份契约的完整规范行 ----------------
g3_exact G3-D07-TP "$sec16" \
  TP-START "$C_D07_TP_START" TP-PROFILE "$C_D07_TP_PROFILE" \
  TP-FIELDS "$C_D07_TP_FIELDS" TP-OPERATORS "$C_D07_TP_OPERATORS" \
  TP-AST "$C_D07_TP_AST"
g3_exact G3-D07-QC "$sec16" \
  QC-START "$C_D07_QC_START" QC-ENTRY "$C_D07_QC_ENTRY" \
  QC-SPAN "$C_D07_QC_SPAN" QC-SEARCH "$C_D07_QC_SEARCH" \
  QC-MATCH "$C_D07_QC_MATCH"
g3_exact G3-D07-RI "$sec16" \
  RI-START "$C_D07_RI_START" RI-VERSION "$C_D07_RI_VERSION" \
  RI-DECLARATIVE "$C_D07_RI_DECLARATIVE"
g3_exact G3-D07-COMPAT "$sec16" QC-COMPAT "$C_D07_QC_COMPAT"

# 四个查询接口的完整签名（不使用 getEntry 等子串存在性判断）
for iface in 'getEntry(entry_id)' 'getSourceSpan(span_id)' 'searchKnowledge(query, filters)' 'matchFacts(fact_set)'; do
  if printf '%s\n' "$sec16" | g3n | g3_grep -Fq -- "$(g3norm "$iface")"; then
    printf 'PASS  G3-D07-QC  接口签名完整: %s\n' "$iface"
  else
    printf 'FAIL  G3-D07-QC  接口签名缺失或被改名: %s\n' "$iface"; FAILED=$((FAILED+1))
  fi
done

if printf '%s\n' "$sec13" | g3_grep -Fq 'FactSet' \
  && printf '%s\n' "$sec13" | g3_grep -Fq '可执行性' \
  && printf '%s\n' "$sec13" | g3_grep -Fq 'G6' \
  && printf '%s\n' "$sec13" | g3_grep -Fq '不负责生产'; then
  printf 'PASS  D-07s M5 verifies FactSet executability under G6 and produces no contract\n'
else
  printf 'FAIL  D-07s M5 FactSet executability or non-producer boundary missing\n'; FAILED=$((FAILED+1))
fi

# ---------------- T-07：§16.2 完整映射表 ----------------
t07_map_err=$(printf '%s\n' "$sec162" | g3_awk -F'|' '
  function nz(s){ gsub(/`/,"",s); gsub(/\*/,"",s); gsub(/[[:space:]]/,"",s); return s }
  BEGIN {
    want["release-manifest"]="ReleaseManifest（发布清单与元数据摘要）"
    want["schema"]="KnowledgeDataPack（及ContractRegistry对应模式定义）"
    want["concepts"]="KnowledgeDataPack（概念定义及术语体系）"
    want["entries"]="KnowledgeDataPack（知识条目KnowledgeEntry集合）"
    want["assertions"]="KnowledgeDataPack（结构化主张Assertion集合）"
    want["applicability-rules"]="RuleIndexPack（与KnowledgeDataPack中的适用规则）"
    want["school-views"]="KnowledgeDataPack（各流派分歧与立场视图）"
    want["evidence-links"]="EvidenceMapPack（证据链接与跨层关联）"
    want["source-spans"]="EvidenceMapPack（与KnowledgeDataPack中的原文片段引用）"
    want["source-anchors"]="EvidenceMapPack（底本物理位置证据锚点，必须随包发布）"
    want["scan-assets-or-references"]="SourceAssetPack（扫描图或受控引用）"
    want["exact-search-index"]="SearchIndexPack（精确检索索引）"
    want["fulltext-index"]="SearchIndexPack（全文检索索引）"
    want["optional-vector-index"]="本期不产出（依据§21非目标）"
    want["query-contract"]="QueryContractPack（查询契约与接口定义）"
    hdr="早期KnowledgePack目录建议(TARGET.md§9)"
  }
  /^\|/ {
    k=nz($2); v=nz($3)
    if (k == hdr) next
    if (k ~ /^[-:]+$/) next
    rows++
    cnt[k]++
    got[k]=v
    if (!(k in want)) extra=extra " [" k "]"
  }
  END {
    e=""
    if (rows != 15) e=e " 数据行=" rows "(期望15)"
    for (x in want) {
      if (cnt[x] != 1) e=e " " x "(x" cnt[x] ")"
      else if (got[x] != want[x]) e=e " " x "=[" got[x] "]期望=[" want[x] "]"
    }
    if (extra != "") e=e " 未知key:" extra
    print (e == "" ? "OK" : e)
  }
')
if [ "$t07_map_err" = "OK" ]; then
  printf 'PASS  G3-T07-MAP  §16.2 映射表 15 项 key 唯一且 value 完整相等\n'
else
  printf 'FAIL  G3-T07-MAP  §16.2 映射表不合规:%s\n' "$t07_map_err"; FAILED=$((FAILED+1))
fi

t07_repl_n=$(g3cnt "$(g3norm "$C_T07_REPLACEMENT")" "$(printf '%s\n' "$sec162" | g3n)")
if [ "$t07_repl_n" = "1" ]; then
  printf 'PASS  G3-T07-REPLACEMENT  §16.2 取代声明完整句唯一且肯定\n'
else
  printf 'FAIL  G3-T07-REPLACEMENT  §16.2 取代声明未完整精确出现一次(x%s)\n' "$t07_repl_n"; FAILED=$((FAILED+1))
fi

# ---------------- T-08：§1 三行 / §16.3.1 三块 / §16.3.2 五条与五行 ----------------
t08_sec1_bad=""
t08_idx=0
for pair in "最小盘面概念字典|KnowledgeDataPack|$C_T08_S1_01" \
            "MarkContentBinding|KnowledgeDataPack,RuleIndexPack|$C_T08_S1_02" \
            "EvidenceBundle|EvidenceMapPack|$C_T08_S1_03"; do
  t08_idx=$((t08_idx+1))
  want_pkgs="${pair#*|}"; want_pkgs="${want_pkgs%|*}"
  line="${pair##*|}"
  n=$(g3cnt "$(g3norm "$line")" "$(printf '%s\n' "$sec01" | g3n)")
  [ "$n" = "1" ] || t08_sec1_bad="$t08_sec1_bad S1-0$t08_idx(x$n)"
done
t08_pk1=$(printf '%s\n' "$C_T08_S1_01" | g3_packs)
t08_pk2=$(printf '%s\n' "$C_T08_S1_02" | g3_packs)
t08_pk3=$(printf '%s\n' "$C_T08_S1_03" | g3_packs)
[ "$t08_pk1" = "KnowledgeDataPack" ] || t08_sec1_bad="$t08_sec1_bad S1-01包集合异常($t08_pk1)"
[ "$t08_pk2" = "KnowledgeDataPack,RuleIndexPack" ] || t08_sec1_bad="$t08_sec1_bad S1-02包集合异常($t08_pk2)"
[ "$t08_pk3" = "EvidenceMapPack" ] || t08_sec1_bad="$t08_sec1_bad S1-03包集合异常($t08_pk3)"
t08_pk_mut=$(printf '%s\n' "$sec01" | g3_grep -F '最小盘面概念字典' | head -1 | g3_packs)
[ "$t08_pk_mut" = "KnowledgeDataPack" ] || t08_sec1_bad="$t08_sec1_bad §1实际包集合异常($t08_pk_mut)"
if [ -z "$t08_sec1_bad" ]; then
  printf 'PASS  G3-T08-SEC1  §1 三接口行完整且各含唯一供给包\n'
else
  printf 'FAIL  G3-T08-SEC1  §1 三接口行不合规:%s\n' "$t08_sec1_bad"; FAILED=$((FAILED+1))
fi

t08_blocks=$(printf '%s\n' "$sec1631" | g3_awk '
  /^[1-3]\.[[:space:]]+\*\*/ { n++ }
  n > 0 { print n "\t" $0 }
')
# 注意：不能用 sub(/^[^\t]*\t/,"") —— 花括号表达式里的 \t 在 BSD awk 中不是制表符转义。
# 用 index/substr 精确去掉 "<块号>\t" 前缀。
t08_block_lines() { printf '%s\n' "$t08_blocks" | g3_awk -F'\t' -v k="$1" '
  $1 == k { p = index($0, "\t"); if (p > 0) $0 = substr($0, p + 1); print }'; }
t08_nblocks=$(printf '%s\n' "$t08_blocks" | g3_awk -F'\t' '$1 > m { m = $1 } END { print m + 0 }')
t08_blk_bad=""
[ "$t08_nblocks" = "3" ] || t08_blk_bad="$t08_blk_bad 编号块数=$t08_nblocks(期望3)"
t08_bi=0
for pair in "B1|$C_T08_B1_HEAD|$C_T08_B1_SUPPLY|KnowledgeDataPack" \
            "B2|$C_T08_B2_HEAD|$C_T08_B2_SUPPLY|KnowledgeDataPack,RuleIndexPack" \
            "B3|$C_T08_B3_HEAD|$C_T08_B3_SUPPLY|EvidenceMapPack"; do
  t08_bi=$((t08_bi+1))
  rest="${pair#*|}"; lbl="${pair%%|*}"
  expect_pkgs="${rest##*|}"; rest="${rest%|*}"
  want_supply="${rest#*|}"; want_head="${rest%%|*}"
  blk=$(t08_block_lines "$t08_bi")
  got_head=$(printf '%s\n' "$blk" | head -1)
  if [ "$(g3norm "$got_head")" = "$(g3norm "$want_head")" ]; then
    :
  else
    t08_blk_bad="$t08_blk_bad ${lbl}标题=[$got_head]"
  fi
  sup_n=$(printf '%s\n' "$blk" | g3_grep -cE '^[[:space:]]+- \*\*供给子包\*\*：')
  if [ "$sup_n" = "1" ]; then
    got_supply=$(printf '%s\n' "$blk" | g3_grep -E '^[[:space:]]+- \*\*供给子包\*\*：')
    if [ "$(g3norm "$got_supply")" = "$(g3norm "$want_supply")" ]; then
      got_pkgs=$(printf '%s\n' "$got_supply" | g3_packs)
      [ "$got_pkgs" = "$expect_pkgs" ] || t08_blk_bad="$t08_blk_bad ${lbl}包集合异常($got_pkgs)"
    else
      t08_blk_bad="$t08_blk_bad ${lbl}供给声明=[$got_supply]"
    fi
  else
    t08_blk_bad="$t08_blk_bad ${lbl}供给声明数=$sup_n(期望1)"
  fi
done
if [ -z "$t08_blk_bad" ]; then
  printf 'PASS  G3-T08-BLOCK  §16.3.1 三块标题与唯一供给声明精确相等\n'
else
  printf 'FAIL  G3-T08-BLOCK  §16.3.1 块结构不合规:%s\n' "$t08_blk_bad"; FAILED=$((FAILED+1))
fi

g3_exact G3-T08-PROSE "$sec1632" \
  P01 "$C_T08_P01" P02 "$C_T08_P02" P03 "$C_T08_P03" \
  P04 "$C_T08_P04" P05 "$C_T08_P05"

t08_tbl_err=$(printf '%s\n' "$sec1632" | g3_awk -F'|' '
  function nz(s){ gsub(/`/,"",s); gsub(/\*/,"",s); gsub(/[[:space:]]/,"",s); return s }
  BEGIN {
    want["omen_carrying"]="M4|KnowledgeDataPack"
    want["condition_affordance"]="M4|RuleIndexPack与KnowledgeDataPack"
    want["school_variance_display"]="M4/M6|KnowledgeDataPack"
    want["concept_id"]="M4|KnowledgeDataPack"
    want["是否改变当前判断"]="M4/M7/M6|KnowledgeDataPack（MarkContentBinding）"
  }
  /^\|/ {
    nm=nz($2); mod=nz($4); pk=nz($5)
    if (nm == "字段名") next
    if (nm ~ /^[-:]+$/) next
    rows++
    cnt[nm]++
    got[nm]=mod "|" pk
    if (mod ~ /M5/) m5=m5 " [" nm "]"
    if (!(nm in want)) extra=extra " [" nm "]"
  }
  END {
    e=""
    if (rows != 5) e=e " 数据行=" rows "(期望5)"
    for (x in want) {
      if (cnt[x] != 1) e=e " " x "(x" cnt[x] ")"
      else if (got[x] != want[x]) e=e " " x "=[" got[x] "]期望=[" want[x] "]"
    }
    if (m5 != "") e=e " 生产列含M5:" m5
    if (extra != "") e=e " 未知字段:" extra
    print (e == "" ? "OK" : e)
  }
')
t08_row_bad=""
t08_lbls=(R01 R02 R03 R04 R05)
t08_rows=("$C_T08_R01" "$C_T08_R02" "$C_T08_R03" "$C_T08_R04" "$C_T08_R05")
for i in 0 1 2 3 4; do
  n=$(g3cnt "$(g3norm "${t08_rows[$i]}")" "$(printf '%s\n' "$sec1632" | g3n)")
  [ "$n" = "1" ] || t08_row_bad="$t08_row_bad ${t08_lbls[$i]}(x$n)"
done
if [ "$t08_tbl_err" = "OK" ] && [ -z "$t08_row_bad" ]; then
  printf 'PASS  G3-T08-TABLE  §16.3.2 五字段行完整、owner/package 精确、无 M5 生产者\n'
else
  printf 'FAIL  G3-T08-TABLE  §16.3.2 字段表不合规:%s%s\n' "$t08_tbl_err" "$t08_row_bad"; FAILED=$((FAILED+1))
fi

t08_s1_line=$(printf '%s\n' "$sec01" | g3_grep -F '最小盘面概念字典' | head -1)
t08_b1_limit=$(printf '%s\n' "$sec1631" | g3_grep -F '硬限制约束' | head -1)
t08_dsl_bad=""
printf '%s\n' "$t08_s1_line"   | g3n | g3_grep -Fq '不含规则DSL' || t08_dsl_bad="$t08_dsl_bad §1"
printf '%s\n' "$t08_b1_limit" | g3n | g3_grep -Fq '不含规则DSL' || t08_dsl_bad="$t08_dsl_bad §16.3.1"
if [ -z "$t08_dsl_bad" ]; then
  printf 'PASS  G3-T08-DSL  最小盘面概念字典在两处均声明不含规则 DSL\n'
else
  printf 'FAIL  G3-T08-DSL  「不含规则 DSL」缺失于:%s\n' "$t08_dsl_bad"; FAILED=$((FAILED+1))
fi

t08_g4_bad=""
printf '%s\n' "$t08_s1_line"   | g3n | g3_grep -Fq 'TAG_SYSTEM_DESIGN.md§12.2' || t08_g4_bad="$t08_g4_bad §1"
printf '%s\n' "$t08_b1_limit" | g3n | g3_grep -Fq 'TAG_SYSTEM_DESIGN.md§12.2' || t08_g4_bad="$t08_g4_bad §16.3.1"
if [ -z "$t08_g4_bad" ]; then
  printf 'PASS  G3-T08-G4  Tag 侧 G4 在两处均以 TAG_SYSTEM_DESIGN.md §12.2 命名空间化\n'
else
  printf 'FAIL  G3-T08-G4  「TAG_SYSTEM_DESIGN.md §12.2」缺失于:%s\n' "$t08_g4_bad"; FAILED=$((FAILED+1))
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
