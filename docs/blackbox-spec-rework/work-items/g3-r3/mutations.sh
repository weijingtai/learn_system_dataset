#!/usr/bin/env bash
# ============================================================================
# G3 R3 永久变异测试入口（mutation-test harness）
#
# 对权威规格 openspec/learn-system-blackbox-architecture.md 逐例施加
# CASES.md 定义的机械变异，再以 SPEC=<变异副本> 调用
# docs/blackbox-spec-rework/verify-T.sh。
#
# 判定：门禁退出码非零 **且** 该例绑定的全部稳定 FAIL ID 都出现在 ^FAIL 行中，
#       该例才算 rejected。否则记为 not-rejected。
#
# 用法：
#   bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh d07       # 34 例
#   bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t07       # 28 例
#   bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t08       # 47 例
#   bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all       # 109 例
#   bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh selftest  # 自检
#
# 约束：
#   * 仅使用 bash + POSIX 工具（awk/sed/grep/mktemp/cp/rm/wc），无第三方依赖。
#   * 每例都从权威规格复制**全新**的私有临时副本；绝不修改仓库内规格；
#     绝不跨用例叠加变异。
#   * 所有 expected / canonical 值硬编码在本脚本内，绝不从 $SPEC 动态推导，
#     否则测试会与错误输入一起漂移。
#   * 整行比较用 awk 的 ENVIRON 传参（`awk -v` 会吞掉反斜杠转义），并强制
#     LC_ALL=C 逐字节比较：macOS 的 en_US.UTF-8 locale 下 awk 的 `==`
#     多字节字符串比较不可靠（会把不同行判成相等）。
# ============================================================================
set -u

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)" || exit 99
GATE="$ROOT/docs/blackbox-spec-rework/verify-T.sh"
SPEC_SRC="$ROOT/openspec/learn-system-blackbox-architecture.md"
cd "$ROOT" || exit 99

# ============================ 硬编码常量 ============================
# 以下常量逐字节照抄 CANONICAL.md 中形如 `[LABEL] <原文>` 的行（去掉 `[LABEL] `
# 方括号标签前缀）；T-07 的 §16.2 表格行按 key 照抄权威规格正文。
# 严禁从 $SPEC（待测变异副本）动态推导任何 expected 值。
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
C_T08_R04_M2='| `concept_id` | 概念标识：全局稳定的概念 ID | M2 | `KnowledgeDataPack` | 术语判层产出的稳定概念 ID，盘面语义物种必须绑定 |'

# ---- CASES.md 给出的替换行 / 追加行 / 右值（同样硬编码，禁止推导） ----
# d07-02：把 D07-TP-FIELDS 整行替换为该行
L_D07_02='- **事实字段与枚举**：包中不列任何事实字段与枚举；字段由客户端自由猜测；'
# t08-18 / t08-19：原供给行之后追加的整行（三段空格缩进）
L_APPEND_SUPPLY_SOURCE='   - **供给子包**：由 `SourceAssetPack` 供给；'
# t08-20：原供给行之后追加的整行
L_APPEND_SUPPLY_SEARCH='   - **供给子包**：由 `SearchIndexPack` 供给；'
# §16.2 错误右值
V_WRONG_PACK='WrongPack'
V_SOURCE_ASSET_PACK='SourceAssetPack'
V_SEARCH_INDEX_PACK='SearchIndexPack'
# t07-16 / t07-17：以「当前完整 RHS + X」作为 value（RHS cell 本体硬编码）
C_T07_M15_CELL='`QueryContractPack`（查询契约与接口定义）'
C_T07_M14_CELL='本期不产出（依据 §21 非目标）'
V_T07_16="${C_T07_M15_CELL}EvidenceMapPack"
V_T07_17="${C_T07_M14_CELL}SearchIndexPack"
# §16.3.2 module 列替换值
V_MODULE_M2='M2'
V_MODULE_M4_M5='M4 / M5'

# ---- R4 加固新增案例所需的常量（同样硬编码，禁止推导） ----
# 控制字符：form-feed (0x0C) 与 vertical-tab (0x0B)。冻结规范化规则**不得**删除它们，
# 因此把它们插进 Package 名必须让「完整行精确相等」失败。
CH_FF="$(printf '\f')"
CH_VT="$(printf '\v')"
V_TP_FF="TechniqueProfile${CH_FF}Pack"
V_TP_VT="TechniqueProfile${CH_VT}Pack"
# d07-27：向 TP 块追加的冲突列表项
L_D07_27='- **自由字段说明**：客户端可以使用自由字段，不受闭集枚举约束；'
# d07-28：向 QC 块追加的第五个查询接口
L_D07_28='- **`getEntry(name)`**：按名称获取条目，作为第五个查询接口；'
# t07-26：保留正确取代声明后再追加的相反声明
L_T07_26='但早期单一 KnowledgePack 仍是正式发布结构，以上取代声明不生效。'
# t08-40：§1 正确 MarkContentBinding 行之后追加的同名错误接口
L_T08_40='4. `MarkContentBinding` 内容供给：由 `SourceAssetPack` 供给，为 UI 标记提供内容与分歧数据；'
# t08-41：B3 正确供给行之后追加的非标准标签额外 Package 来源
L_T08_41='   - **附加来源**：由 `SearchIndexPack` 供给；'
# t08-42：B1 正确硬限制行之后追加的例外声明
L_T08_42='   - **例外**：最小盘面概念字典允许直接包含规则 DSL。'

# ---- R5 区域边界封闭新增案例所需的常量（逐字照抄 g3-r5/TDD.md §1.1，禁止推导） ----
# d07-32 / d07-33 / d07-34：三个封闭块之后隔空行追加的冲突段落（非列表行）
L_D07_32='客户端仍可绕过 TechniqueProfilePack，使用任意自由字段参与确定性匹配。'
L_D07_33='客户端可以绕过 QueryContractPack 直接读取底层文件。'
L_D07_34='RuleIndexPack 中的规则允许附带 Python 代码块。'
# t07-27 / t07-28：§16.2 正确数据行行尾追加的第三列
V_T07_EXTRA_COL=' 冲突附加值 |'
# t08-45：§16.3.1 标题与 B1 标题之间插入的块外正文
L_T08_45='以上三个接口之外，Tag 系统还可以直接读取 `SourceAssetPack`。'
# §16.3.1 标题与 B1/B2/B3 的其余条目（照抄 verify-T.sh 既有常量与规格第 734 行）
C_T08_S1631_HEAD='#### 16.3.1 三个耦合接口规范与供给子包'
C_T08_B1_SCOPE='   - **规模与范围**：规模控制在约 100–200 个概念（覆盖十天干、十二地支、九星、八门、八神等盘面基础元素），仅包含稳定 ID（`concept_id`）、名称与基础类象；'
C_T08_B2_NOTE='   - **承接说明**：为 UI 标记提供内容与分歧数据，包括吉凶定性、条件槽位可供性与流派分歧展示。'
C_T08_B3_NOTE='   - **承接说明**：为 AI 解盘与端侧证据高亮提供底层的无损证据链切片，确保标记内容能溯源至底本原页与字框坐标。'

# ============================ 运行期状态 ============================
CUR_TMP=""
CASE_MSG=""
CASE_REJECTED=0
G_PASS=0
G_TOTAL=0

