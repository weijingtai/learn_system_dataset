# impl-07：M7 Incremental Knowledge Assembly（§15）

状态：`READY_FOR_REVIEW（创世薄切片）`（W5-L0 定稿 2026-09-13，依 `G7-RULINGS.md` §1 P1–P9、§5 impl-07、§9.12 第 61 条；未经实现；派发前置见 `ACT.yaml` 的 `preconditions` 与 `PROMPT-L0.md`；完整增量汇编的原始条目保留在 §4 与 §6–§8，标 `DEFERRED`）

## 0. 首切片：创世汇编（W5-L0）

### 0.1 范围与分期

依 `G7-RULINGS.md` §9.12 第 61 条：`CanonicalKnowledgeSnapshot` 按规格 §6.2:153-175 归 M7；把 M7 的**创世汇编**提前为独立薄切片，作为 impl-07 的执行组 `G0` 先行定稿与实现（impl-06 已删除其 Snapshot 直通 ACT 10）。

本切片只做一件事：

```text
空基底（无既有 CanonicalKnowledgeSnapshot）
+ 单个 ReviewedEditionPackage（M6 产出，§6.2:155、§14:631）
→ CanonicalKnowledgeSnapshot 修订（§6.2:165）
```

- **做**：
  1. `pipeline/assembly/` 的纯函数创世汇编：空基底、单 Edition 视图、全部自动裁定（无人工提案）；
  2. 最小 Ledger 事务：ReleaseRun + 一个 `assemble` StepRun，封存 `canonical_snapshot` 主内容与 `assembly_package` 阶段包（§17:836）；
  3. 独立创世 Gate（不 import 汇编逻辑，自行重算身份与保真）；
  4. `openspec/acceptance/m7-assembler.sh`（§19.0:911 判据；本切片返回非 0，见 §0.2）。
- **不做（保持 `DEFERRED`，见 `ACT.yaml` 的 `deferred_acts`）**：多 Edition 对勘（`§15:655` Alignment/VariantReading/Addition/Omission）、非空基线的合并/别名/冲突提案（R03b–R03g、R06 `unify`、R10）、跨 Release 保号与 IdentityDelta（§6.3）、M6 返工替换（D-14）、§20.5（`:941`）接线 `run_all.sh`（Q29 采纳 C，`G7-RULINGS §5`）。
- **为什么提前**：首纵切（P1）之后的下一波需要 Snapshot 作为 M8 知识链前三段与 GraphProjectionPack 的输入（`§16:661-662`、`§16:725`）；Snapshot 归 M7，M6/M8 不得承担 M7 职责，避免日后拆除临时实现（第 61 条）。

### 0.2 完成判据（本切片的唯一「做完」定义）

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/assembly/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"   # OK（用例数 ≥ TDD.md §1 阈值）
bash openspec/acceptance/m7-assembler.sh; echo exit=$?
# 期望：全部已实现判据 PASS + 全部 DEFERRED 项 BLOCKED；末行 SUMMARY pass=<N> fail=0 blocked=<M>；exit=2
bash openspec/acceptance/run_all.sh | tail -1   # 与开工基线逐字相同（本切片不改 run_all.sh；20.5 仍 BLOCKED）
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?   # 与开工基线相同
git diff --check
```

`<N>`/`<M>` 在 ACT G0-05 固定；用例阈值等于具名用例累计。本切片无 FAIL、有 BLOCKED（增量项未实现），故 exit 2 —— 与 impl-02 `semantic_layer`、impl-05 `m4-stage-gate.sh` 先例一致（`impl-02-corpus/README.md:34`）。

### 0.3 上游契约：M6 ReviewedEditionPackage（只认 succeeded，P5）

M7 只经 Ledger 冻结修订读取（`§17:826-836`），解析上游时**只接受所属 StepRun `succeeded` 的包**（P5；`INTERFACES.md:24`【I-13】）。生产代码不读 fixture、不读工作目录「最新文件」（`§7:207`）。

| 来源 | 定位 | artifact_type | M7 读取字段 | 约束 |
|---|---|---|---|---|
| M6 | 调用方显式传入的 `reviewed_package_revision_ids` | `stage_package`（`pkg_m6_`） | `stage=="m6"`、`validation.passed==true`、`manifest.output_artifacts` 中恰 1 个 `reviewed_edition_package` | 修订 `sealed`；所属 StepRun `succeeded`（P5）；M7 **不修改**其状态（`§6.2:175`） |
| M6 | 上项 `manifest.output_artifacts` 所指修订 | `reviewed_edition_package` | `reviewed_edition_revision_id`、`unresolved_count==0`、`decision_revision_ids` | `sealed` |
| M6 | `reviewed_edition_revision_id` 所指修订 | `reviewed_edition` | `edition_part_artifact_id`、`candidate_package_revision_id`、`approved[{entity_id,kind,artifact_revision_id,content_status}]`、`rejected[]`、`decisions[]`、`evidence_links[{entity_id,source_span_id,corpus_spans_revision_id,start_offset,end_offset,quote_sha256}]`、`school_views[{school_view_id,school_id,subject_entity_id,conflict_group_id,changes_current_judgment}]`、`unresolved_count==0` | `sealed`；键逐字取 `impl-06-review/README.md §5.3` |
| M4（在 M6 包冻结血缘内） | `reviewed_edition.candidate_package_revision_id` → `candidate_package.candidate_set_revision_id` | `candidate_package` / `candidate_set` | `technique_id`、`source_id`、`edition_part_artifact_id`、`assertions[]`、`patterns[]`、`school_views[]`、`concept_mentions[]`、`new_concept_candidates[]`、`counts` | m4 StepRun `succeeded`（P5）；必须出现在 m6 包的 `lineage.upstream_artifacts` |
| 调用方 | `run_m7(...)` 参数 | — | `technique_id`、`reviewed_package_revision_ids`、`base_snapshot_revision_id=None` | 显式传入，不查「最新」；本切片 `base_snapshot_revision_id` 必须为 `None`（非 None → `AssemblyRefused`，消息含「纵切后」） |

**为什么读 M4 `candidate_set`（D-0-2，主 Agent 决定）**：`impl-06` 定稿的 `reviewed_edition` 只承载审核结论（approved/rejected + `content_status`）、证据链与 SchoolView 摘要，**不含** Concept 名称、Pattern 名称/规则、Assertion 命题文本；这些内容实体在 M4 `candidate_set`。M7 经 m6 包的冻结血缘解析 `candidate_package` 属「消费 ReviewedEditionPackage 的冻结输入」，不改 impl-06 契约（P9 精神），也不让 M6 承担 M7 职责（第 61 条边界）。替代方案（要求 impl-06 在 `reviewed_edition` 内嵌内容）须改已定稿的上游契约，见 §0.7 接口需求（第 65 条）。

**`candidate_set` 的真实形状（F1，键逐字取已验收 `pipeline/knowledge_extraction/assemble.py:637-651`）**：顶层 `schema_version / technique_id / source_id / edition_part_artifact_id / evidence_level / span_layer / source_channels / assertions / patterns / school_views / concept_mentions / new_concept_candidates / rejected / disputes / counts`。要点：**assertion 无 `subject`、无 `school_view_ids`，用 `school_ids`**（`:428-442`）；**pattern 恒有合法 `pat_` 号、无 `candidate_key`**（`:484-498`）；**断言↔Pattern 关联以 `patterns[].assertion_ids` 为唯一来源**；`school_view.subject_entity_id` 解析到 `assertion_id` 或 `pattern_id`（`:560-572`）。M7 一律照此解析，不引用自造字段（合成宿主 `tests/data/genesis_package.json` 同此形状）。

### 0.4 下游契约：M8 知识链前三段与 GraphProjectionPack 所需 Snapshot 字段

M8 冻结输入第 1 项为 CanonicalKnowledgeSnapshot Revision（`§16:661-662`）；GraphProjectionPack 与移动端数据必须与 Snapshot 共享 `release_id`、`canonical_hash`、实体 ID 与关系 ID（`§16:725`）。本切片 Snapshot 内容形状（`schema_version: "0.1.0-draft"`，P3）：

```text
{ schema_version: "0.1.0-draft",
  knowledge: {
    technique_id,
    id_allocation {"pat_<technique>": <int>} | {},      # 新发号时的历史最高号
    id_range {"pat_<technique>": [<start>, <end>]},     # 第 64 条：本 Run 配置修订登记的号段
    allocated_pattern_ids [],                           # 第 64 条：本次补发清单（升序）
    retired_entity_ids [],                              # 创世恒空
    editions [{source_id, work_key, reviewed_edition_package_revision_id,
               reviewed_edition_revision_id, stage_package_id,
               edition_part_artifact_ids, edition_complete}],
    concepts [{concept_id, name, aliases, provenance[{source_id, content_sha256, content_status}]}],
    patterns [{pattern_id, concept_id|null, name, aliases, rules[{rule_key, ast_sha256, source_id}],
               assertion_ids, school_view_ids, recognition_rule_status, provenance[...]}],
    assertions [{assertion_id, subject_entity_id, source_id, proposition, collation_key|null,
                 text_sha256, source_span_ids, evidence[{source_span_id, start_offset, end_offset, quote_sha256}],
                 school_view_ids, content_status}],
    school_views [{school_view_id, school_id, subject_entity_id, conflict_group_id,
                   source_conflict_group_id, claim_refs, changes_current_judgment, content_status}],
    conflict_groups [{conflict_group_id, member_school_view_ids, first_layer_display, resolutions[]}],
    relations [] },                                     # 创世恒空（无对勘、无 attach、无 alias）
  meta {snapshot_artifact_id, base_snapshot_revision_id: null, release_scope_id, processing_run_id,
        step_run_id, assembly_seq, knowledge_sha256, canonical_hash, decision_refs: {}} }
