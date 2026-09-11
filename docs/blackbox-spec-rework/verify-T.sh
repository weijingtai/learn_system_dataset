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

# G3 R4 精确结构门禁：D-07 / T-07 / T-08（封闭结构版）
# ---------------------------------------------------------------------
# 本段所有 sed / grep / awk 一律通过 g3_sed / g3_grep / g3_awk 包一层 LC_ALL=C。
# 原因：macOS BSD awk 在 en_US.UTF-8 下会把两个无关的中文串判为相等
# （实测 "是否改变当前判断" == "字段名" 返回真），sed/grep 的多字节类也不确定。
# 注意：不能全局 export LC_ALL=C —— 脚本其他段落（T-06s、T-08s 历史判据）依赖
# en_US.UTF-8 下的多字节括号表达式与 `[^由]` 这类字符类，全局切换会让它们误报。
g3_sed()  { LC_ALL=C sed "$@"; }
g3_grep() { LC_ALL=C grep "$@"; }
g3_awk()  { LC_ALL=C awk "$@"; }

# 冻结规范化：只删除 5 种字节 —— 反引号(96)、星号(42)、普通空格(32)、Tab(9)、CR(13)。
# 用 tr 按八进制逐字节删除，因此 form-feed(12)、vertical-tab(11)、其他 Unicode 空白、
# 中英文标点、数字、斜杠、否定词与标识符全部原样保留。绝不使用 [[:space:]] 宽泛删除。
g3n() { LC_ALL=C tr -d '\011\015\040\052\140'; }
g3norm() { printf '%s\n' "$1" | g3n; }
g3cnt() { printf '%s\n' "$2" | g3_grep -Fxc -- "$1"; }   # $1 已规范化规范行, $2 已规范化段落

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

# Package 标识多重集：保留重复次数（禁止 sort -u 抹掉重复）。
g3_packs() { g3_grep -oE '[A-Za-z][A-Za-z0-9]*Pack' | LC_ALL=C sort \
  | g3_awk 'BEGIN{ORS=""} {print (NR>1?",":"") $0}'; }

# 把若干行拼成一个带换行结尾的字符串（供与 $() 提取结果做整体相等比较）
g3_join_items() { local out="" l; for l in "$@"; do out="$out$l"$'\n'; done; printf '%s' "$out"; }
g3_nlines() { printf '%s\n' "$1" | g3_grep -c .; }

# ---- 权威规范行（照抄自 work-items/g3-r3/CANONICAL.md 与权威正文，硬编码） ----
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

C_T07_HEAD='### 16.2 KnowledgePack 与 PublicationPackage 双向映射表'
C_T07_REPLACEMENT='黑箱架构规格以多子包组合的 `PublicationPackage`（特别是其中的结构化知识主体 `KnowledgeDataPack`）正式取代早期草案中单一扁平的 `KnowledgePack` 概念。'
C_T07_EXPLAIN='为消除历史协作歧义，早期草案（`LEARN_SYSTEM_TARGET.md §9`）建议的 KnowledgePack 目录项与现行黑箱架构子包及规约的双向对应关系如下：'
# §16.2 映射表的表头行与分隔行（逐字硬编码，用于表格 17 行完整封闭）
C_T07_TBL_HEAD='| 早期 KnowledgePack 目录建议 (`TARGET.md §9`) | 现行黑箱架构落点 (`PublicationPackage` 子包 / 规约) |'
C_T07_TBL_SEP='|---|---|'
# §16.2 映射表的 15 个 canonical 数据行（逐字抄自 work-items/g3-r3/mutations.sh）
C_T07_M01='| `release-manifest` | `ReleaseManifest`（发布清单与元数据摘要） |'
C_T07_M02='| `schema` | `KnowledgeDataPack`（及 Contract Registry 对应模式定义） |'
C_T07_M03='| `concepts` | `KnowledgeDataPack`（概念定义及术语体系） |'
C_T07_M04='| `entries` | `KnowledgeDataPack`（知识条目 KnowledgeEntry 集合） |'
C_T07_M05='| `assertions` | `KnowledgeDataPack`（结构化主张 Assertion 集合） |'
C_T07_M06='| `applicability-rules` | `RuleIndexPack`（与 `KnowledgeDataPack` 中的适用规则） |'
C_T07_M07='| `school-views` | `KnowledgeDataPack`（各流派分歧与立场视图） |'
C_T07_M08='| `evidence-links` | `EvidenceMapPack`（证据链接与跨层关联） |'
C_T07_M09='| `source-spans` | `EvidenceMapPack`（与 `KnowledgeDataPack` 中的原文片段引用） |'
C_T07_M10='| `source-anchors` | `EvidenceMapPack`（底本物理位置证据锚点，必须随包发布） |'
C_T07_M11='| `scan-assets-or-references` | `SourceAssetPack`（扫描图或受控引用） |'
C_T07_M12='| `exact-search-index` | `SearchIndexPack`（精确检索索引） |'
C_T07_M13='| `fulltext-index` | `SearchIndexPack`（全文检索索引） |'
C_T07_M14='| `optional-vector-index` | 本期不产出（依据 §21 非目标） |'
C_T07_M15='| `query-contract` | `QueryContractPack`（查询契约与接口定义） |'