# ============================ 临时文件管理 ============================
# 注意：new_tmp 常常在命令替换 $( ) 的子 shell 中调用，普通变量无法跨子 shell
# 累计；因此把每个临时路径追加到一张清单文件，由 EXIT trap 读取清单统一清理。
TMPLIST_FILE=""
TMPLIST_FILE="$(mktemp -t g3r3l-XXXXXX 2>/dev/null)"
new_tmp() {
  local t
  t="$(mktemp -t g3r3-XXXXXX 2>/dev/null)" || t="$(mktemp "${TMPDIR:-/tmp}/g3r3-XXXXXX" 2>/dev/null)" || return 1
  [ -n "$t" ] || return 1
  if [ -n "$TMPLIST_FILE" ]; then printf '%s\n' "$t" >> "$TMPLIST_FILE"; fi
  printf '%s\n' "$t"
}
cleanup() {
  local f
  if [ -n "$TMPLIST_FILE" ] && [ -f "$TMPLIST_FILE" ]; then
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      rm -f "$f" "$f.t" 2>/dev/null
    done < "$TMPLIST_FILE"
    rm -f "$TMPLIST_FILE" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM HUP

# ============================ 精确匹配原语 ============================
# 整行命中次数（ENVIRON 传参 + LC_ALL=C 逐字节比较）
line_count() {
  LCNT="$2" LC_ALL=C awk '$0 == ENVIRON["LCNT"] { c++ } END { print c + 0 }' "$1"
}
total_lines() { wc -l < "$1" | tr -d ' '; }

# 字符串内 needle 的字面出现次数（非正则；空 needle 返回 -1 视为非法）
occ_in() {
  H="$1" N="$2" LC_ALL=C awk 'BEGIN{
    h = ENVIRON["H"]; n = ENVIRON["N"]
    if (length(n) == 0) { print -1; exit }
    c = 0
    while ((i = index(h, n)) > 0) { c++; h = substr(h, i + length(n)) }
    print c
  }'
}

# 取一行中第 3 / 4 / 5 个 pipe cell（只去除首尾的普通空格与 Tab；
# form-feed / vertical-tab 属于有效字符，必须保留，不得当空白删掉）
cell_of() {
  case "$2" in
    3) printf '%s\n' "$1" | LC_ALL=C awk -F'|' 'function trim(s){ gsub(/^ +/,"",s); gsub(/ +$/,"",s); while (substr(s,1,1)==sprintf("%c",9)) s=substr(s,2); while (length(s)>0 && substr(s,length(s),1)==sprintf("%c",9)) s=substr(s,1,length(s)-1); return s } { print trim($3) }' ;;
    4) printf '%s\n' "$1" | LC_ALL=C awk -F'|' 'function trim(s){ gsub(/^ +/,"",s); gsub(/ +$/,"",s); while (substr(s,1,1)==sprintf("%c",9)) s=substr(s,2); while (length(s)>0 && substr(s,length(s),1)==sprintf("%c",9)) s=substr(s,1,length(s)-1); return s } { print trim($4) }' ;;
    5) printf '%s\n' "$1" | LC_ALL=C awk -F'|' 'function trim(s){ gsub(/^ +/,"",s); gsub(/ +$/,"",s); while (substr(s,1,1)==sprintf("%c",9)) s=substr(s,2); while (length(s)>0 && substr(s,length(s),1)==sprintf("%c",9)) s=substr(s,1,length(s)-1); return s } { print trim($5) }' ;;
    *) return 1 ;;
  esac
}

# 断言 anchor 命中次数恰好等于给定值
assert_count() { [ "$(line_count "$1" "$2")" = "$3" ]; }

# ---- replace_line(anchor, exact_line)：整行替换，断言新行 1 次 / 原行 0 次 ----
replace_line() { # file anchor exact_line
  local f="$1" a="$2" n="$3"
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  [ "$n" != "$a" ] || return 1
  ANCHOR="$a" NEWLINE="$n" LC_ALL=C awk '$0 == ENVIRON["ANCHOR"] { print ENVIRON["NEWLINE"]; next } { print }' "$f" > "$f.t" || return 1
  mv "$f.t" "$f" || return 1
  [ "$(line_count "$f" "$n")" = 1 ] || return 1
  [ "$(line_count "$f" "$a")" = 0 ] || return 1
  return 0
}

# ---- delete_line(anchor) ----
del_line() { # file anchor
  local f="$1" a="$2" before after
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  before="$(total_lines "$f")"
  ANCHOR="$a" LC_ALL=C awk '$0 != ENVIRON["ANCHOR"] { print }' "$f" > "$f.t" || return 1
  mv "$f.t" "$f" || return 1
  [ "$(line_count "$f" "$a")" = 0 ] || return 1
  after="$(total_lines "$f")"
  [ "$after" = "$((before - 1))" ] || return 1
  return 0
}

# ---- duplicate_line(anchor)：在 anchor 后原样追加同一行一次 ----
dup_line() { # file anchor
  local f="$1" a="$2" before after
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  before="$(total_lines "$f")"
  ANCHOR="$a" LC_ALL=C awk '$0 == ENVIRON["ANCHOR"] { print; print; next } { print }' "$f" > "$f.t" || return 1
  mv "$f.t" "$f" || return 1
  [ "$(line_count "$f" "$a")" = 2 ] || return 1
  after="$(total_lines "$f")"
  [ "$after" = "$((before + 1))" ] || return 1
  return 0
}

# ---- replace_text(anchor, before, after)：before 必须在 anchor 内恰好出现一次 ----
replace_text() { # file anchor before after
  local f="$1" a="$2" b="$3" c="$4" occ new
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  occ="$(occ_in "$a" "$b")"
  [ "$occ" = 1 ] || return 1
  new="$(ASTR="$a" BSTR="$b" CSTR="$c" LC_ALL=C awk 'BEGIN{
    t = ENVIRON["ASTR"]; b = ENVIRON["BSTR"]; i = index(t, b)
    if (i == 0) { print t; exit }
    print substr(t, 1, i - 1) ENVIRON["CSTR"] substr(t, i + length(b))
  }')"
  [ "$new" != "$a" ] || return 1
  if [ -n "$c" ]; then
    case "$new" in *"$c"*) : ;; *) return 1 ;; esac
  fi
  replace_line "$f" "$a" "$new" || return 1
  return 0
}

# ---- replace_map_value(anchor, value)：§16.2 三列行，保留 key，整套替换第 3 pipe cell ----
map_value() { # file anchor value
  local f="$1" a="$2" v="$3" new cell
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  new="$(ANCHOR="$a" VALUE="$v" LC_ALL=C awk -F'|' 'BEGIN{ OFS = "|" } $0 == ENVIRON["ANCHOR"] { $3 = " " ENVIRON["VALUE"] " "; print; exit }' "$f")"
  [ -n "$new" ] || return 1
  cell="$(cell_of "$new" 3)"
  [ "$cell" = "$v" ] || return 1
  replace_line "$f" "$a" "$new" || return 1
  return 0
}

# ---- replace_field_cell(anchor, module|package, value)：§16.3.2 六列行 ----
field_cell() { # file anchor module|package value
  local f="$1" a="$2" col="$3" v="$4" new cell
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  case "$col" in
    module)
      new="$(ANCHOR="$a" VALUE="$v" LC_ALL=C awk -F'|' 'BEGIN{ OFS = "|" } $0 == ENVIRON["ANCHOR"] { $4 = " " ENVIRON["VALUE"] " "; print; exit }' "$f")"
      cell="$(cell_of "$new" 4)" ;;
    package)
      new="$(ANCHOR="$a" VALUE="$v" LC_ALL=C awk -F'|' 'BEGIN{ OFS = "|" } $0 == ENVIRON["ANCHOR"] { $5 = " " ENVIRON["VALUE"] " "; print; exit }' "$f")"
      cell="$(cell_of "$new" 5)" ;;
    *) return 1 ;;
  esac
  [ -n "$new" ] || return 1
  [ "$cell" = "$v" ] || return 1
  replace_line "$f" "$a" "$new" || return 1
  return 0
}