```

对 M8 的映射（只写接口需求，不改 impl-04）：

| M8 消费项 | Snapshot 字段 | 说明 |
|---|---|---|
| `KnowledgeEntry.subject_entity_id` | `patterns[].pattern_id` / `concepts[].concept_id` | 本切片 Pattern 可无 `concept_id`（见 §0.7 接口需求） |
| `KnowledgeEntry.title` | `patterns[].name` / `concepts[].name` | |
| `KnowledgeEntry.assertion_ids` / `school_view_ids` | `patterns[].assertion_ids` / `patterns[].school_view_ids` | |
| `Assertion` | `assertions[]{assertion_id, proposition, subject_entity_id, school_view_ids, source_span_ids, content_status}` | `proposition` 为本切片相对草稿 §5.2 新增；`subject_entity_id` 由 `patterns[].assertion_ids` 反查（恰 1 个 → 该 `pat_`，多个 → 字典序最小，零个 → null，F1）；`school_view_ids` 由 `school_views[].subject_entity_id` / `claim_refs` 反解（F1） |
| `EvidenceLink` | `assertions[].evidence[]{source_span_id, start_offset, end_offset, quote_sha256}` | 坐标与 M3 `corpus_spans` 同源（`INTERFACES.md:410`【I-11】） |
| `school_ids` | 经 `assertions[].school_view_ids` → `school_views[].school_id` | |
| Graph 节点 / 边 | `patterns` / `concepts` / `assertions` / `school_views` 的稳定号 + `relations[]` + `conflict_groups` 成员 | 本切片 `relations` 为空，Graph 只有 subject 边与冲突组成员边 |
| `canonical_hash` | `meta.canonical_hash` | `canonical_hash = sha256(canonical_json({concepts, patterns, assertions, school_views, conflict_groups}))`（草稿 §3.7） |
| `release_id` | 由 M8 补齐 | M7 只给 `meta.release_scope_id` |
| `IdentityMigrationMap` | M7 `identity_delta`（本切片不产出，`DEFERRED`） | 创世无基线，无身份迁移 |

`knowledge_sha256 = sha256(canonical_json(knowledge))`；`meta` 含运行随机值，`knowledge` 可与金标逐字节比对（草稿 §5.2）。M7 不合成、不升级内容成熟度：`content_status` 逐来源保留，由 M8 按消费级别过滤（`§16.1:670-678`）。

### 0.5 主 Agent 决定（执行者不重议）

裁决来源：`G7-RULINGS.md` §1 P1–P9、§5 impl-07、§9.12 第 61 条、**§9.13 第 63–66 条（R1–R4 裁定）**。**未单列的细节默认采纳原草稿推荐**；与已落地 impl-05/impl-06 契约冲突处以已落地契约为准。

- **D-0-1｜Q17 首切片里 Snapshot 从哪来 → 第 61 条定案**。Snapshot 归 M7，创世汇编薄切片提前先行；M8 不自带薄适配器、不直接消费 ReviewedEditionPackage。M6 删除 ACT 10；依赖 Snapshot 的验收项在 M7 落地前恒 BLOCKED。
- **D-0-2｜M7 经 M6 冻结血缘读 M4 `candidate_set` 取内容实体**（见 §0.3）。零 impl-06 改动。
- **D-0-3｜Q27 新 artifact_type → P2，只在已登记名内取用、不新增类型名**。本切片使用 `canonical_snapshot`（主内容）+ `assembly_package`（阶段输出索引）——两者已在 `INTERFACES.md §4` M7 行出现；提案并入 `assembly_package` 与报告，不另立提案 Artifact（完整波的提案类型 `DEFERRED`）。内容结构以代码草案表达（P3），`schema_version: "0.1.0-draft"`；`PUBLIC_RELEASE` 以 `draft_schema` 拒绝。
- **D-0-4｜ReleaseRun scope 键 → `edition_part_artifact_id`**。创世输入为单 Part 的 `reviewed_edition`（impl-06 §5.3），故 `create_processing_run("release_run", edition_part_artifact_id)`，与 `G7-RULINGS §9` 第 4 条（单 Part 取该 Part）一致；跨 Part/多 Edition 的配置 Artifact 键（草稿 D-02 推荐 A）`DEFERRED`。
- **D-0-5｜Q29/§20.5 → 采纳 C（`G7-RULINGS §5`）**。本切片不改 `openspec/acceptance/run_all.sh`；`m7-assembler.sh` 存在并经 ACT 判定，但 20.5 维持 BLOCKED，接线留待 W5 另裁。
- **D-0-6｜Q22 自动/人工边界 → 本切片只走自动分支**。空基底 → 只有 admit_new 与保留号（R02/R03e/R04/R05 + 冲突组原样保留），无人工提案、无 `awaiting_human`；完整规则表（R03b–R03g、R06 `unify`、R07–R10）`DEFERRED`。
- **D-0-7｜Q32 Checkpoint 粒度 → 非人工 task 落盘**。本切片 task 为 `propose_r1`、`seal_snapshot` 两个 Checkpoint；同阶段后续运行经 `supersede_step_run` 续写（第 58 条）。
- **D-0-8｜Q31 基底状态与并发 → 创世无基底**，不调用 `supersede_revision`；同一 Part 的第二个同阶段运行经 `supersede_step_run`（第 58 条）。
- **D-0-9｜Q26 fixture → 本切片不自建共享 fixture**。M6 未实现且共享 fixture 属 impl-00 独占写权（P4），故创世验收宿主用包内非生产 `fixture_seed.py` + `tests/data/` 的合成 `reviewed_edition`（标 `synthetic: true`，§9.7 第 52 条口径），只写临时 Ledger；草稿 `mini_release01`（ACT 00–01）随完整波次 `DEFERRED`，见 §0.5 D-0-15。
- **D-0-10｜Q25 人工决定 decision_type → 本切片无人工决定**，不产出 `human_event`；完整波的 `decision_type` 映射随人工回路 `DEFERRED`。
- **D-0-11｜写范围零交集**。G0 只写 `pipeline/assembly/**` 与 `openspec/acceptance/m7-assembler.sh`；与 `pipeline/review/`、`pipeline/dataset_compiler/`、`pipeline/orchestrator/` 零交集；不写 `run_all.sh`、`pipeline/ledger/**`、`openspec/schemas/**`、fixture。
- **D-0-12｜R1 Snapshot 粒度与身份 → 第 63 条（采纳 R1 推荐 A）**。每个 technique 一个 CanonicalKnowledgeSnapshot Artifact（`§6.2:165`、`§16:699`），后续 Release 以新修订续写；创世无基底 → 新建 `art_` + 首个 `rev_`（无 `prev_revision_id`）。
- **D-0-13｜R2 Pattern 身份发号 → 第 64 条（采纳 R2 推荐 B，附确定性取号约束）**。保留 M4 已发 `pat_`；仅对 `pattern_id: null` 的候选补发；补发**只从配置修订登记的 `id_range` 确定性取号**（在号段内跳过已被保留号占用的值），不新增前缀（P8）；号段与补发清单写入 Snapshot 修订的 `knowledge.id_range` 与 `knowledge.allocated_pattern_ids`（并同步 `assembly_package`）。
- **D-0-14｜R3 M4/M6 内容缺口 → 第 65 条（采纳 R3 推荐 A）**。创世薄切片缩水，知识链按 `pat_` 聚合；缺口登记为对 M4/M6 的接口需求（§0.7），不在 M7 内补造内容。
- **D-0-15｜R4 创世验收宿主 → 第 66 条（采纳 R4 推荐 A，附条件）**。用包内合成宿主（`pipeline/assembly/tests/data/`），不改共享 fixture（P4）。附条件：合成输入中的人工决定须标 `synthetic_fixture: true`（同第 52 条）且不计 `expert_verified`（补具名用例断言）；「消费真实 M6 产出」验收项在 impl-06 实现并验收前判 BLOCKED。

### 0.6 原待裁决 R1–R4 → 已由第 63–66 条裁定

> 原 §0.6 的 R1–R4（Snapshot 粒度与身份、Pattern 身份发号、M4/M6 内容缺口、创世验收宿主）已由 `G7-RULINGS.md` §9.13 第 63–66 条裁定，要点逐字移入 §0.5 D-0-12～D-0-15；此处不再保留待裁内容。缺口对应的接口需求见 §0.7。

### 0.7 接口需求（对 M4/M6；第 65 条）

以下为创世薄切片暴露、需由 M4/M6 负责方在完整波次补齐的接口需求。**本切片不在 M7 内补造内容**；登记入 `INTERFACES.md` §2.4/§2.6 卡片的「接口需求」（由 impl-00 后续登记 ACT 或 M4/M6 负责方执行，本包不写该文件）：

1. **`candidate_set.concepts[]`**（M4）：当前只有 `concept_mentions[]`（已绑定 `concept_ref`）与无号 `new_concept_candidates[]`，无正式 Concept 对象（名称/别名/规范面）。需求：M4 产出 `concepts[{concept_id, name, aliases[], content_status}]`，使 Snapshot `concepts[].name/aliases` 有权威来源；在此之前 M7 由已绑定 `concept_mentions` 按 `concept_ref` 聚合（`name` 取 surface 升序首个，其余入 `aliases`）。
2. **`candidate_set.patterns[].concept_id` / `aliases`**（M4）：当前候选 Pattern 无该绑定、无别名（`assemble.py:485-498`）。需求：M4 给出 `concept_id`（可为 null）与 `aliases[]`。在此之前 Snapshot `patterns[].concept_id = null`、`patterns[].aliases = []`，M8 `KnowledgeEntry.subject_entity_id` 按 `pat_` 聚合。
3. **`candidate_set.patterns[].rules[]`**（M4）：当前 `recognition_rule_status = not_captured`，无 `{rule_key, ast_sha256}`。需求：M4 补规则 AST 与哈希。在此之前 Snapshot `patterns[].rules = []` 且 `recognition_rule_status = "not_captured"`（`§20.6:942`：`not_captured` 不得误判为不存在）。
4. **`reviewed_edition` 内容内嵌与否**（M6，可选）：本切片经 m6 冻结血缘读 M4 `candidate_set`（D-0-2），M6 契约保持不变。若后续要求 `reviewed_edition` 自包含内容实体，须经另立契约变更 ACT，并同步 M7 上游解析（§0.3）。
5. **无号 Pattern 候选的稳定键**（M4，防御）：impl-05 已验收代码**恒为每个 pattern 发 `pat_` 号**（`assemble.py:484`），不产出 `pattern_id: null` 的候选，也无 `candidate_key`。故 M7 的 R03e（`pattern_id` 为 null → 从 `id_range` 补发）在当前上游下**不出现**，仅作防御分支保留：若未来 M4 引入无号候选，必须同时提供稳定 `candidate_key`（否则 M7 以 `SCH_001` 拒绝）。本条与第 64/65 条一致。

## 0.8 待主 Agent 裁决

（无。R1–R4 已由 `G7-RULINGS.md` §9.13 第 63–66 条裁定，见 §0.5 D-0-12～D-0-15。）

## 1. 目标（完整增量汇编，DEFERRED）

> 以下 §1–§8 为完整增量汇编的原始草稿内容，**不在创世薄切片内**，保留备查并标 `DEFERRED`；其原始待裁决条目见 §4，执行分组见 `ACT.yaml` 的 `deferred_groups`。创世薄切片的范围、决定与裁决见 §0。

### 1.1 分期核实：M7 在首纵切之外

- 规格 §19 主表 M7 行分期为「首纵切后」（`openspec/learn-system-blackbox-architecture.md:881`）。
- §22.2 纵切终点链路为 M2 → M3 → M4 → M5 → M8，不经过 M6、M7（`:974-984`）。
- §22.3「阶段 2 纵切后」明列关闭 M7 差距（`:992`）；§22.4 首纵切内硬上限 4 行，只有 Ledger/M3/M5/M8（`:997`）。
- PLAN 节 C 登记 M7 为「首纵切后」，判据是 `run_all.sh 20.5` 由 BLOCKED 变 PASS（`PLAN.md:94`）。

结论：本包是**纵切后第一批**。它按「可并行实现」的粒度起草：输入不是真实 M4–M6 产物（尚不存在），而是新规范 fixture 中的**金标 ReviewedEdition 知识视图**和由它们推出的**多版本 CanonicalKnowledgeSnapshot 金标**（见 §4 D-10）。

### 1.2 派发前必须 ACCEPTED 或拍板的前置

| 前置 | 当前 | 为什么是前置 |
|---|---|---|
| impl-01 Artifact Ledger | `ACCEPTED` | M7 只经 Ledger 读写（§17 `:836`） |
| §4 D-01～D-18 主 Agent 裁决 | 待裁决 | 身份发号、scope 键、fixture、artifact_type 都悬而未决，执行者无法写出唯一实现 |
| ACT 00–01 fixture `mini_release01`（F 组） | 未开始 | J 组所有金标用例的比对基准；必须由非 J 组 Agent 产出并经主 Agent 手工核对 |
| mini_ed01 `spans.yaml` 金标（sha256 `ec6d77b9…44ef`） | 已冻结 | ed01 知识视图的 `source_span_ids` 锚定这些真实 Span |

**不是**实现前置（可并行）：impl-02 M3 返工、M4/M5/M6 实现、M8 实现。但真实 M6 未产出 ReviewedEditionPackage 前，`m7-assembler.sh` 固定保留一行 `BLOCKED upstream_m6_real`，所以只能返回 2，不能返回 0（同 impl-02 `semantic_layer` 先例，`impl-02-corpus/README.md:34`）。

### 1.3 本批要做的事

在 `pipeline/assembly/` 落地 §15 与 §6.2 的 M7：

1. 读取 ReleaseRun 冻结输入（基底 Snapshot 修订 + 一个或多个 m6 StagePackage 修订），确定性产出四类提案（Merge/Alias/Conflict/EvidenceRelation）；
2. 能自动裁定的直接裁定；不能的进入 `awaiting_human`，由 Review Console（M7 模式）写回人工事件；恢复后回流，只重算受影响提案；
3. 封存新 Snapshot 修订（同一 Artifact 的新 `rev_`，基底修订转 `superseded`）、对勘集（Alignment/VariantReading/Addition/Omission）、IdentityDelta、汇编报告与 m7 StagePackage；
4. 以不 import 汇编逻辑的独立 Gate 判定身份保号、无静默折叠、增量范围正确、增量等于全量；
5. 新建 §19.0 已登记的判据脚本 `openspec/acceptance/m7-assembler.sh`（`:911`），并按 D-13 裁决决定是否接线 `run_all.sh 20.5`。

### 1.4 完成判据（完整波次，DEFERRED；创世薄切片的完成判据见 §0.2）

```bash
export LC_ALL=en_US.UTF-8
bash openspec/acceptance/m7-assembler.sh; echo exit=$?
# 期望：13 行 PASS + 1 行 BLOCKED upstream_m6_real + SUMMARY pass=13 fail=0 blocked=1；exit=2
bash openspec/acceptance/run_all.sh 20.5
# 期望（按 D-13 推荐项 A 接线后）：BLOCKED  20.5  前置缺失: M6 Review Workbench；ReviewedEditionPackage 由 mini_release01 金标视图代替
bash openspec/acceptance/run_all.sh | tail -1
# 期望：SUMMARY pass=2 fail=1 blocked=8（20.5 仍 BLOCKED，只是原因从 M7 收窄到 M6；若 D-13 选 B 则 pass=3 blocked=7）
.venv/bin/python -m unittest discover -s pipeline/assembly/tests -t . 2>&1 | tail -1   # OK
```

## 2. 依据（只读来源，文件:行号）

规格 `openspec/learn-system-blackbox-architecture.md`：

| 位置 | 用途 |
|---|---|
| `:37`（§2.7） | 修订不可覆盖；`entity_id` 跨修订稳定必须复用 |
| `:40`（§2.10） | 模型输出只能成为候选；M7 不调用模型 |
| `:55`（§3） | 版本间用 Alignment/VariantReading/Addition/Omission 表达 |
| `:77`（§4） | `not_captured` 不得解释为不存在（对勘「不可比」同理） |
| `:86`（§4） | M7 汇编 Concept、Pattern、Assertion 及其关系 |
| `:119-124`（§5） | PendingQueue 第 5 个专用队列「M7 待裁决」 |
| `:130`（§5） | Review Console M7 模式；人工决定归属发起队列的 Run/StepRun/Stage |
| `:151`（§6.1） | Part 级结果可进入内部验收或开发检索包 |
| `:153-175`（§6.2） | ReleaseRun 流程、M7 位置、裁决归属、不改已封存 ReviewedEditionPackage |
| `:207`（§7） | 只读冻结 Artifact，不读「最新文件」 |
| `:211-220`（§7.1） | 一个 StepRun 覆盖任务及其整个人工队列；`resume_token` 语义 |
| `:257-267`（§8.1） | 业务身份与物理修订分离；合并/拆分取新号；删除永久退役；IdentityMigrationMap |
| `:298`（§8.1） | `pkg_m7_` |
| `:316-318`（§8.1 3b） | `cg_`（M4/M7 产出）、`pat_`（M4 候选、M7 聚合后正式）、`ent_` |
| `:349-364`（§8.2） | ReviewDecision 8 类闭集 |
| `:382-404`（§8.2） | Artifact status 迁移（`sealed → superseded`） |
| `:570`（§12.2） | SchoolView 字段；M4 与 M7 不得以默认流派静默折叠；`changes_current_judgment` |
| `:625`（§14） | M7 模式输出归属 ReleaseRun 的合并 ReviewDecision |
| `:631`（§14） | ReviewedEditionPackage 内容 |
| `:635-645`（§14.1） | 精确失效传播：内容哈希等价自动继承、变化降级待复核、禁止整 Edition 失效 |
| `:647-655`（§15） | M7 全文 |
| `:662`（§16） | M8 冻结输入第 1 项为 CanonicalKnowledgeSnapshot Revision |
| `:699`（§16） | 建议一个 Technique 一个 Release |
| `:725`（§16） | Graph 与移动端数据来自同一 Snapshot |
| `:727-734`（§16） | AnchorContractPack、稳定性等级、IdentityMigrationMap `change_type` 闭集与 `reason_ref` |
| `:736`（§16） | 冲突组首层展示由包内标记，客户端不推导 |
| `:815`（§16.3.2） | 「是否改变当前判断」由 M4/M7/M6 供给 |
| `:834-836`（§17） | Artifact 必记字段与事务序列 |
| `:842-845`（§17.1） | Checkpoint 链与落盘粒度（人工阶段列表未含 M7） |
| `:854-859`（§18） | KnowledgeGraph 含 `anchor_migration` 边；重要关系必须有稳定键与来源 |
| `:881`、`:911`（§19/§19.0） | M7 差距行与 `m7-assembler.sh` 判据 |
| `:935`、`:941`（§20） | 统一验收宿主；20.5 条文 |
| `:974-1000`（§22） | 纵切链路、分期表、取舍理由 |

其他：

- `openspec/id-prefix-registry.md:52`（`cg_` 生产者 M4/M7）、`:60`（`pat_` 语义与发号）、`:61`（`ent_` 由 M8 发）、`:93-96`（只引用已登记前缀；新增流程）。
- `openspec/schemas/stage_package.schema.json:271-285`（`pkg_m7_` 分支）；`artifact_ref.schema.json`；`step_request/step_result.schema.json`。
- `pipeline/ledger/service.py`：`create_processing_run` `:319-345`（kind ∈ edition_run/release_run，`edition_part_id` 必须是 `art_`）；`put_artifact` `:442`（`prev_revision_id` 续同一 Artifact）；`put_run_artifact` `:528-597`（只允许 configuration/technique_profile）；`supersede_revision` `:678-716`；`register_stage_package` `:718`；`await_human` `:885`；`record_human_event` `:922-960`（artifact_type 必须 `human_event`，`decision_type` 可为 None）；`resume` `:965`；`_write_checkpoint_locked` `:1242`，`:1280-1285` 同一 (edition_part_id, stage) 已被 succeeded StepRun 封存后拒绝续写。
- `pipeline/ledger/store.py:78-86`（`processing_runs.edition_part_id NOT NULL`）、`:168-179`（`stage_checkpoints`）。
- `pipeline/ledger/ids.py:13-33`（19 个前缀家族正则）。
- `openspec/acceptance/run_all.sh:232-234`（20.5 当前恒 BLOCKED「M7 Incremental Assembly」）。
- 模板：`docs/blackbox-spec-rework/work-items/impl-02-corpus/`（事务模板 `act/03.yaml`，验收脚本模板 `act/04.yaml`）。
- fixture：`pipeline/corpus/_fixture/mini_ed01/spans.yaml`、`manifest.yaml`、`verify.sh`（只读）。

## 3. 范围（完整增量汇编，DEFERRED）

> 创世薄切片的写范围见 §0 与 `ACT.yaml` 的 G0：只写 `pipeline/assembly/**` 与 `openspec/acceptance/m7-assembler.sh`。以下为完整波次的写范围，`DEFERRED`。

写（落地后）：

- `pipeline/corpus/_fixture/mini_release01/**`（新建；ACT 00–01，F 组；须 D-10 选 A）
- `pipeline/assembly/**`（新建；ACT 02–09）
- `openspec/acceptance/m7-assembler.sh`（新建；ACT 09）
- `openspec/acceptance/run_all.sh` 仅 `20.5)` 分支（ACT 10；须 D-13 选 A 或 B 且主 Agent 书面授权）

禁止：

- 改规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、`pipeline/corpus/_fixture/mini_ed01/**`、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`PLAN.md`、`SUBAGENT_TODO.md`、`HANDOFF.md`、其他 work-items；
- 新增依赖（只用标准库 + PyYAML + jsonschema）；新增 ID 前缀；把提案键、对勘键、候选键写成任何已登记前缀形态；
- 生产代码读 fixture 路径或工作目录文件（只读 Ledger 冻结修订；`fixture_seed.py` 与 `acceptance.py` 除外，且只经 `--fixture` 参数）；
- 调用任何模型 API；做模糊文本相似度匹配；
- 修改或封存状态迁移任何 m6 StagePackage / `reviewed_edition_knowledge` 修订（§6.2 `:175`）；
- 读取其他 ReleaseRun 的人工决定（§6.2 `:173`）；
- M7 发 `ent_`、`rel_`（属 M8）；M7 合成或升级内容成熟度状态（§8.2 `:440`）。

## 4. 待主 Agent 裁决（完整增量汇编的原始条目，DEFERRED）

> **创世薄切片的决定见 §0.5（含 R1–R4 的第 63–66 条裁定），接口需求见 §0.7；§0.8 无待裁决项。** 以下 D-01～D-18 是完整增量汇编的原始草稿条目，保留备查；其多数已被 §0.5 的决定覆盖（Q17/Q19/Q20/Q26/Q27/Q29/Q22/Q25/Q31/Q32 见 §0.5 D-0-1～D-0-15），未覆盖部分随完整波次再议。推荐不等于定案。

### D-01 首纵切里 M8 的 Snapshot 从哪来

矛盾：§16 `:662` 规定 M8 冻结输入第 1 项是 CanonicalKnowledgeSnapshot Revision；§22.2 `:974-984` 纵切链路没有 M7，§22.3 `:991` 也没把 M7 列为「薄用」。

- A：把本包 ACT 02–04 的纯函数「创世汇编」（空基底 + 单个 ReviewedEdition 视图，全部自动裁定）作为 M8 的最薄前置提前交付；§19 M7 行分期不变，`m7-assembler.sh` 仍非 0。
- B：M8 草案自带薄适配器，把单个 ReviewedEditionPackage 投影成 Snapshot；M7 落地后替换。
- C：纵切中 M8 直接消费 ReviewedEditionPackage，规格 §16 `:662` 加注例外。

**推荐 A**：Snapshot 投影规则只有一份，避免 M7 落地后出现两个 Snapshot 生成器并存与字节差异；创世汇编只用到 R01/R02/R04 的自动分支，工作量小。

### D-02 ReleaseRun 在 Ledger 里的 scope 键

事实：`processing_runs.edition_part_id NOT NULL`（`store.py:81`），`create_processing_run` 要求 `art_` 格式（`service.py:327`）；Checkpoint 链以 (edition_part_id, stage) 为键，已被 succeeded StepRun 封存后拒绝续写（`service.py:1280-1285`）。ReleaseRun 跨多个 Edition，没有单一 EditionPart。

- A：每个 ReleaseRun 先 `new_id("artifact_id")` 得 X，`create_processing_run("release_run", X, technique_id)`，再 `put_run_artifact("configuration", artifact_id=X)`；X 即本次 M7 配置 Artifact 的身份，也是 Checkpoint 链键。不改 Ledger。
- B：改 Ledger Schema，新增 `release_scope_id` 列或允许 NULL（触及已 ACCEPTED 的 impl-01，需另开工作包）。
- C：以 Snapshot 的 `art_` 作键——第二个 ReleaseRun 写 m7 Checkpoint 会被 `:1280` 拒绝，除非滥用 `supersede_step_run`。

**推荐 A**：零 Ledger 改动；键有真实 Artifact 行支撑，不是悬空 ID；每个 ReleaseRun 独占一条 m7 Checkpoint 链，符合 §17.1 `:842`。

### D-03 Snapshot 的粒度与身份

- A：每个 technique 一个 Snapshot Artifact（`art_` 稳定），每次汇编写新 `rev_`，`prev_revision_id` 指向基底修订。
- B：每个 Work 一个 Snapshot。
- C：每次 Release 新建一个 Snapshot Artifact。

**推荐 A**：`pat_` 按技法命名空间（§8.1 `:317`），同一格局可跨 Work 聚合；§16 `:699` 建议一个 Technique 一个 Release；§6.2 `:165` 与 §15 `:651` 用词是「新 Snapshot Revision」，即同一对象的新修订。

### D-04 Pattern 身份谁发号

冲突点：登记册 `:60` 写「M4 产出候选，M7 跨 Edition 聚合后正式；Contract Registry 登记」，但 Contract Registry（L2'）是首纵切后才实现（`:885`）。若每个 EditionRun 自行发 `pat_`，同一格局每加一版就会产生新号。

- A：M4/M6 只能携带已正式的 `pat_`（在基底 Snapshot 中存在）或不带号的 `candidate_key`；M7 在「admit_new」获批（自动或人工）时发号，号 = 该技法命名空间历史最大号（含已退役）+ 1，写入 Snapshot `id_allocation`；Contract Registry 落地前 Snapshot 即登记来源。`as_`/`co_` 由 M4 在技法命名空间全局唯一发号，M7 不发，只做碰撞检测（`ID_002` fail-closed）；仅人工 `merge_entities`/`split` 时 M7 为 Pattern/Concept 发新号。
- B：每个 EditionRun 的 M4 自行发 `pat_`，M7 合并时换新号并写 `merged`——同一格局随版本增加反复换号，直接违反 §20.5「不改旧身份」`:941`。
- C：等 Contract Registry 先落地再做 M7（本包整体顺延）。

**推荐 A**。

### D-05 「并入」与「合并」必须是两种语义

冲突点：§8.1 `:267` 规定合并必须取新 `entity_id`；§15 `:653` 的 MergeProposal 若按字面理解为「合并」，则每个跨 Edition 的同一格局都要换号。

- A：`MergeProposal.relation` 闭集 `{attach, admit_new, merge_entities}`。`attach`＝新版候选并入既有正式对象（保号，只增 provenance/规则/断言）；`admit_new`＝无可比对象，新建正式对象；只有 `merge_entities`（两个既有正式对象合一）取新号并写 IdentityDelta `merged`。
- B：所有跨 Edition 同一格局都视作合并换号（违反 §20.5）。
- C：`attach` 不经提案、直接静默并入（违反「提案、差异和决定全部保留」`:653`）。

**推荐 A**。

### D-06 自动裁定与人工裁决的边界

§6.2 `:161-162` 写「可自动裁定的提案直接进入封存队列」，但没有定义可自动裁定的标准。

- A（规则表见 §6.1）：只有结构性等价才自动——`pat_` 已绑定且 concept 一致；名称与规则 AST 哈希**同时**唯一命中同一对象；无任何命中时 admit_new；对勘键两侧均声明时的 Alignment/VariantReading/Addition/Omission；Assertion 被 M6 返工删除时退役。其余（同名异规则、异名同规则、多重命中、概念绑定不一致、同主体跨版冲突组、Pattern/Concept 失去全部来源、依赖未决提案的候选）一律人工。
- B：名称相等即自动 attach（违反 §15 `:653` 保留同名异义）。
- C：全部人工（可行，但 §6.2 的自动通道无实现、无测试）。

**推荐 A**。

### D-07 「可比内容」如何判定

§15 `:655` 只说「仅对可比内容建立」，未定义可比。

- A：可比单元 = (work_key, `collation_key`)，两侧主体须裁决到同一正式对象，否则转人工（R07b）。每个 ReviewedEdition 视图声明 `collation_units: [{collation_key, present}]`，`present: false` 表示该版覆盖此位置但原文缺；两侧都声明才比较，任一侧未声明 → `not_comparable`（只进报告，绝不记 Omission，对应 §4 `:77`）。M7 不做文本相似度。文本差异用 NFC 后逐字比较，差异细节用标准库 `difflib.SequenceMatcher` opcodes。
- B：允许按 NFC 文本相似度阈值自动对齐（引入可调阈值，结果随阈值漂移）。
- C：本批不做对勘，只做 Pattern 聚合（§15 `:655` 与 §20.5 部分落空）。

**推荐 A**。代价：要求 M4/M6 供给 `collation_key` 与 `collation_units`（接口假设 §5.3 第 4 条）。

### D-08 对象级「所见修订」的粒度

§8.1 `:265` 要求 ReviewDecision 同时记目标 `entity_id` 与所见 `artifact_revision_id`。

- A：对象不单独入 Ledger；所见修订 = 承载该对象的包级修订（`reviewed_edition_knowledge` 或 Snapshot 修订），另记对象 `content_sha256`（规范 JSON 哈希）。
- B：每个 Pattern/Assertion/SchoolView 各是一个 Ledger Artifact 修订（上千个 Artifact，Checkpoint 与 Transformation 爆炸）。
- C：交给 M6 草案决定，M7 两种都兼容（接口不收敛）。

**推荐 A**。

### D-09 M7 人工决定的 `decision_type`

§8.2 `:349-364` 闭集 8 类，没有「身份汇编」类。

- A：对勘相关 → `review_edition_collation`；冲突组相关 → `review_school_attribution`；attach/alias/admit_new/merge_entities/split/retire → `decision_type=None`（`record_human_event` 允许，`service.py:922-927`），决定细节放事件内容 `m7_decision` 字段。
- B：规格 §8.2 新增第 9 类 `review_identity_assembly`（改闭集，需用户确认）。
- C：全部 None。

**推荐 A**。

### D-10 新规范 fixture 与期望产物

现状：M4–M8 期望产物不存在；mini_ed01 只有一个 Edition，禁止修改。

- A：新建规范 fixture `pipeline/corpus/_fixture/mini_release01/`：ed01 视图的 Span 引用锚定 mini_ed01 真实 `spans.yaml`（以其 sha256 绑定）；合成第二版次用 `src_sanche_ed99`（`ed99` 约定为合成保留号，避免与未来真实版次撞号）；合成对象号用 `pat_/as_/co_qizheng_9000NN`、`sch_qizheng_001/002`（登记册 `:54` 已列）、`sv_/cg_/art_/rev_` 用可读零填充常量（同 mini_ed01 先例）；全部内容标 `synthetic: true`、`content_status: machine_extracted`，README 声明不得作知识来源。由独立 F 组 Agent 产出，期望产物以场景表逐项字面量写出（不得实现通用汇编算法），主 Agent 手工核对。
- B：期望产物放 `pipeline/assembly/tests/data/`（不是规范宿主，`m7-assembler.sh` 无法遵守「只调用规范 verify.sh」纪律）。
- C：等真实 M4–M6 产出与真实第二版次（无限期 BLOCKED）。

**推荐 A**。需主 Agent 同时确认：`ed99` 与 `9000NN` 是约定而非新前缀；F 组与 J 组不得是同一 Agent。

### D-11 新 artifact_type

- A：新增 `reviewed_edition_knowledge`（M6 产出，需与 M6 草案对账）、`canonical_knowledge_snapshot`、`assembly_proposal_set`、`edition_collation_set`、`identity_delta`、`assembly_report`；沿用 `configuration`、`human_event`、`validation_report`、`step_log`、`failure_report`、`stage_package`、`stage_checkpoint`。
- B：全部塞进一个 `m7_output` 内容（丢失分项血缘，§18 `:857` 要求重要关系有稳定 ID 与来源）。
- C：等 Contract Registry 统一登记后再实现（L2' 未实现，阻塞）。

**推荐 A**。

### D-12 提案与对勘关系的标识

四类提案、四类对勘关系都没有登记前缀；登记册 `:93` 规定未登记前缀非法。

- A：不发登记 ID。`proposal_key = "<kind>:" + sha256(规范 JSON(主体元组))[:32]`，kind ∈ `merge|alias|conflict|evidence`；对勘关系键 `relation_key = "<relation>:" + sha256(...)[:32]`。冒号形态不匹配任何前缀家族（`ids.kind_of` 返回 None），性质同 impl-02 的批号任务标签。ReviewDecision 以 (proposal_set_revision_id, proposal_key) 引用提案，同时记主体 `entity_id`。
- B：每个提案一个 `art_`/`rev_`（Artifact 爆炸）。
- C：登记 `mp_`/`ap_`/`cfp_`/`erp_`/`aln_` 等新前缀（须按登记册 `:96` 流程经用户确认）。

**推荐 A**。

### D-13 §20.5 何时 PASS，谁改 `run_all.sh`

- A：`m7-assembler.sh` 保留 `BLOCKED upstream_m6_real`（exit 2）；ACT 10 把 `run_all.sh` 的 `20.5)` 分支改为调用它：0 → PASS，2 → `BLOCKED 前置缺失: M6 Review Workbench`，1/其他 → FAIL。
- B：金标输入即可判 PASS（20.5 的性质只取决于 M7），ACT 10 接线后 20.5 PASS。
- C：本包不改 `run_all.sh`，20.5 维持「M7 未实现」直到 M6 落地后另批接线。

**推荐 A**：与 impl-02 `semantic_layer` 先例一致；BLOCKED 原因从 M7 收窄到 M6，进展可观测；不把「金标代替真实上游」写成 PASS。注：20.5「不改旧身份」本包只覆盖 `pat_/co_/as_/sv_`，`ent_` 保号属 M8 与 20.11。

### D-14 同一 Edition 的新修订（M6 返工）进入 ReleaseRun

- A：本包支持「替换」。以 (source_id, edition_part_ids 集合相等) 识别替换，不以 `stage_package_id` 识别——`register_stage_package` 对已存在的包号抛 `DuplicateIdentifier`（`service.py:745-746`），M6 返工在 Ledger 里只能取新包号（与 §8.1 `:303`「修正保留包号」不一致，需另报）；part 集合不相交视为扩展，部分重叠拒绝。按对象 (entity_id, content_sha256) 比对 Snapshot `provenance` 中的旧哈希与新视图：等价 → 原样继承（`carried_forward`）；自动关系直接重算；人工裁决按 `basis_sha256` 重算（只取与该裁决相关的字段：Merge/Alias 取名称、别名、规则哈希、concept_id；冲突组取各 SchoolView 的 school_id、subject、claim_refs、conflict_group_id、changes_current_judgment），相等则继承，不等则降级 `needs_review` 重新入 M7 队列；Assertion 被删 → 自动退役并写 IdentityDelta `retired`；Pattern/Concept 失去全部来源 → `ConflictProposal(provenance_lost)` 人工决定 `retire` 或 `keep`。M6 的 ReworkImpactReport 只作交叉核对，不作判定依据。
- B：本包拒绝替换，另批实现。
- C：旧 Edition 的全部贡献失效后重算（违反 §14.1 `:643` 禁止整 Edition 批量失效）。

**推荐 A**：规则与 §14.1 `:640` 同构；既往 ReleaseRun 的裁决结果只从 Snapshot 读取，不读其他 Run 的决定 Artifact，符合 §6.2 `:173`。

### D-15 基底 Snapshot 修订的状态与并发

- A：新 Snapshot 修订封存后调用 `supersede_revision(base, new)`；并发的第二个 ReleaseRun 若基底已 `superseded`，在 begin 之前被拒（`NotConsumable`），形成乐观并发。
- B：不 supersede，靠「查最新修订」判断基底（违反 §7 `:207`）。
- C：同一 technique 只允许一个 running release_run（需 Local Orchestrator，未实现）。

**推荐 A**：superseded 修订仍可历史重放（§8.2 `:392`）。

### D-16 M7 Checkpoint 落盘粒度

§17.1 `:843` 的人工阶段列表只写 M2/M3/M4/M6，未含 M7。

- A：视同人工阶段：非人工 task（`propose_r<N>`、`seal_snapshot`）各一个 Checkpoint；每条人工决定被 Ledger 接受后即时一个。
- B：只按非人工 task 落盘。

**推荐 A**：M7 有人工队列（§5 `:124`），遗漏会使 §17.1 `:845` 的恢复语义在 M7 失效。

### D-17 Part 级 ReviewedEditionPackage 能否汇编

- A：允许。Snapshot 逐 Edition 记已汇编 `edition_part_ids` 与 `edition_complete`；完整性由 M8 按消费级别卡（PUBLIC_RELEASE 须完整）。
- B：只接受完整 Edition（首纵切宿主只有「卷一·前三页」，永远无法汇编）。

**推荐 A**（§6.1 `:151`）。

### D-18 Work 标识

§3 `:45` 有 Work 概念，但登记册没有 Work 前缀。

- A：以 `src_<work>_ed<NN>` 的 `<work>` 段作 `work_key`，不新增前缀。
- B：新登记 `wk_` 前缀。

**推荐 A**。

## 5. 接口契约

### 5.1 上游输入（M7 消费）

| 来源 | artifact_type / 对象 | M7 读取的字段 | 约束 |
|---|---|---|---|
| M6 | m6 StagePackage（`pkg_m6_<32hex>`，`artifact_type=stage_package`） | `stage=="m6"`、`status=="sealed"`、`validation.passed==true`、`manifest.output_artifacts` 中恰 1 个 `reviewed_edition_package` 引用 | 修订 `sealed`；**所属 StepRun `succeeded`（P5，`INTERFACES.md:24`【I-13】）**；M7 不改其状态 |
| M6 | `reviewed_edition_package`（索引）+ `reviewed_edition`（主内容），键逐字取 `impl-06-review/README.md §5.3` | 见 §0.3 与 `impl-06-review/README.md §5.3` | `sealed`；`unresolved_count==0`（§14 `:631`） |
| M4（在 M6 包冻结血缘内） | `candidate_package` / `candidate_set`（经 `reviewed_edition.candidate_package_revision_id`） | 内容实体（概念/格局/主张/学派视图）与证据链路 | m4 StepRun `succeeded`（P5）；须在 m6 包 `lineage.upstream_artifacts` 中 |
| M7 自身 | `canonical_snapshot`（基底，可无） | `knowledge` 全部；`meta.snapshot_artifact_id` | 必须 `sealed`（已 superseded 即拒绝，D-15） |
| Review Console M7 模式 | `human_event`（内容含 `m7_decision`） | 见 §5.4 | 必须经 `record_human_event` 写入本 StepRun |
| 调用方 | `run_m7(...)` 参数 | `technique_id`、`reviewed_package_revision_ids`（显式列表）、`base_snapshot_revision_id`（显式或 None） | 不查「最新」（§7 `:207`） |

M6 产出契约为 `reviewed_edition`（主内容）+ `reviewed_edition_package`（阶段输出索引），逐字见 `impl-06-review/README.md §5.3`；草稿原写的 `reviewed_edition_knowledge`（本包自造聚合视图）**已由 D-0-2 撤销**，内容实体改由 M7 经 m6 冻结血缘读 M4 `candidate_set`。对象 `content_sha256` 由 M7 按规范 JSON 计算，不信任上游自带值。

### 5.2 下游输出（M7 产出）

> 命名按 D-0-3：主内容取 `INTERFACES.md §4` M7 行已登记名 `canonical_snapshot`（草稿原写 `canonical_knowledge_snapshot`，以登记名为准）；创世薄切片只产出 `canonical_snapshot` + `assembly_package`（其余为完整波次，`DEFERRED`）。

| artifact_type | 内容 | 主要消费者 |
|---|---|---|
| `canonical_snapshot` | `{schema_version, knowledge, meta}`；`knowledge_sha256 = sha256(canonical_json(knowledge))` | M8（§16 `:662`）、下一次 M7 |
| `assembly_proposal_set` | 每轮一个修订：提案列表（`proposal_key`、kind、relation、subject、targets、options、`resolution: auto|human|blocked`、`decision_type`） | Review Console M7 模式、PendingQueue |
| `edition_collation_set` | Alignment/VariantReading/Addition/Omission 关系与 `not_comparable` 清单 | M8（EvidenceMapPack/KnowledgeDataPack） |
| `identity_delta` | 相对基底的身份变化：`{from_entity_id, to_entity_ids, change_type ∈ migrated|merged|split|retired, entity_kind ∈ pattern|concept|assertion, reason_ref, span_allocation?}` | M8 IdentityMigrationMap（§16 `:732`） |
| `assembly_report` | `affected_entity_ids`、`recomputed_entity_ids`、`carried_entity_count`、提案计数、回流轮数、`needs_review` 清单 | Gate、Orchestrator ReworkImpact |
| `validation_report` | Gate 结果 | StagePackage.validation |
| m7 StagePackage（`pkg_m7_`） | `payload`：各修订引用 + `technique_id` + `editions_included` | M8、LineageGraph |

`knowledge` 结构（全部列表按键排序，规范 JSON：`sort_keys=True, ensure_ascii=False, separators=(",", ":")`，末尾 `"\n"`）：

```text
technique_id; id_allocation {"pat_<technique>": <最大已发号整数>}; retired_entity_ids []
editions  [{source_id, work_key, reviewed_package_revision_id, stage_package_id, edition_part_ids, edition_complete}]
concepts  [{concept_id, name, aliases, provenance[{source_id, content_sha256, content_status}]}]
patterns  [{pattern_id, concept_id, name, aliases, rules[{rule_key, ast_sha256, source_id}], assertion_ids, school_view_ids, provenance[...]}]
assertions [{assertion_id, subject_entity_id, source_id, collation_key, text_sha256, source_span_ids, school_view_ids, content_status}]
school_views [原样保留，subject 改写为正式 entity_id]
conflict_groups [{conflict_group_id, member_school_view_ids, first_layer_display, resolutions[{mode, proposal_key, basis_sha256}]}]
relations [{relation_key, kind ∈ attached|alias_of|distinct_from|merged_into|alignment|variant_reading|addition|omission, subject, object, detail, resolution{mode auto|human, proposal_key, basis_sha256}}]
```

`meta`：`snapshot_artifact_id`、`base_snapshot_revision_id`、`release_scope_id`、`processing_run_id`、`step_run_id`、`assembly_seq`、`entity_last_changed {entity_id: seq}`、`decision_refs {proposal_key: human_event 修订}`。运行随机值只进 `meta`，所以 `knowledge` 可与金标逐字节比对。

M7 不合成、不升级内容成熟度：`content_status` 逐来源保留，由 M8 按消费级别过滤（§16.1 `:670-678`）。

### 5.3 对其他模块的接口假设（需并行草案对账）

1. **M4**：`as_`、`co_` 在技法命名空间全局唯一发号（跨 EditionRun 不撞号）；新格局候选不自发 `pat_`，只带 `candidate_key`（D-04）。
2. **M4**：规则以纯声明式 AST 表达，M4/M6 或 M7 能对其规范 JSON 取 `ast_sha256`（§13 `:612`）。
3. **M4/M6**：SchoolView 的 `conflict_group_id` 在单个 EditionRun 内发号；跨版冲突组统一由 M7 裁决（R06）。
4. **M4/M6**：供给 `collation_key` 与 `collation_units`（D-07）；同一 Work 不同版次的同一 `collation_key` 表示同一位置。
5. **M6**：ReviewedEditionPackage 以 m6 StagePackage + 一个 `reviewed_edition_knowledge` 修订的形态封存；返工在 Ledger 中只能以新 `stage_package_id` 登记（`service.py:745-746`），M7 以 (source_id, edition_part_ids) 识别替换（D-14）。
6. **M6 §14.1**：M7 不读 M6 的失效结果做判定，只按内容哈希自行比对（D-14）；M6 的 ReworkImpactReport 如存在，由 `assembly_report.rework_cross_check` 记录一致性。
7. **M8**：以 m7 StagePackage 修订为冻结输入，从 `identity_delta` 链（上次 Release 所用 Snapshot 修订 → 本次）合成 IdentityMigrationMap 并补 `release_id`；`ent_` 的保号与退役由 M8 按 subject 的 IdentityDelta 推导。
8. **M8**：`conflict_groups[].first_layer_display` 是 SchoolViewPack 首层展示的唯一来源（§16 `:736`）。
9. **Review Console M7 模式**：只写 `human_event`，内容符合 §5.4；决定作用对象是提案，不直接改 Snapshot。
10. **Local Orchestrator**：PendingQueue「M7 待裁决」读 m7 Checkpoint 的 `pending_queue`（元素 `{"task_id": proposal_key}`）。

### 5.4 M7 人工决定事件内容

```json
{"schema_version":"1.0.0","m7_decision":{"proposal_set_revision_id":"rev_…","proposal_key":"merge:…",
 "choice":"attach|admit_new|merge_entities|split|accept_alias|reject_alias|unify|keep_separate|retire|keep",
 "target_entity_ids":["pat_…"],"seen_revision_id":"rev_…","span_allocation":{"<新号占位>":["ss_…"]},"note":"…"}}
```

`choice` 必须属于该提案 `options`；`seen_revision_id` 必须等于提案所见的包或 Snapshot 修订；`split` 必须给出覆盖旧对象全部 Span 且互不重叠的 `span_allocation`（§16 `:732`）。

## 6. 设计要点

### 6.1 稳定 Pattern 聚合规则（M7-R）

记新版候选为 c，基底正式集为 S，同批其他候选为 B。名称键 = NFC 后去首尾空白的 `name ∪ aliases`；规则键 = `ast_sha256` 集合。

| 规则 | 条件 | 提案 | 裁定 |
|---|---|---|---|
| R01 | `c.pattern_id` ∈ S，concept 一致 | Merge(attach) | 自动 |
| R01b | `c.pattern_id` ∈ S，concept 不一致 | Conflict(concept_binding_mismatch) | 人工 |
| R02 | `c.pattern_id` 非空、∉ S：已退役 → 拒绝（`ID_001`，§8.1 `:267`）；未退役且无名称/规则命中 → Merge(admit_new，保留该号) | 自动 |
| R03a | 无号；名称命中 = 规则命中 = {p} | Merge(attach p) | 自动 |
| R03b | 名称命中 {p}，规则命中 ∅ | Merge(options attach p / admit_new) | 人工（同名异义或多套规则） |
| R03c | 名称命中 ∅，规则命中 {p} | Alias(accept_alias / reject_alias) | 人工（异名同义） |
| R03d | 名称或规则命中 ≥2 个正式对象 | Merge(options 各 attach / admit_new / merge_entities) | 人工 |
| R03e | 无任何命中且与 B 无名称/规则交集 | Merge(admit_new，发号) | 自动 |
| R03f | 对 S 无命中，但与 B 中「对 S 有命中且待人工」的候选有名称/规则交集 | 标 `blocked`，依赖该提案，裁决后回流重算 | 回流 |
| R03g | 对 S 无命中，且与 B 中另一个同样对 S 无命中的候选有交集 | Merge(options 各自 admit_new / 并为一个) | 人工 |
| R04 | Concept：`concept_id` ∈ S → attach 自动；同名异号 → Alias 人工；无命中 → admit_new 自动（保留 M4 的 `co_`） | | |
| R05 | Assertion 永不跨版合并，保号；挂到 subject 裁决后的正式对象 | — | 自动 |
| R06 | SchoolView 原样保留；同一正式主体在基底已有冲突组、新版又带冲突组 → Conflict(unify / keep_separate)；`unify` 沿用基底 `cg_`（分组标识，非身份）；任一成员 `changes_current_judgment=true` → `first_layer_display=true` | | 人工 / 自动 |
| R07 | 同 work_key、同 `collation_key`，两侧 `present`，两侧主体裁决到同一正式对象，NFC 文本相等 | Evidence(alignment) | 自动 |
| R07b | 同 R07 位置，但两侧主体裁决到不同正式对象 | Conflict(collation_subject_mismatch) | 人工 |
| R08 | 同 R07，文本不等 | Evidence(variant_reading，带 difflib opcodes) | 自动 |
| R09 | 新版 `present`、旧版声明 `present:false` → addition；反之 → omission；任一侧未声明 → `not_comparable` | Evidence | 自动 |
| R10 | 人工 `reject_alias`/同名异义选 `admit_new` → 写 `distinct_from` 关系；后续 ReleaseRun 遇同一对不再提案 | — | 自动 |

新号在所有轮次结束后统一分配，顺序为 (source_id, candidate_key) 升序，保证增量与全量结果一致。

### 6.2 增量判定（M7-I）

1. **触点**（只命中拥有该键的基底对象）：Pattern 候选 → 裁决目标、`pattern_id`/名称/规则命中的全部基底 Pattern、其 concept；Concept → `concept_id` 与名称命中；Assertion → 裁决后主体、基底中同 (work_key, collation_key) 的 Assertion；SchoolView → 裁决后主体、基底中同 (主体, school_id) 的 SchoolView；声明 `present:false` 或被撤销声明的对勘单元 → 基底中该位置的 Assertion。
2. **命中集** A0 = 上述触点命中 ∪ 本次人工决定的目标（冲突组决定取全部基底成员）∪（替换时）内容哈希变化或被删除的对象及其旧版触点。只统计基底中已有的对象；本次新建对象另列 `created_entity_ids`。
3. **闭包** A* = A0 沿 `alias_of`、`attached`、`merged_into`、`distinct_from` 与同冲突组成员迭代到不动点；对勘关系只为 A* 主体、且只在涉及新版 work_key 的版次对上重算。
4. **不受影响的对象**：规范 JSON 字节原样拷贝，`entity_last_changed` 不变。
5. **报告**：`assembly_report.recomputed_entity_ids` 必须**恰好等于** A*（少了是漏算，多了就不是增量）。
6. **等价性**：`knowledge_sha256(增量汇编)` == `knowledge_sha256(从空基底按加入顺序一次汇编全部版次，使用同一组决定)`。
7. 独立 Gate 自行重算 A* 与等价性，不信任汇编器报告。

### 6.3 身份保号

- 基底中每个 `entity_id`，要么仍以同号存在于新 Snapshot，要么作为 `from_entity_id` 出现在 `identity_delta`，且 `reason_ref` 可解析到本 Run 已封存的提案或决定；
- 新发 `pat_` 号大于 `id_allocation` 历史最大值，永不复用 `retired_entity_ids`；
- `merge_entities`/`split` 的新对象取新号，旧号进 `retired_entity_ids`；
- SourceSpan 永不改（`permanent`，§16 `:730`），M7 只引用。

### 6.4 ReleaseRun 中 M7 的位置（§6.2 映射到 Ledger）

```text
create_processing_run("release_run", X)                         X = 本次配置 Artifact 身份（D-02）
put_run_artifact("configuration", artifact_id=X, {"stage":"m7", …})
begin_step_run(inputs=[基底 Snapshot 修订?] + m6 包修订 + reviewed_edition_knowledge 修订)
  propose_r1 → 自动裁定 → seal assembly_proposal_set → Checkpoint
  有人工提案？ await_human([proposal_set 修订]) → 返回 resume_token          （M7 待裁决队列）
    record_m7_decision × N（每条 put+seal human_event → record_human_event → Checkpoint）
    resume_m7：校验全部待决提案恰被决定一次 → resume → 回流 propose_r2 …（可再次 await_human）
  apply → Gate → seal snapshot（prev=基底）/ collation / identity_delta / report / validation / log
  record_transformation(operation="assemble_knowledge") → m7 StagePackage → finish_step_run
  supersede_revision(基底, 新 Snapshot)                                     （D-15）
→ 同一 ReleaseRun 的 M8 StepRun 以 m7 StagePackage 修订为冻结输入
```

### 6.5 与 M6 精确失效传播、M8 IdentityMigrationMap 的接口

- M6 返工 → 同一 `stage_package_id` 的新修订 → 新 ReleaseRun 显式传入 → M7 按 D-14 比对内容哈希，得出 carried/needs_review/retired，结果写 `assembly_report`；不触碰 M6 修订状态。
- M7 → M8：只交 `identity_delta`（实体级、无 `release_id`）；M8 负责跨多个 Snapshot 修订合成、补 `release_id`、推导 `ent_` 映射并计算锚点可迁移率（§16 `:734`）。`reason_ref` 形如 `{"kind":"proposal","proposal_set_revision_id":…,"proposal_key":…}` 或 `{"kind":"review_decision","human_event_revision_id":…}`。

## 7. 目录（完整波次落地后，DEFERRED）

> 创世薄切片 `G0` 的目录见 §0 与各 `act/g0-*.yaml` 的 `scope.write`；以下是完整波次，`DEFERRED`。

```text
pipeline/corpus/_fixture/mini_release01/          F 组（ACT 00–01）
  README.md  manifest.yaml  verify.sh
  editions/ed01.reviewed.json  ed99.reviewed.json  ed01r2.reviewed.json
  decisions/r2.decisions.yaml  r2b.decisions.yaml  r3.decisions.yaml
  expected/snapshot_s1.knowledge.json  snapshot_s2.knowledge.json  snapshot_s3.knowledge.json
           proposals_r2.json  collation_s2.json  identity_delta_s3.json  affected_s2.json  affected_s3.json
  tools/build_fixture.py
pipeline/assembly/
  __init__.py        M7_TOOL / M7_TOOL_VERSION
  errors.py          AssemblyRefused
  canonical.py       canonical_json / sha256 / nfc_key / proposal_key
  model.py           validate_reviewed_edition / validate_snapshot_knowledge / empty_knowledge
  matcher.py         propose（M7-R 规则，纯函数）
  apply.py           apply_resolutions（新 knowledge + collation + identity_delta，纯函数）
  incremental.py     affected_closure / replace_edition_diff / assemble（纯函数编排）
  gate.py            evaluate_assembly（不 import matcher/apply/incremental）
  fixture_seed.py    把 mini_release01 视图灌入 Ledger 为 m6 包（验收宿主专用）
  inputs.py          resolve_m7_inputs（只读）
  step.py            run_m7 / record_m7_decision / resume_m7
  __main__.py        python -m pipeline.assembly run|decide|resume
  acceptance.py      m7-assembler 十四项判定
  tests/             test_canonical test_model test_matcher test_apply test_incremental test_gate test_step test_human_loop test_acceptance
openspec/acceptance/m7-assembler.sh
```

## 8. 派发建议

**创世薄切片 `G0`（本波，W5-L0）**：

| 组 | ACT | 说明 |
|---|---|---|
| G0 | G0-01、G0-02、G0-03、G0-04、G0-05 | 纯函数创世汇编（01–03）+ 最小 Ledger 事务（04）+ 验收判据（05）；串行，前一个 `ACCEPTED` 后派下一个 |

**完整增量汇编（`DEFERRED`，下一波）**：

| 组 | ACT | 说明 |
|---|---|---|
| F | 00、01 | fixture 输入与金标；不得与 J 组同一 Agent |
| J1 | 02、03、04 | 规范化、模型校验、提案、应用（纯函数） |
| J2 | 05、06 | 增量编排与独立 Gate |
| J3 | 07、08 | Ledger 集成：自动路径、人工回路与替换 |
| J4 | 09、10 | 验收脚本；ACT 10 只在 D-13 选 A/B 且主 Agent 授权时派发 |

各组串行，前一组 `ACCEPTED` 后派下一组。`G0` 的 ACT 是完整波次 ACT 02–04、06–07、09 的创世子集；完整波次的草稿 ACT 文件保留，随 `deferred_acts` 重编号后再派发。