C_T08_S1_01='1. `最小盘面概念字典`：规模约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅包含稳定 `concept_id` + 名称 + 基础类象，**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题；'
C_T08_S1_02='2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，为 UI 标记提供内容与分歧数据；'
C_T08_S1_03='3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为解盘与证据高亮提供底层的无损证据链切片。'
C_T08_S1631_HEAD='#### 16.3.1 三个耦合接口规范与供给子包'
C_T08_B1_HEAD='1. **`最小盘面概念字典`**：'
C_T08_B1_SUPPLY='   - **供给子包**：由 `KnowledgeDataPack` 供给；'
C_T08_B1_SCOPE='   - **规模与范围**：规模控制在约 100–200 个概念（覆盖十天干、十二地支、九星、八门、八神等盘面基础元素），仅包含稳定 ID（`concept_id`）、名称与基础类象；'
C_T08_B1_LIMIT='   - **硬限制约束**：**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题。规则 DSL 属于后续阶段的 RuntimeFeature 范围，不在最小概念字典中承载。'
C_T08_B2_HEAD='2. **`MarkContentBinding` 内容供给**：'
C_T08_B2_SUPPLY='   - **供给子包**：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给；'
C_T08_B2_NOTE='   - **承接说明**：为 UI 标记提供内容与分歧数据，包括吉凶定性、条件槽位可供性与流派分歧展示。'
C_T08_B3_HEAD='3. **`EvidenceBundle` 服务**：'
C_T08_B3_SUPPLY='   - **供给子包**：由 `EvidenceMapPack` 供给；'
C_T08_B3_NOTE='   - **承接说明**：为 AI 解盘与端侧证据高亮提供底层的无损证据链切片，确保标记内容能溯源至底本原页与字框坐标。'
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
sec162raw=$(g3_sed -n '/^### 16\.2 /,/^### 16\.3 /p' "$SPEC")
sec01=$(g3_sed -n '/^## 1\.[[:space:]]/,/^## 2\.[[:space:]]/p' "$SPEC")
sec1631=$(g3_sed -n '/^#### 16\.3\.1 /,/^#### 16\.3\.2 /p' "$SPEC")
sec1632=$(g3_sed -n '/^#### 16\.3\.2 /,/^## 17/p' "$SPEC")
sec13=$(g3_sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")
# §16.2 切片去掉收尾的下一节标题，使非表格声明区成为真正封闭的区域
sec162=$(printf '%s\n' "$sec162raw" | g3_awk 'index($0, "### 16.3 ") == 1 { exit } { print }')
sec16n=$(printf '%s\n' "$sec16" | g3n)
sec162n=$(printf '%s\n' "$sec162" | g3n)
sec1631n=$(printf '%s\n' "$sec1631" | g3n)

# ============ D-07：三个封闭契约区域 ============
# 区域定义（不再是「遇非列表行即停」的块，而是到下一个固定边界为止的整段）：
#   TP 区域 = TP START 行 .. QC START 行之前；QC 区域 = QC START 行 .. RI START 行之前；
#   RI 区域 = RI START 行 .. `### 16.2` 标题行之前。
# 区域内跳过空行后，剩余行序列必须逐字等于「START 行 + 固定有序条目」。
# 这样，区域内任何位置（含块尾隔空行处）追加的多余行都会使序列不等而 FAIL。
g3_d07_region() { # <规范化§16> <规范化START行> <规范化END行>
  printf '%s\n' "$1" | S="$2" E="$3" g3_awk '
    st == 1 && $0 == ENVIRON["E"] { exit }
    $0 == ENVIRON["S"] { st = 1; print; next }
    st == 1 { if ($0 == "") next; print }'
}

d07_tp_n=$(g3cnt "$(g3norm "$C_D07_TP_START")" "$sec16n")
d07_qc_n=$(g3cnt "$(g3norm "$C_D07_QC_START")" "$sec16n")
d07_ri_n=$(g3cnt "$(g3norm "$C_D07_RI_START")" "$sec16n")
d07_tp_got=$(g3_d07_region "$sec16n" "$(g3norm "$C_D07_TP_START")" "$(g3norm "$C_D07_QC_START")")
d07_qc_got=$(g3_d07_region "$sec16n" "$(g3norm "$C_D07_QC_START")" "$(g3norm "$C_D07_RI_START")")
d07_ri_got=$(g3_d07_region "$sec16n" "$(g3norm "$C_D07_RI_START")" "$(g3norm "$C_T07_HEAD")")
D07_TP_WANT=$(g3_join_items "$(g3norm "$C_D07_TP_START")" \
                            "$(g3norm "$C_D07_TP_PROFILE")" "$(g3norm "$C_D07_TP_FIELDS")" \
                            "$(g3norm "$C_D07_TP_OPERATORS")" "$(g3norm "$C_D07_TP_AST")")
D07_QC_WANT=$(g3_join_items "$(g3norm "$C_D07_QC_START")" \
                            "$(g3norm "$C_D07_QC_ENTRY")" "$(g3norm "$C_D07_QC_SPAN")" \
                            "$(g3norm "$C_D07_QC_SEARCH")" "$(g3norm "$C_D07_QC_MATCH")" \
                            "$(g3norm "$C_D07_QC_COMPAT")")
D07_RI_WANT=$(g3_join_items "$(g3norm "$C_D07_RI_START")" \
                            "$(g3norm "$C_D07_RI_VERSION")" "$(g3norm "$C_D07_RI_DECLARATIVE")")

if [ "$d07_tp_n" = "1" ] && [ "$d07_tp_got" = "$D07_TP_WANT" ]; then
  printf 'PASS  G3-D07-TP  TechniqueProfilePack 封闭块 4 条列表项序列完全相等\n'
else
  printf 'FAIL  G3-D07-TP  TechniqueProfilePack 封闭块不等于规范序列(START x%s，区域非空行 %s/5)\n' \
    "$d07_tp_n" "$(g3_nlines "$d07_tp_got")"; FAILED=$((FAILED+1))
fi

# 四个查询接口只能来自 QC 区域去掉首行 START 之后的条目，不做全 §16 子串搜索
d07_qc_items=$(printf '%s\n' "$d07_qc_got" | g3_sed -n '2,$p')
d07_iface_bad=""
for d07_sig in 'getEntry(entry_id)' 'getSourceSpan(span_id)' 'searchKnowledge(query, filters)' 'matchFacts(fact_set)'; do
  printf '%s\n' "$d07_qc_items" | g3_grep -Fq -- "$(g3norm "$d07_sig")" \
    || d07_iface_bad="$d07_iface_bad ${d07_sig}"
done

if [ "$d07_qc_n" = "1" ] && [ "$d07_qc_got" = "$D07_QC_WANT" ] && [ -z "$d07_iface_bad" ]; then
  printf 'PASS  G3-D07-QC  QueryContractPack 封闭块 5 条列表项序列完全相等且恰四个查询接口\n'
else
  printf 'FAIL  G3-D07-QC  QueryContractPack 封闭块不等于规范序列(START x%s，区域非空行 %s/6，签名缺失:%s)\n' \
    "$d07_qc_n" "$(g3_nlines "$d07_qc_got")" "${d07_iface_bad:-无}"; FAILED=$((FAILED+1))
fi

d07_compat_n=$(g3cnt "$(g3norm "$C_D07_QC_COMPAT")" "$d07_qc_got")
if [ "$d07_compat_n" = "1" ]; then
  printf 'PASS  G3-D07-COMPAT  向后兼容声明在 QC 封闭块内恰一次且完整相等\n'
else
  printf 'FAIL  G3-D07-COMPAT  向后兼容声明在 QC 封闭块内出现 %s 次(期望 1)\n' "$d07_compat_n"; FAILED=$((FAILED+1))
fi

if [ "$d07_ri_n" = "1" ] && [ "$d07_ri_got" = "$D07_RI_WANT" ]; then
  printf 'PASS  G3-D07-RI  RuleIndexPack 封闭块 2 条列表项序列完全相等\n'
else
  printf 'FAIL  G3-D07-RI  RuleIndexPack 封闭块不等于规范序列(START x%s，区域非空行 %s/3)\n' \
    "$d07_ri_n" "$(g3_nlines "$d07_ri_got")"; FAILED=$((FAILED+1))
fi

if printf '%s\n' "$sec13" | g3_grep -Fq 'FactSet' \
  && printf '%s\n' "$sec13" | g3_grep -Fq '可执行性' \
  && printf '%s\n' "$sec13" | g3_grep -Fq 'G6' \
  && printf '%s\n' "$sec13" | g3_grep -Fq '不负责生产'; then
  printf 'PASS  D-07s M5 verifies FactSet executability under G6 and produces no contract\n'
else
  printf 'FAIL  D-07s M5 FactSet executability or non-producer boundary missing\n'; FAILED=$((FAILED+1))
fi

# ============ T-07：封闭映射表 + 封闭声明区 ============
t07_map_err=$(printf '%s\n' "$sec162" | g3_awk -F'|' '
  function nz(s){ gsub(/`/,"",s); gsub(/\*/,"",s); gsub(/ /,"",s); gsub(sprintf("%c",9),"",s); gsub(sprintf("%c",13),"",s); return s }
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

# §16.2 非表格声明区封闭：只允许 标题 / 取代声明 / 说明行 / 空行 / 表格行，
# 任何其他声明行（含追加的相反声明）都使该区不封闭。
t07_decl_err=$(printf '%s\n' "$sec162n" \
  | H="$(g3norm "$C_T07_HEAD")" R="$(g3norm "$C_T07_REPLACEMENT")" E="$(g3norm "$C_T07_EXPLAIN")" g3_awk '
    { if ($0 == "") { blank++; next }
      if ($0 == ENVIRON["H"]) { h++; next }
      if ($0 == ENVIRON["R"]) { r++; next }
      if ($0 == ENVIRON["E"]) { e++; next }
      if (substr($0, 1, 1) == "|") { tbl++; next }
      other++; oth = oth " [" $0 "]" }
    END { m = ""
      if (h != 1) m = m " 标题(x" h ")"
      if (r != 1) m = m " 取代声明(x" r ")"
      if (e != 1) m = m " 说明行(x" e ")"
      if (other != 0) m = m " 封闭区外声明行" other "条:" oth
      print (m == "" ? "OK" : m) }')

# §16.2 表格整体 17 行封闭：表头 1 行 + 分隔 1 行 + 15 个数据行；
# 每个数据行必须逐字等于 15 个 canonical 之一（且每个 canonical 恰出现一次），
# 且每行 `|` 字节数恰为 3（两列）。任何行尾追加的第三列都会破坏这两项。
t07_tbl_lines=$(printf '%s\n' "$sec162n" | g3_awk 'substr($0, 1, 1) == "|" { print }')
t07_tbl_n=$(g3_nlines "$t07_tbl_lines")
t07_tbl_msg=""
[ "$t07_tbl_n" = "17" ] || t07_tbl_msg="$t07_tbl_msg 表格行数=$t07_tbl_n(期望17)"
t07_tbl_l1=$(printf '%s\n' "$t07_tbl_lines" | g3_sed -n '1p')
t07_tbl_l2=$(printf '%s\n' "$t07_tbl_lines" | g3_sed -n '2p')
[ "$t07_tbl_l1" = "$(g3norm "$C_T07_TBL_HEAD")" ] || t07_tbl_msg="$t07_tbl_msg 表头行=[$t07_tbl_l1]"
[ "$t07_tbl_l2" = "$(g3norm "$C_T07_TBL_SEP")" ] || t07_tbl_msg="$t07_tbl_msg 分隔行=[$t07_tbl_l2]"

T07_ROWS_WANT=$(g3_join_items \
  "$(g3norm "$C_T07_M01")" "$(g3norm "$C_T07_M02")" "$(g3norm "$C_T07_M03")" \
  "$(g3norm "$C_T07_M04")" "$(g3norm "$C_T07_M05")" "$(g3norm "$C_T07_M06")" \
  "$(g3norm "$C_T07_M07")" "$(g3norm "$C_T07_M08")" "$(g3norm "$C_T07_M09")" \
  "$(g3norm "$C_T07_M10")" "$(g3norm "$C_T07_M11")" "$(g3norm "$C_T07_M12")" \
  "$(g3norm "$C_T07_M13")" "$(g3norm "$C_T07_M14")" "$(g3norm "$C_T07_M15")")
t07_m_lbls=(M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11 M12 M13 M14 M15)
t07_m_rows=("$C_T07_M01" "$C_T07_M02" "$C_T07_M03" "$C_T07_M04" "$C_T07_M05" \
            "$C_T07_M06" "$C_T07_M07" "$C_T07_M08" "$C_T07_M09" "$C_T07_M10" \
            "$C_T07_M11" "$C_T07_M12" "$C_T07_M13" "$C_T07_M14" "$C_T07_M15")
for i in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14; do
  t07_mn=$(g3cnt "$(g3norm "${t07_m_rows[$i]}")" "$t07_tbl_lines")
  [ "$t07_mn" = "1" ] || t07_tbl_msg="$t07_tbl_msg ${t07_m_lbls[$i]}(x$t07_mn)"
done

# 第 3–17 行逐行校验：`|` 字节数恰 3，且整行属于 15 个 canonical 之一
while IFS= read -r t07_row; do
  [ -n "$t07_row" ] || continue
  t07_pipe_n=$(printf '%s\n' "$t07_row" | g3_awk '{ print gsub(/[|]/, "&") }')
  [ "$t07_pipe_n" = "3" ] || t07_tbl_msg="$t07_tbl_msg 竖线数=$t07_pipe_n[$t07_row]"
  t07_mem_n=$(g3cnt "$t07_row" "$T07_ROWS_WANT")
  [ "$t07_mem_n" = "1" ] || t07_tbl_msg="$t07_tbl_msg 非规范数据行[$t07_row]"
done <<< "$(printf '%s\n' "$t07_tbl_lines" | g3_sed -n '3,$p')"

t07_tbl_err="OK"
[ -z "$t07_tbl_msg" ] || t07_tbl_err="$t07_tbl_msg"

if [ "$t07_map_err" = "OK" ] && [ "$t07_decl_err" = "OK" ] && [ "$t07_tbl_err" = "OK" ]; then
  printf 'PASS  G3-T07-MAP  §16.2 映射表 15 项唯一且声明区封闭\n'
else
  printf 'FAIL  G3-T07-MAP  §16.2 不合规[表:%s][声明区:%s][表行:%s]\n' \
    "$t07_map_err" "$t07_decl_err" "$t07_tbl_err"; FAILED=$((FAILED+1))
fi

if [ "$t07_decl_err" = "OK" ]; then
  printf 'PASS  G3-T07-REPLACEMENT  §16.2 取代声明完整句唯一且声明区封闭\n'
else
  printf 'FAIL  G3-T07-REPLACEMENT  §16.2 取代声明区不封闭:%s\n' "$t07_decl_err"; FAILED=$((FAILED+1))
fi

# ============ T-08：§1 封闭接口集合 ============
# 收集 §1 中所有包含三个保留接口名之一的行（按出现顺序），必须恰为规范的三行。
t08_s1_got=$(printf '%s\n' "$sec01" | g3_awk '
  { n = $0
    gsub(/`/, "", n); gsub(/\*/, "", n); gsub(/ /, "", n)
    gsub(sprintf("%c", 9), "", n); gsub(sprintf("%c", 13), "", n)
    if (index(n, "最小盘面概念字典") > 0 || index(n, "MarkContentBinding") > 0 \
        || index(n, "EvidenceBundle") > 0) print n }')
T08_S1_WANT=$(g3_join_items "$(g3norm "$C_T08_S1_01")" "$(g3norm "$C_T08_S1_02")" "$(g3norm "$C_T08_S1_03")")
t08_s1_n=$(g3_nlines "$t08_s1_got")
t08_s1_l1=$(printf '%s\n' "$t08_s1_got" | g3_sed -n '1p')
t08_s1_l2=$(printf '%s\n' "$t08_s1_got" | g3_sed -n '2p')
t08_s1_l3=$(printf '%s\n' "$t08_s1_got" | g3_sed -n '3p')

t08_s1_dup=""
for t08_nm in '最小盘面概念字典' 'MarkContentBinding' 'EvidenceBundle'; do
  t08_c=$(printf '%s\n' "$t08_s1_got" | g3_grep -F -c -- "$t08_nm")
  [ "$t08_c" = "1" ] || t08_s1_dup="$t08_s1_dup ${t08_nm}(x${t08_c})"
done
# Package 多重集从**实际规格行**提取，与期望多重集比较（保留重复次数）
t08_s1_p1=$(printf '%s\n' "$t08_s1_l1" | g3_packs)
t08_s1_p2=$(printf '%s\n' "$t08_s1_l2" | g3_packs)
t08_s1_p3=$(printf '%s\n' "$t08_s1_l3" | g3_packs)

t08_sec1_bad=""
[ "$t08_s1_n" = "3" ] || t08_sec1_bad="$t08_sec1_bad 接口行数=$t08_s1_n(期望3)"
[ "$t08_s1_got" = "$T08_S1_WANT" ] || t08_sec1_bad="$t08_sec1_bad 行内容不等于规范序列"
[ -z "$t08_s1_dup" ] || t08_sec1_bad="$t08_sec1_bad 接口名重复:$t08_s1_dup"
[ "$t08_s1_p1" = "KnowledgeDataPack" ] || t08_sec1_bad="$t08_sec1_bad 实际包多重集1[$t08_s1_p1]"
[ "$t08_s1_p2" = "KnowledgeDataPack,RuleIndexPack" ] || t08_sec1_bad="$t08_sec1_bad 实际包多重集2[$t08_s1_p2]"
[ "$t08_s1_p3" = "EvidenceMapPack" ] || t08_sec1_bad="$t08_sec1_bad 实际包多重集3[$t08_s1_p3]"
if [ -z "$t08_sec1_bad" ]; then
  printf 'PASS  G3-T08-SEC1  §1 接口集合封闭为三行且包多重集精确\n'
else
  printf 'FAIL  G3-T08-SEC1  §1 接口集合不封闭:%s\n' "$t08_sec1_bad"; FAILED=$((FAILED+1))
fi

# ============ T-08：§16.3.1 三个完整封闭块 ============
# 边界：下一个同级编号标题或 #### 16.3.2。块内每个非空行都必须是规范列表项。
g3_t08_block() { # <规范化§16.3.1> <规范化HEAD行>
  # 规范化删除了星号，因此编号标题在规范化文本中形如 "1.最小盘面概念字典："
  # （列表项则以 "-" 开头），同级标题边界即 ^[1-3]\.
  printf '%s\n' "$1" | H="$2" g3_awk '
    $0 == ENVIRON["H"] { inb = 1; next }
    inb == 1 {
      if (index($0, "####16.3.2") == 1) { inb = 0; next }
      if ($0 ~ /^[1-3]\./) { inb = 0; next }
      if ($0 == "") next
      print
    }'
}
t08_b1_blk=$(g3_t08_block "$sec1631n" "$(g3norm "$C_T08_B1_HEAD")")
t08_b2_blk=$(g3_t08_block "$sec1631n" "$(g3norm "$C_T08_B2_HEAD")")
t08_b3_blk=$(g3_t08_block "$sec1631n" "$(g3norm "$C_T08_B3_HEAD")")
T08_B1_WANT=$(g3_join_items "$(g3norm "$C_T08_B1_SUPPLY")" "$(g3norm "$C_T08_B1_SCOPE")" "$(g3norm "$C_T08_B1_LIMIT")")
T08_B2_WANT=$(g3_join_items "$(g3norm "$C_T08_B2_SUPPLY")" "$(g3norm "$C_T08_B2_NOTE")")
T08_B3_WANT=$(g3_join_items "$(g3norm "$C_T08_B3_SUPPLY")" "$(g3norm "$C_T08_B3_NOTE")")
t08_b1_pk=$(printf '%s\n' "$t08_b1_blk" | g3_packs)
t08_b2_pk=$(printf '%s\n' "$t08_b2_blk" | g3_packs)
t08_b3_pk=$(printf '%s\n' "$t08_b3_blk" | g3_packs)

# §16.3.1 整区域封闭：从 `#### 16.3.1` 标题行到 `#### 16.3.2` 之前，去掉空行后的
# 规范化行序列必须逐字等于 11 行（标题 + B1 标题与 3 条目 + B2 标题与 2 条目 + B3 标题与 2 条目）。
# 三个块标题在区域内必须各恰出现一次。块尾重复标题与块外正文因此都会 FAIL。
t08_s1631_seq=$(printf '%s\n' "$sec1631n" | g3_awk '
  index($0, "####16.3.2") == 1 { exit }
  $0 == "" { next }
  { print }')
T08_S1631_WANT=$(g3_join_items "$(g3norm "$C_T08_S1631_HEAD")" \
  "$(g3norm "$C_T08_B1_HEAD")" "$(g3norm "$C_T08_B1_SUPPLY")" \
  "$(g3norm "$C_T08_B1_SCOPE")" "$(g3norm "$C_T08_B1_LIMIT")" \
  "$(g3norm "$C_T08_B2_HEAD")" "$(g3norm "$C_T08_B2_SUPPLY")" "$(g3norm "$C_T08_B2_NOTE")" \
  "$(g3norm "$C_T08_B3_HEAD")" "$(g3norm "$C_T08_B3_SUPPLY")" "$(g3norm "$C_T08_B3_NOTE")")
t08_s1631_n=$(g3_nlines "$t08_s1631_seq")
t08_h1_n=$(g3cnt "$(g3norm "$C_T08_B1_HEAD")" "$sec1631n")
t08_h2_n=$(g3cnt "$(g3norm "$C_T08_B2_HEAD")" "$sec1631n")
t08_h3_n=$(g3cnt "$(g3norm "$C_T08_B3_HEAD")" "$sec1631n")

t08_blk_bad=""
[ "$t08_s1631_seq" = "$T08_S1631_WANT" ] || t08_blk_bad="$t08_blk_bad §16.3.1区域序列不等于规范"
if [ "$t08_h1_n" = "1" ] && [ "$t08_h2_n" = "1" ] && [ "$t08_h3_n" = "1" ]; then
  :
else
  t08_blk_bad="$t08_blk_bad 块标题非唯一"
fi
if [ "$t08_b1_blk" = "$T08_B1_WANT" ] && [ "$t08_b1_pk" = "KnowledgeDataPack" ]; then
  :
else
  t08_blk_bad="$t08_blk_bad B1条目$(g3_nlines "$t08_b1_blk")/3 包多重集[$t08_b1_pk]"
fi
if [ "$t08_b2_blk" = "$T08_B2_WANT" ] && [ "$t08_b2_pk" = "KnowledgeDataPack,RuleIndexPack" ]; then
  :
else
  t08_blk_bad="$t08_blk_bad B2条目$(g3_nlines "$t08_b2_blk")/2 包多重集[$t08_b2_pk]"
fi
if [ "$t08_b3_blk" = "$T08_B3_WANT" ] && [ "$t08_b3_pk" = "EvidenceMapPack" ]; then
  :
else
  t08_blk_bad="$t08_blk_bad B3条目$(g3_nlines "$t08_b3_blk")/2 包多重集[$t08_b3_pk]"
fi
if [ -z "$t08_blk_bad" ]; then
  printf 'PASS  G3-T08-BLOCK  §16.3.1 三块条目序列封闭且包多重集精确\n'
else
  printf 'FAIL  G3-T08-BLOCK  §16.3.1 块结构不封闭:%s 区域行数=%s(期望11) 标题计数 B1x%s B2x%s B3x%s\n' \
    "$t08_blk_bad" "$t08_s1631_n" "$t08_h1_n" "$t08_h2_n" "$t08_h3_n"; FAILED=$((FAILED+1))
fi

g3_exact G3-T08-PROSE "$sec1632" \
  P01 "$C_T08_P01" P02 "$C_T08_P02" P03 "$C_T08_P03" \
  P04 "$C_T08_P04" P05 "$C_T08_P05"

t08_tbl_err=$(printf '%s\n' "$sec1632" | g3_awk -F'|' '
  function nz(s){ gsub(/`/,"",s); gsub(/\*/,"",s); gsub(/ /,"",s); gsub(sprintf("%c",9),"",s); gsub(sprintf("%c",13),"",s); return s }
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

# ============ T-08：DSL 与 G4 用完整行校验（两处各自独立） ============
# §1 的最小盘面概念字典行必须完整等于 canonical；§16.3.1 的 B1 块内含 DSL / G4
# 引用的行必须恰为规范的「硬限制约束」行，不得再追加任何例外或冲突声明。
t08_dsl_bad=""
t08_g4_bad=""
[ "$t08_s1_l1" = "$(g3norm "$C_T08_S1_01")" ] || { t08_dsl_bad="$t08_dsl_bad §1完整行"; t08_g4_bad="$t08_g4_bad §1完整行"; }
t08_b1_dsl=$(printf '%s\n' "$t08_b1_blk" | g3_grep -F 'DSL')
t08_b1_g4=$(printf '%s\n' "$t08_b1_blk" | g3_grep -F 'TAG_SYSTEM_DESIGN.md')
[ "$t08_b1_dsl" = "$(g3norm "$C_T08_B1_LIMIT")" ] || t08_dsl_bad="$t08_dsl_bad §16.3.1硬限制约束区"
[ "$t08_b1_g4" = "$(g3norm "$C_T08_B1_LIMIT")" ] || t08_g4_bad="$t08_g4_bad §16.3.1硬限制约束区"
if [ -z "$t08_dsl_bad" ]; then
  printf 'PASS  G3-T08-DSL  最小盘面概念字典两处完整行均封闭声明不含规则 DSL\n'
else
  printf 'FAIL  G3-T08-DSL  「不含规则 DSL」完整行校验失败于:%s\n' "$t08_dsl_bad"; FAILED=$((FAILED+1))
fi
if [ -z "$t08_g4_bad" ]; then
  printf 'PASS  G3-T08-G4  Tag 侧 G4 两处完整行均以 TAG_SYSTEM_DESIGN.md §12.2 命名空间化\n'
else
  printf 'FAIL  G3-T08-G4  「TAG_SYSTEM_DESIGN.md §12.2」完整行校验失败于:%s\n' "$t08_g4_bad"; FAILED=$((FAILED+1))
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