# ---- append_line(anchor, exact_line)：在 anchor 之后插入 exact_line ----
append_line() { # file anchor exact_line
  local f="$1" a="$2" l="$3" before after
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  before="$(line_count "$f" "$l")"
  ANCHOR="$a" APPLINE="$l" LC_ALL=C awk '$0 == ENVIRON["ANCHOR"] { print; print ENVIRON["APPLINE"]; next } { print }' "$f" > "$f.t" || return 1
  mv "$f.t" "$f" || return 1
  after="$(line_count "$f" "$l")"
  [ "$after" = "$((before + 1))" ] || return 1
  [ "$after" -ge 1 ] || return 1
  return 0
}

# ---- delete_block(start_anchor, end_heading)：删到 end_heading 之前，end heading 保留 ----
del_block() { # file start_anchor end_heading_regex
  local f="$1" s="$2" e="$3" before after endcnt
  [ "$(line_count "$f" "$s")" = 1 ] || return 1
  before="$(total_lines "$f")"
  ANCHOR="$s" ENDRE="$e" LC_ALL=C awk '
    {
      if (inb && $0 != ENVIRON["ANCHOR"] && ($0 ~ /^[0-9]+\. \*\*/ || $0 ~ ENVIRON["ENDRE"])) inb = 0
      if ($0 == ENVIRON["ANCHOR"]) inb = 1
      if (!inb) print
    }
  ' "$f" > "$f.t" || return 1
  mv "$f.t" "$f" || return 1
  [ "$(line_count "$f" "$s")" = 0 ] || return 1
  after="$(total_lines "$f")"
  [ "$after" -lt "$before" ] || return 1
  endcnt="$(ENDRE="$e" LC_ALL=C awk '$0 ~ ENVIRON["ENDRE"] { c++ } END { print c + 0 }' "$f")"
  [ "$endcnt" -ge 1 ] || return 1
  return 0
}

# ---- append_gap_line(anchor, exact_line)：在 anchor 之后先插入一个空行，再插入 exact_line ----
# 用于构造「封闭块结束后、下一 START 之前隔空行追加」的区域间隙绕过。
# 断言：anchor 恰 1 次；总行数 +2；exact_line 命中次数 +1；anchor 仍恰 1 次。
append_gap_line() { # file anchor exact_line
  local f="$1" a="$2" l="$3" before_total after_total before after
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  before_total="$(total_lines "$f")"
  before="$(line_count "$f" "$l")"
  ANCHOR="$a" APPLINE="$l" LC_ALL=C awk '$0 == ENVIRON["ANCHOR"] { print; print ""; print ENVIRON["APPLINE"]; next } { print }' "$f" > "$f.t" || return 1
  mv "$f.t" "$f" || return 1
  after_total="$(total_lines "$f")"
  [ "$after_total" = "$((before_total + 2))" ] || return 1
  after="$(line_count "$f" "$l")"
  [ "$after" = "$((before + 1))" ] || return 1
  [ "$after" -ge 1 ] || return 1
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  return 0
}

# ---- append_suffix(anchor, suffix)：把 anchor 整行替换为 anchor+suffix（基于 replace_line） ----
# 用于构造「表格数据行行尾追加第三列」的绕过。
# 断言：anchor 恰 1 次；suffix 非空；新行恰 1 次；原行 0 次。
append_suffix() { # file anchor suffix
  local f="$1" a="$2" s="$3" new
  [ "$(line_count "$f" "$a")" = 1 ] || return 1
  [ -n "$s" ] || return 1
  new="${a}${s}"
  replace_line "$f" "$a" "$new" || return 1
  [ "$(line_count "$f" "$new")" = 1 ] || return 1
  [ "$(line_count "$f" "$a")" = 0 ] || return 1
  return 0
}

# ============================ 用例表（109 例） ============================
# 每个组合用例的每个子操作都必须独立满足命中次数断言，按 CASES.md 给出的顺序执行。
apply_case() { # $1 = case id，操作 $CUR_TMP；任一子操作失败即返回非零
  local cid="$1"
  case "$cid" in
    # ------------------------------- D-07（25） -------------------------------
    d07-01) del_line "$CUR_TMP" "$C_D07_TP_FIELDS" ;;
    d07-02) replace_line "$CUR_TMP" "$C_D07_TP_FIELDS" "$L_D07_02" ;;
    d07-03) del_line "$CUR_TMP" "$C_D07_RI_VERSION" ;;
    d07-04) replace_text "$CUR_TMP" "$C_D07_TP_START" 'TechniqueProfilePack' 'WrongProfilePack' ;;
    d07-05) replace_text "$CUR_TMP" "$C_D07_QC_START" 'QueryContractPack' 'WrongQueryPack' ;;
    d07-06) replace_text "$CUR_TMP" "$C_D07_RI_START" 'RuleIndexPack' 'WrongRulePack' ;;
    d07-07) del_line "$CUR_TMP" "$C_D07_QC_COMPAT" ;;
    d07-08) replace_text "$CUR_TMP" "$C_D07_QC_COMPAT" '必须保持' '不得保持' ;;
    d07-09) replace_text "$CUR_TMP" "$C_D07_QC_COMPAT" '必须保持' '不应保持' ;;
    d07-10) replace_text "$CUR_TMP" "$C_D07_QC_COMPAT" '必须保持' '并未保持' ;;
    d07-11) del_line "$CUR_TMP" "$C_D07_TP_PROFILE" ;;
    d07-12) del_line "$CUR_TMP" "$C_D07_TP_OPERATORS" ;;
    d07-13) del_line "$CUR_TMP" "$C_D07_TP_AST" ;;
    d07-14) del_line "$CUR_TMP" "$C_D07_QC_ENTRY" ;;
    d07-15) del_line "$CUR_TMP" "$C_D07_QC_SPAN" ;;
    d07-16) del_line "$CUR_TMP" "$C_D07_QC_SEARCH" ;;
    d07-17) del_line "$CUR_TMP" "$C_D07_QC_MATCH" ;;
    d07-18) del_line "$CUR_TMP" "$C_D07_RI_DECLARATIVE" ;;
    d07-19) dup_line "$CUR_TMP" "$C_D07_TP_FIELDS" ;;
    d07-20) dup_line "$CUR_TMP" "$C_D07_QC_ENTRY" ;;
    d07-21) dup_line "$CUR_TMP" "$C_D07_RI_DECLARATIVE" ;;
    d07-22) replace_text "$CUR_TMP" "$C_D07_QC_ENTRY" 'getEntry' 'WronggetEntry' ;;
    d07-23) replace_text "$CUR_TMP" "$C_D07_QC_SPAN" 'getSourceSpan' 'WronggetSourceSpan' ;;
    d07-24) replace_text "$CUR_TMP" "$C_D07_QC_SEARCH" 'searchKnowledge' 'WrongsearchKnowledge' ;;
    d07-25) replace_text "$CUR_TMP" "$C_D07_QC_MATCH" 'matchFacts' 'WrongmatchFacts' ;;
    # ----------------------- D-07（R4 加固 5 例） -----------------------
    # d07-26：把 TP 的「事实字段与枚举」完整原行移动到 RI 块（全文仍只出现一次）
    d07-26) del_line "$CUR_TMP" "$C_D07_TP_FIELDS" \
              && append_line "$CUR_TMP" "$C_D07_RI_VERSION" "$C_D07_TP_FIELDS" ;;
    # d07-27：TP 块追加冲突列表项
    d07-27) append_line "$CUR_TMP" "$C_D07_TP_FIELDS" "$L_D07_27" ;;
    # d07-28：QC 块追加第五个查询接口
    d07-28) append_line "$CUR_TMP" "$C_D07_QC_MATCH" "$L_D07_28" ;;
    # d07-29 / d07-30：Package 名中插入 form-feed / vertical-tab
    d07-29) replace_text "$CUR_TMP" "$C_D07_TP_START" 'TechniqueProfilePack' "$V_TP_FF" ;;
    d07-30) replace_text "$CUR_TMP" "$C_D07_TP_START" 'TechniqueProfilePack' "$V_TP_VT" ;;
    # ----------------------- D-07（R5 区域间隙 4 例） -----------------------
    # d07-31：TP 第四条目之后隔一个空行追加冲突 bullet（旧「遇空行即停」解析看不到它）
    d07-31) append_gap_line "$CUR_TMP" "$C_D07_TP_AST" "$L_D07_27" ;;
    # d07-32：TP 第四条目之后隔一个空行追加冲突段落（非列表行）
    d07-32) append_gap_line "$CUR_TMP" "$C_D07_TP_AST" "$L_D07_32" ;;
    # d07-33：QC 第五条目（向后兼容声明）之后隔一个空行追加冲突段落
    d07-33) append_gap_line "$CUR_TMP" "$C_D07_QC_COMPAT" "$L_D07_33" ;;
    # d07-34：RI 第二条目之后、### 16.2 之前隔一个空行追加冲突段落
    d07-34) append_gap_line "$CUR_TMP" "$C_D07_RI_DECLARATIVE" "$L_D07_34" ;;
    # ------------------------------- T-07（25） -------------------------------
    t07-01) map_value "$CUR_TMP" "$C_T07_M01" "$V_WRONG_PACK" ;;
    t07-02) map_value "$CUR_TMP" "$C_T07_M02" "$V_WRONG_PACK" ;;
    t07-03) map_value "$CUR_TMP" "$C_T07_M03" "$V_WRONG_PACK" ;;
    t07-04) map_value "$CUR_TMP" "$C_T07_M04" "$V_WRONG_PACK" ;;
    t07-05) map_value "$CUR_TMP" "$C_T07_M05" "$V_WRONG_PACK" ;;
    t07-06) map_value "$CUR_TMP" "$C_T07_M06" "$V_WRONG_PACK" ;;
    t07-07) map_value "$CUR_TMP" "$C_T07_M07" "$V_WRONG_PACK" ;;
    t07-08) map_value "$CUR_TMP" "$C_T07_M08" "$V_WRONG_PACK" ;;
    t07-09) map_value "$CUR_TMP" "$C_T07_M09" "$V_WRONG_PACK" ;;
    t07-10) map_value "$CUR_TMP" "$C_T07_M10" "$V_WRONG_PACK" ;;
    t07-11) map_value "$CUR_TMP" "$C_T07_M11" "$V_WRONG_PACK" ;;
    t07-12) map_value "$CUR_TMP" "$C_T07_M12" "$V_WRONG_PACK" ;;
    t07-13) map_value "$CUR_TMP" "$C_T07_M13" "$V_WRONG_PACK" ;;
    t07-14) map_value "$CUR_TMP" "$C_T07_M14" "$V_WRONG_PACK" ;;
    t07-15) map_value "$CUR_TMP" "$C_T07_M15" "$V_WRONG_PACK" ;;
    t07-16) map_value "$CUR_TMP" "$C_T07_M15" "$V_T07_16" ;;
    t07-17) map_value "$CUR_TMP" "$C_T07_M14" "$V_T07_17" ;;
    t07-18) del_line "$CUR_TMP" "$C_T07_REPLACEMENT" ;;
    t07-19) dup_line "$CUR_TMP" "$C_T07_REPLACEMENT" ;;
    t07-20) replace_text "$CUR_TMP" "$C_T07_REPLACEMENT" '正式取代' '不得取代' ;;
    t07-21) replace_text "$CUR_TMP" "$C_T07_REPLACEMENT" '正式取代' '并未正式取代' ;;
    t07-22) replace_text "$CUR_TMP" "$C_T07_REPLACEMENT" '正式取代' '尚未正式取代' ;;
    t07-23) replace_text "$CUR_TMP" "$C_T07_REPLACEMENT" '正式取代' '不应正式取代' ;;
    t07-24) del_line "$CUR_TMP" "$C_T07_M02" ;;
    t07-25) dup_line "$CUR_TMP" "$C_T07_M15" ;;
    # ----------------------- T-07（R4 加固 1 例） -----------------------
    # t07-26：保留正确取代声明，再追加相反声明
    t07-26) append_line "$CUR_TMP" "$C_T07_REPLACEMENT" "$L_T07_26" ;;
    # ----------------------- T-07（R5 表格额外列 2 例） -----------------------
    # t07-27：release-manifest 正确数据行行尾追加第三列（key/value 字典比较看不到第三列）
    t07-27) append_suffix "$CUR_TMP" "$C_T07_M01" "$V_T07_EXTRA_COL" ;;
    # t07-28：query-contract 末行行尾追加第三列
    t07-28) append_suffix "$CUR_TMP" "$C_T07_M15" "$V_T07_EXTRA_COL" ;;
    # ------------------------------- T-08（39） -------------------------------
    t08-01) field_cell "$CUR_TMP" "$C_T08_R04" module "$V_MODULE_M2" \
              && field_cell "$CUR_TMP" "$C_T08_R04_M2" package "$V_SOURCE_ASSET_PACK" ;;
    t08-02) field_cell "$CUR_TMP" "$C_T08_R01" module "$V_MODULE_M2" ;;
    t08-03) field_cell "$CUR_TMP" "$C_T08_R02" module "$V_MODULE_M2" ;;
    t08-04) field_cell "$CUR_TMP" "$C_T08_R03" module "$V_MODULE_M2" ;;
    t08-05) field_cell "$CUR_TMP" "$C_T08_R04" module "$V_MODULE_M2" ;;
    t08-06) field_cell "$CUR_TMP" "$C_T08_R05" module "$V_MODULE_M2" ;;
    t08-07) field_cell "$CUR_TMP" "$C_T08_R01" package "$V_SOURCE_ASSET_PACK" ;;
    t08-08) field_cell "$CUR_TMP" "$C_T08_R02" package "$V_SOURCE_ASSET_PACK" ;;
    t08-09) field_cell "$CUR_TMP" "$C_T08_R03" package "$V_SOURCE_ASSET_PACK" ;;
    t08-10) field_cell "$CUR_TMP" "$C_T08_R04" package "$V_SOURCE_ASSET_PACK" ;;
    t08-11) field_cell "$CUR_TMP" "$C_T08_R05" package "$V_SOURCE_ASSET_PACK" ;;
    t08-12) replace_text "$CUR_TMP" "$C_T08_S1_01" 'KnowledgeDataPack' 'SourceAssetPack' \
              && replace_text "$CUR_TMP" "$C_T08_B1_SUPPLY" 'KnowledgeDataPack' 'SourceAssetPack' ;;
    t08-13) replace_text "$CUR_TMP" "$C_T08_S1_02" '由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给' '由 `SourceAssetPack` 供给' \
              && replace_text "$CUR_TMP" "$C_T08_B2_SUPPLY" '由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给' '由 `SourceAssetPack` 供给' ;;
    t08-14) replace_text "$CUR_TMP" "$C_T08_S1_03" 'EvidenceMapPack' 'SearchIndexPack' \
              && replace_text "$CUR_TMP" "$C_T08_B3_SUPPLY" 'EvidenceMapPack' 'SearchIndexPack' ;;
    t08-15) replace_text "$CUR_TMP" "$C_T08_S1_01" '由 `KnowledgeDataPack` 供给' '由 `KnowledgeDataPack` 供给，并由 `SourceAssetPack` 供给' ;;
    t08-16) replace_text "$CUR_TMP" "$C_T08_S1_02" '由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给' '由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，并由 `SourceAssetPack` 供给' ;;
    t08-17) replace_text "$CUR_TMP" "$C_T08_S1_03" '由 `EvidenceMapPack` 供给' '由 `EvidenceMapPack` 供给，并由 `SearchIndexPack` 供给' ;;
    t08-18) append_line "$CUR_TMP" "$C_T08_B1_SUPPLY" "$L_APPEND_SUPPLY_SOURCE" ;;
    t08-19) append_line "$CUR_TMP" "$C_T08_B2_SUPPLY" "$L_APPEND_SUPPLY_SOURCE" ;;
    t08-20) append_line "$CUR_TMP" "$C_T08_B3_SUPPLY" "$L_APPEND_SUPPLY_SEARCH" ;;
    t08-21) replace_text "$CUR_TMP" "$C_T08_B1_HEAD" '最小盘面概念字典' 'Wrong概念字典' ;;
    t08-22) replace_text "$CUR_TMP" "$C_T08_B2_HEAD" 'MarkContentBinding' 'WrongMarkContentBinding' ;;
    t08-23) replace_text "$CUR_TMP" "$C_T08_B3_HEAD" 'EvidenceBundle' 'WrongEvidenceBundle' ;;
    t08-24) replace_text "$CUR_TMP" "$C_T08_P01" '由 M4 生产' '由 M2 生产' ;;
    t08-25) replace_text "$CUR_TMP" "$C_T08_P04" 'KnowledgeDataPack' 'SourceAssetPack' ;;
    t08-26) field_cell "$CUR_TMP" "$C_T08_R01" module "$V_MODULE_M4_M5" ;;
    t08-27) field_cell "$CUR_TMP" "$C_T08_R02" module "$V_MODULE_M4_M5" ;;
    t08-28) assert_count "$CUR_TMP" "$C_T08_B3_SUPPLY" 1 \
              && del_line "$CUR_TMP" "$C_T08_S1_03" \
              && del_block "$CUR_TMP" "$C_T08_B3_HEAD" '^#### 16\.3\.2 ' ;;
    t08-29) del_line "$CUR_TMP" "$C_T08_R04" ;;
    t08-30) replace_text "$CUR_TMP" "$C_T08_S1_01" '不含规则 DSL' '' ;;
    t08-31) replace_text "$CUR_TMP" "$C_T08_S1_01" 'TAG_SYSTEM_DESIGN.md §12.2' '' ;;
    t08-32) replace_text "$CUR_TMP" "$C_T08_P02" '由 M4 结构化生产' '由 M2 结构化生产' ;;
    t08-33) replace_text "$CUR_TMP" "$C_T08_P03" '由 M4/M6 审核产出' '由 M2 审核产出' ;;
    t08-34) replace_text "$CUR_TMP" "$C_T08_P05" 'M4/M7/M6' 'M2' ;;
    t08-35) replace_text "$CUR_TMP" "$C_T08_S1_01" '最小盘面概念字典' 'Wrong概念字典' ;;
    t08-36) replace_text "$CUR_TMP" "$C_T08_S1_02" 'MarkContentBinding' 'WrongMarkContentBinding' ;;
    t08-37) replace_text "$CUR_TMP" "$C_T08_S1_03" 'EvidenceBundle' 'WrongEvidenceBundle' ;;
    t08-38) replace_text "$CUR_TMP" "$C_T08_B1_LIMIT" '不含规则 DSL' '' ;;
    t08-39) replace_text "$CUR_TMP" "$C_T08_B1_LIMIT" 'TAG_SYSTEM_DESIGN.md §12.2' '' ;;
    # ----------------------- T-08（R4 加固 3 例） -----------------------
    # t08-40：§1 正确 MarkContentBinding 之后追加同名错误接口
    t08-40) append_line "$CUR_TMP" "$C_T08_S1_02" "$L_T08_40" ;;
    # t08-41：B3 正确供给行之后追加非「供给子包」标签的额外 Package 来源
    t08-41) append_line "$CUR_TMP" "$C_T08_B3_SUPPLY" "$L_T08_41" ;;
    # t08-42：B1 正确硬限制行之后追加「允许规则 DSL」的例外声明
    t08-42) append_line "$CUR_TMP" "$C_T08_B1_LIMIT" "$L_T08_42" ;;
    # ----------------------- T-08（R5 §16.3.1 区域封闭 5 例） -----------------------
    # t08-43：B3 承接说明之后、#### 16.3.2 之前再插入同名 B3 标题（块解析以标题为界，重复标题块为空）
    t08-43) append_line "$CUR_TMP" "$C_T08_B3_NOTE" "$C_T08_B3_HEAD" ;;
    # t08-44：B1 硬限制约束之后重复 B1 标题
    t08-44) append_line "$CUR_TMP" "$C_T08_B1_LIMIT" "$C_T08_B1_HEAD" ;;
    # t08-45：§16.3.1 标题与 B1 标题之间插入块外正文
    t08-45) append_line "$CUR_TMP" "$C_T08_S1631_HEAD" "$L_T08_45" ;;
    # t08-46：B3 承接说明之后隔一个空行再重复 B3 标题
    t08-46) append_gap_line "$CUR_TMP" "$C_T08_B3_NOTE" "$C_T08_B3_HEAD" ;;
    # t08-47：B2 承接说明之后重复 B2 标题（B2 块尾）
    t08-47) append_line "$CUR_TMP" "$C_T08_B2_NOTE" "$C_T08_B2_HEAD" ;;
    *) return 1 ;;
  esac
}

# 每例绑定的稳定 FAIL ID（CASES.md 表格最后一列）。两 ID 的用例要求两者都命中。
case_ids() {
  case "$1" in
    d07-01|d07-02|d07-04|d07-11|d07-12|d07-13|d07-19|d07-26|d07-27|d07-29|d07-30) printf 'G3-D07-TP\n' ;;
    d07-03|d07-06|d07-18|d07-21) printf 'G3-D07-RI\n' ;;
    d07-05|d07-14|d07-15|d07-16|d07-17|d07-20|d07-22|d07-23|d07-24|d07-25|d07-28) printf 'G3-D07-QC\n' ;;
    d07-07|d07-08|d07-09|d07-10) printf 'G3-D07-COMPAT\n' ;;
    t07-01|t07-02|t07-03|t07-04|t07-05|t07-06|t07-07|t07-08|t07-09|t07-10|t07-11|t07-12|t07-13|t07-14|t07-15|t07-16|t07-17|t07-24|t07-25) printf 'G3-T07-MAP\n' ;;
    t07-18|t07-19|t07-20|t07-21|t07-22|t07-23|t07-26) printf 'G3-T07-REPLACEMENT\n' ;;
    t08-01|t08-02|t08-03|t08-04|t08-05|t08-06|t08-07|t08-08|t08-09|t08-10|t08-11|t08-26|t08-27|t08-29) printf 'G3-T08-TABLE\n' ;;
    t08-12|t08-13|t08-14) printf 'G3-T08-SEC1 G3-T08-BLOCK\n' ;;
    t08-15|t08-16|t08-17|t08-28|t08-35|t08-36|t08-37) printf 'G3-T08-SEC1\n' ;;
    t08-18|t08-19|t08-20|t08-21|t08-22|t08-23) printf 'G3-T08-BLOCK\n' ;;
    t08-24|t08-25|t08-32|t08-33|t08-34) printf 'G3-T08-PROSE\n' ;;
    t08-30|t08-38|t08-42) printf 'G3-T08-DSL\n' ;;
    t08-31|t08-39) printf 'G3-T08-G4\n' ;;
    t08-40) printf 'G3-T08-SEC1\n' ;;
    t08-41) printf 'G3-T08-BLOCK\n' ;;
    # ---- R5 区域边界封闭新增绑定 ----
    d07-31|d07-32) printf 'G3-D07-TP\n' ;;
    d07-33) printf 'G3-D07-QC\n' ;;
    d07-34) printf 'G3-D07-RI\n' ;;
    t07-27|t07-28) printf 'G3-T07-MAP\n' ;;
    t08-43|t08-44|t08-45|t08-46|t08-47) printf 'G3-T08-BLOCK\n' ;;
    *) return 1 ;;
  esac
}

# ============================ 用例执行器 ============================
# 绑定 FAIL ID 命中判定：必须是完整 token，结构严格为
#     ^FAIL[[:space:]]+<完整ID>([[:space:]]|$)
# 因此 `FAIL  G3-D07-QC-BOGUS`、`FAIL XG3-D07-QC`、`FAILURE G3-D07-QC`、
# `PASS  G3-D07-QC` 以及普通正文中出现的 `G3-D07-QC` 都不算命中。
ids_hit_all() { # output id...
  local out="$1" id
  shift
  for id in "$@"; do
    [ -n "$id" ] || continue
    printf '%s\n' "$out" \
      | LC_ALL=C grep -E -q -- '^FAIL[[:space:]]+'"${id}"'([[:space:]]|$)' || return 1
  done
  return 0
}

# 单例核心流程：全新临时副本 -> 施加变异（含命中断言）-> 调用门禁 -> 判定。
# 结果写入 CASE_MSG / CASE_REJECTED；返回值 1 表示变异未成功施加。
run_case_core() { # cid applyfn ids src gate
  local cid="$1" applyfn="$2" ids="$3" src="$4" gate="$5"
  local tmp rc out
  CASE_REJECTED=0
  CASE_MSG=""
  tmp="$(new_tmp)" || { CASE_MSG="MUTATION_NOT_APPLIED $cid"; return 1; }
  if ! cp "$src" "$tmp"; then
    rm -f "$tmp" "$tmp.t" 2>/dev/null
    CASE_MSG="MUTATION_NOT_APPLIED $cid"
    return 1
  fi
  CUR_TMP="$tmp"
  if ! "$applyfn" "$cid"; then
    rm -f "$tmp" "$tmp.t" 2>/dev/null
    CASE_MSG="MUTATION_NOT_APPLIED $cid"
    return 1
  fi
  out="$(SPEC="$tmp" bash "$gate" 2>&1)"
  rc=$?
  if [ "$rc" -ne 0 ] && ids_hit_all "$out" $ids; then
    CASE_REJECTED=1
    CASE_MSG="rejected $cid (exit $rc) $ids"
  else
    CASE_MSG="not-rejected $cid (exit $rc) $ids"
  fi
  rm -f "$tmp" "$tmp.t" 2>/dev/null
  return 0
}

run_case() { # cid
  run_case_core "$1" apply_case "$(case_ids "$1")" "$SPEC_SRC" "$GATE"
  printf '%s\n' "$CASE_MSG"
}

gen_ids() { # prefix count
  local p="$1" n="$2" i=1
  while [ "$i" -le "$n" ]; do printf '%s-%02d\n' "$p" "$i"; i=$((i + 1)); done
}

# 单组运行；单例失败绝不中断整组。
run_group() { # prefix count
  local p="$1" n="$2" pass=0 total=0 cid
  for cid in $(gen_ids "$p" "$n"); do
    run_case "$cid"
    total=$((total + 1))
    if [ "$CASE_REJECTED" = 1 ]; then pass=$((pass + 1)); fi
  done
  printf '%s: %d/%d rejected\n' "$p" "$pass" "$total"
  G_PASS=$((G_PASS + pass))
  G_TOTAL=$((G_TOTAL + total))
}

# ============================ selftest（自检） ============================
ST_PASS=0
ST_TOTAL=0
st() { # desc ok(1/0)
  ST_TOTAL=$((ST_TOTAL + 1))
  if [ "$2" = 1 ]; then
    ST_PASS=$((ST_PASS + 1))
    printf 'PASS  selftest  %s\n' "$1"
  else
    printf 'FAIL  selftest  %s\n' "$1"
  fi
}

# 把每个参数写成 fixture 的一行
mkfixture() { # path line...
  local p="$1"
  shift
  : > "$p" || return 1
  local l
  for l in "$@"; do printf '%s\n' "$l" >> "$p"; done
}

# normalize：仅删除 5 种字节 —— 反引号(96)、星号(42)、普通空格(32)、Tab(9)、CR(13)。
# 其余一切字节都保留：form-feed(12)、vertical-tab(11)、其他 Unicode 空白、
# 中英文标点、数字、斜杠、否定词与标识符。不得使用 [[:space:]] 这种宽泛删除。
norm_str() {
  printf '%s' "$1" | LC_ALL=C tr -d '\011\015\040\052\140'
}
norm_eq() { [ "$(norm_str "$1")" = "$(norm_str "$2")" ]; }

# selftest 用的合成 apply 函数
st_apply_missing() { del_line "$CUR_TMP" 'NOPE-ANCHOR-§-不存在的行'; }
st_apply_ok() { return 0; }

# 编号块解析：起于精确 HEAD 行，止于下一个 ^[0-9]+\. \*\* 或 ^#### 16\.3\.2 行
block_lines() { # file head
  HEAD="$2" LC_ALL=C awk '
    {
      if (inb && $0 != ENVIRON["HEAD"] && ($0 ~ /^[0-9]+\. \*\*/ || $0 ~ /^#### 16\.3\.2 /)) inb = 0
      if ($0 == ENVIRON["HEAD"]) inb = 1
      if (inb) print
    }
  ' "$1"
}
block_supply_count() { block_lines "$1" "$2" | LC_ALL=C grep -c -E '^[[:space:]]+- \*\*供给子包\*\*：'; }
block_has_line() { block_lines "$1" "$2" | LC_ALL=C grep -F -x -q -- "$3"; }

run_selftest() {
  local ok fx1 fx2 fx3 fx5 fx6 g1 g2 gm0 gm1 c1 c2 t1 t2 out
  local H1 H2 H3 H3B tail
  local fx7a fx7b fx7c fx7d
  ST_PASS=0
  ST_TOTAL=0

  # ---- [1] 非施加 / no-op 变异必须报 MUTATION_NOT_APPLIED，绝不判 rejected ----
  fx1="$(new_tmp)"
  mkfixture "$fx1" 'hello' 'world'
  if del_line "$fx1" 'NOPE-ANCHOR-§-不存在的行'; then ok=0; else ok=1; fi
  st "[1] anchor 缺失时原语失败（no-op 不算命中）" "$ok"

  gm1="$(new_tmp)"
  mkfixture "$gm1" '#!/usr/bin/env bash' 'echo "FAIL  G3-D07-TP  synthetic"' 'exit 1'
  run_case_core 'st-noop' st_apply_missing 'G3-D07-TP' "$fx1" "$gm1"
  case "$CASE_MSG" in MUTATION_NOT_APPLIED*) ok=1 ;; *) ok=0 ;; esac
  [ "$CASE_REJECTED" = 0 ] || ok=0
  st "[1] runner 打印 MUTATION_NOT_APPLIED 且不判 rejected" "$ok"

  # ---- [2] anchor 命中 0 次失败；命中 2+ 次失败 ----
  fx2="$(new_tmp)"
  mkfixture "$fx2" 'alpha' 'alpha' 'beta'
  if [ "$(line_count "$fx2" 'alpha')" = 2 ] && [ "$(line_count "$fx2" 'gamma')" = 0 ]; then ok=1; else ok=0; fi
  st "[2] 命中计数准确（2 次 / 0 次）" "$ok"
  if del_line "$fx2" 'gamma'; then ok=0; else ok=1; fi
  st "[2] anchor 命中 0 次 -> 失败" "$ok"
  if del_line "$fx2" 'alpha'; then ok=0; else ok=1; fi
  st "[2] anchor 命中 2 次 -> 失败" "$ok"

  # ---- [3] 绑定 ID 未出现在 ^FAIL 行 -> 不得算 rejected ----
  out='PASS  G3-D07-TP
FAIL  G3-T07-MAP  other issue'
  if ids_hit_all "$out" 'G3-D07-TP'; then ok=0; else ok=1; fi
  st "[3] 仅出现在 PASS 行上的 ID 不算命中" "$ok"
  out='FAIL  G3-D07-TP  real'
  if ids_hit_all "$out" 'G3-D07-TP'; then ok=1; else ok=0; fi
  st "[3] 出现在 FAIL 行上的 ID 算命中" "$ok"
  out='FAIL  G3-T07-MAP  x'
  if ids_hit_all "$out" 'G3-D07-COMPAT'; then ok=0; else ok=1; fi
  st "[3] 绑定 ID 缺失（合成输出）-> 不命中" "$ok"

  gm0="$(new_tmp)"
  mkfixture "$gm0" '#!/usr/bin/env bash' 'echo "PASS  G3-D07-TP  synthetic"' 'exit 0'
  run_case_core 'st-exit0' st_apply_ok 'G3-D07-TP' "$fx1" "$gm0"
  case "$CASE_MSG" in rejected*) ok=0 ;; *) ok=1 ;; esac
  st "[3] 门禁退出码为 0 -> 不得 rejected" "$ok"
  run_case_core 'st-miss' st_apply_ok 'G3-D07-COMPAT' "$fx1" "$gm1"
  case "$CASE_MSG" in rejected*) ok=0 ;; *) ok=1 ;; esac
  st "[3] fake gate 非零但绑定 ID 未出现在 ^FAIL 行 -> 不得 rejected" "$ok"
  run_case_core 'st-hit' st_apply_ok 'G3-D07-TP' "$fx1" "$gm1"
  if [ "$CASE_REJECTED" = 1 ]; then ok=1; else ok=0; fi
  st "[3] fake gate 非零且绑定 ID 命中 -> rejected" "$ok"

  # ---- [3b] FAIL ID 必须是完整 token：^FAIL[[:space:]]+<ID>([[:space:]]|$) ----
  if ids_hit_all 'FAIL  G3-D07-QC-BOGUS  超集伪 ID' 'G3-D07-QC'; then ok=0; else ok=1; fi
  st "[3] FAIL  G3-D07-QC-BOGUS 不得冒充 G3-D07-QC" "$ok"
  if ids_hit_all 'FAIL XG3-D07-QC  前缀污染' 'G3-D07-QC'; then ok=0; else ok=1; fi
  st "[3] FAIL XG3-D07-QC 不得命中" "$ok"
  if ids_hit_all 'FAILURE G3-D07-QC  非法动词' 'G3-D07-QC'; then ok=0; else ok=1; fi
  st "[3] FAILURE G3-D07-QC 不得命中" "$ok"
  if ids_hit_all 'PASS  G3-D07-QC  通过行' 'G3-D07-QC'; then ok=0; else ok=1; fi
  st "[3] PASS 行上的 G3-D07-QC 不得命中" "$ok"
  if ids_hit_all '正文提到 G3-D07-QC 但这不是 FAIL 行' 'G3-D07-QC'; then ok=0; else ok=1; fi
  st "[3] 普通正文中的 G3-D07-QC 不得命中" "$ok"
  if ids_hit_all 'FAIL  G3-D07-QC  message' 'G3-D07-QC'; then ok=1; else ok=0; fi
  st "[3] 正确的 FAIL  G3-D07-QC  message 必须命中" "$ok"
  if ids_hit_all 'FAIL  G3-D07-QC' 'G3-D07-QC'; then ok=1; else ok=0; fi
  st "[3] ID 位于行尾（无后继空白）也必须命中" "$ok"
  if ids_hit_all 'FAIL  G3-T08-SEC1  a
FAIL  G3-T08-BLOCK  b' 'G3-T08-SEC1' 'G3-T08-BLOCK'; then ok=1; else ok=0; fi
  st "[3] 两行各报一个完整 ID 时双双命中" "$ok"
  if ids_hit_all 'FAIL  G3-T08-SEC1 G3-T08-BLOCK  同行第二个 ID' 'G3-T08-BLOCK'; then ok=0; else ok=1; fi
  st "[3] FAIL 行首个 token 之后的 ID 不得命中（结构要求紧随 FAIL）" "$ok"

  # ---- [4] 每例独立临时副本，互不影响 ----
  fx3="$(new_tmp)"
  mkfixture "$fx3" 'AAA' 'BBB'
  c1="$(new_tmp)"
  c2="$(new_tmp)"
  cp "$fx3" "$c1"
  cp "$fx3" "$c2"
  append_line "$c1" 'AAA' 'ZZZ'
  if [ "$(line_count "$c1" 'ZZZ')" = 1 ] && [ "$(line_count "$c2" 'ZZZ')" = 0 ] \
     && [ "$(cat "$c2")" = "$(cat "$fx3")" ]; then ok=1; else ok=0; fi
  st "[4] 变异副本 A 不影响副本 B（各自独立）" "$ok"
  t1="$(new_tmp)"
  t2="$(new_tmp)"
  if [ "$t1" != "$t2" ] && [ -n "$t1" ] && [ -n "$t2" ]; then ok=1; else ok=0; fi
  st "[4] new_tmp 每次返回全新路径" "$ok"

  # ---- [5] 精确比较能识别标点 / 标识符 / 否定词的改动 ----
  if norm_eq '`A` *B*' 'AB'; then ok=1; else ok=0; fi
  st "[5] 仅反引号/星号/空白差异 -> 相等" "$ok"
  if norm_eq '必须在规定时间内完成。' '必须在规定时间内完成，'; then ok=0; else ok=1; fi
  st "[5] 单标点差异 -> 不等" "$ok"
  if norm_eq 'KnowledgeDataPack' 'KnowledgeDataPac'; then ok=0; else ok=1; fi
  st "[5] 标识符单字符差异 -> 不等" "$ok"
  if norm_eq '正式取代' '不得取代'; then ok=0; else ok=1; fi
  st "[5] 否定词差异（正式取代 vs 不得取代）-> 不等" "$ok"
  fx5="$(new_tmp)"
  mkfixture "$fx5" '知识层正式取代早期草案'
  if [ "$(line_count "$fx5" '知识层不得取代早期草案')" = 0 ]; then ok=1; else ok=0; fi
  st "[5] 整行精确比较可识别否定词改动" "$ok"

  # ---- [5b] 冻结规范化只删 5 种字节：form-feed / vertical-tab 必须保留 ----
  if [ "$(norm_str "A${CH_FF}B")" = "$(norm_str 'AB')" ]; then ok=0; else ok=1; fi
  st "[5] form-feed 必须保留（不得与无 form-feed 文本相等）" "$ok"
  if [ "$(norm_str "A${CH_VT}B")" = "$(norm_str 'AB')" ]; then ok=0; else ok=1; fi
  st "[5] vertical-tab 必须保留" "$ok"
  if [ "$(printf 'a\tb\vc\fd\re' | LC_ALL=C tr -d '\011\015\040\052\140')" = "ab${CH_VT}c${CH_FF}de" ]; then ok=1; else ok=0; fi
  st "[5] 只删 Tab/CR/空格/星号/反引号，VT 与 FF 原样保留" "$ok"
  if norm_eq "TechniqueProfile${CH_FF}Pack" 'TechniqueProfilePack'; then ok=0; else ok=1; fi
  st "[5] Package 名插入 form-feed 后与原名不等" "$ok"
  if norm_eq "TechniqueProfile${CH_VT}Pack" 'TechniqueProfilePack'; then ok=0; else ok=1; fi
  st "[5] Package 名插入 vertical-tab 后与原名不等" "$ok"

  # ---- [6] 块解析止于下一同级标题 / #### 16.3.2 ----
  fx6="$(new_tmp)"
  H1='1. **`Alpha`**：'
  H2='2. **`Beta`**：'
  H3='3. **`Gamma`**：'
  H3B='3. **`Delta`**：'
  tail='- `p`：由 M4 生产，归入 `KnowledgeDataPack`；'
  mkfixture "$fx6" \
    "$H1" '   - **供给子包**：由 `KnowledgeDataPack` 供给；' \
    "$H2" '   - **供给子包**：由 `RuleIndexPack` 供给；' \
    "$H3" '   - **供给子包**：由 `EvidenceMapPack` 供给；' \
    '#### 16.3.2 尾段' "$tail"
  if [ "$(block_supply_count "$fx6" "$H1")" = 1 ] \
     && [ "$(block_supply_count "$fx6" "$H2")" = 1 ] \
     && [ "$(block_supply_count "$fx6" "$H3")" = 1 ]; then ok=1; else ok=0; fi
  st "[6] 三个编号块各恰 1 条供给声明 -> 通过" "$ok"
  if block_has_line "$fx6" "$H1" '   - **供给子包**：由 `RuleIndexPack` 供给；'; then ok=0; else ok=1; fi
  st "[6] 块解析止于下一同级标题（块1 不含块2 供给行）" "$ok"
  if block_has_line "$fx6" "$H3" "$tail"; then ok=0; else ok=1; fi
  st "[6] 块解析止于 #### 16.3.2（块3 不含尾段）" "$ok"

  g1="$(new_tmp)"
  cp "$fx6" "$g1"
  replace_line "$g1" "$H3" "$H3B"
  if [ "$(block_supply_count "$g1" "$H3")" = 0 ] \
     && [ "$(line_count "$g1" "$H3B")" = 1 ] \
     && [ "$(block_supply_count "$g1" "$H1")" = 1 ] \
     && [ "$(block_supply_count "$g1" "$H2")" = 1 ]; then ok=1; else ok=0; fi
  st "[6] 块3 标题改名被检出，且块1/块2 不受影响" "$ok"

  g2="$(new_tmp)"
  cp "$fx6" "$g2"
  append_line "$g2" "$H2" '   - **供给子包**：由 `SearchIndexPack` 供给；'
  if [ "$(block_supply_count "$g2" "$H2")" = 2 ] \
     && [ "$(block_supply_count "$g2" "$H1")" = 1 ] \
     && [ "$(block_supply_count "$g2" "$H3")" = 1 ]; then ok=1; else ok=0; fi
  st "[6] 块2 内重复供给被检出，且相邻块不受影响" "$ok"

  # ---- [7] R5 新增原语：append_gap_line / append_suffix ----
  fx7a="$(new_tmp)"
  mkfixture "$fx7a" 'one' 'two' 'three'
  if append_gap_line "$fx7a" 'two' 'gap-target' \
     && [ "$(total_lines "$fx7a")" = 5 ] \
     && [ "$(LC_ALL=C awk 'NR == 2' "$fx7a")" = 'two' ] \
     && [ "$(LC_ALL=C awk 'NR == 3' "$fx7a")" = '' ] \
     && [ "$(LC_ALL=C awk 'NR == 4' "$fx7a")" = 'gap-target' ] \
     && [ "$(LC_ALL=C awk 'NR == 5' "$fx7a")" = 'three' ] \
     && [ "$(line_count "$fx7a" 'gap-target')" = 1 ]; then ok=1; else ok=0; fi
  st "[7] append_gap_line 在 anchor 后恰插入「空行 + 目标行」且总行数 +2" "$ok"

  fx7b="$(new_tmp)"
  mkfixture "$fx7b" 'one' 'two'
  if append_gap_line "$fx7b" 'NOPE-ANCHOR-§-不存在的行' 'gap-target'; then ok=0; else ok=1; fi
  [ "$(total_lines "$fx7b")" = 2 ] || ok=0
  [ "$(line_count "$fx7b" 'gap-target')" = 0 ] || ok=0
  st "[7] append_gap_line anchor 缺失 -> 失败" "$ok"

  fx7c="$(new_tmp)"
  mkfixture "$fx7c" '| `k` | v |' 'other'
  if append_suffix "$fx7c" '| `k` | v |' ' 冲突附加值 |' \
     && [ "$(line_count "$fx7c" '| `k` | v | 冲突附加值 |')" = 1 ] \
     && [ "$(line_count "$fx7c" '| `k` | v |')" = 0 ] \
     && [ "$(total_lines "$fx7c")" = 2 ]; then ok=1; else ok=0; fi
  st "[7] append_suffix 结果恰为 anchor+suffix 且原行消失" "$ok"

  fx7d="$(new_tmp)"
  mkfixture "$fx7d" 'dup' 'dup' 'other'
  if append_suffix "$fx7d" 'dup' ' X'; then ok=0; else ok=1; fi
  [ "$(line_count "$fx7d" 'dup')" = 2 ] || ok=0
  [ "$(line_count "$fx7d" 'dup X')" = 0 ] || ok=0
  st "[7] append_suffix anchor 命中 2 次 -> 失败" "$ok"

  printf '\nSELFTEST: %d/%d\n' "$ST_PASS" "$ST_TOTAL"
  if [ "$ST_PASS" = "$ST_TOTAL" ]; then return 0; else return 1; fi
}

# ============================ 入口 ============================
usage() {
  printf 'usage: bash %s {d07|t07|t08|all|selftest}\n' "$0"
}

main() {
  case "${1:-}" in
    d07) run_group d07 34 ;;
    t07) run_group t07 28 ;;
    t08) run_group t08 47 ;;
    all) run_group d07 34; run_group t07 28; run_group t08 47 ;;
    selftest) run_selftest; return $? ;;
    help|-h|--help) usage; return 0 ;;
    *) usage >&2; return 2 ;;
  esac
  printf '\nMUTATIONS: %d/%d rejected\n' "$G_PASS" "$G_TOTAL"
  if [ "$G_PASS" = "$G_TOTAL" ]; then return 0; else return 1; fi
}

main "${1:-}"
exit $?
