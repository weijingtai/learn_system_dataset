# INTERFACES：M1–M8 跨模块接口总表（impl-00 草案）

状态：`READY_FOR_REVIEW`（`impl-00/10` 已登记 §4 临时闭集并同步首纵切裁决；W2-C1 定稿 2026-09-12）。本表是 M1/M2 薄接入、M3 语义层、M4、M5、M6、M7、M8、Orchestrator/Contract Registry 各并行草案的对账基准。

图例：
- 【规格】规格原文可引，给出行号（`openspec/learn-system-blackbox-architecture.md`，共 1001 行）；
- 【实际】现有代码或 fixture 的实际形状，m1–m3 一律以此为准；
- 【草案】本包提议，依赖 README §4 的 D-xx 裁决；
- 【未定义】规格没有写，指向 D-xx 或标注「纵切后」。

对账规则：下游卡片的「冻结输入」必须与上游卡片的「输出」逐字对上（artifact_type、键名）。并行草案发现不一致时，引用本表条目上报，不得自行改名。

---

## 1. 公共约定

### 1.1 调用、事务与人工恢复

| 项 | 约定 | 依据 |
|---|---|---|
| 调用 | `execute(StepRequest) → StepResult`；StepRequest 必填 `schema_version, processing_run_id, step_run_id, input_artifact_ids, technique_profile_id, configuration_artifact_id`，可选 `supersedes_step_run_id` | 【规格】181–207；`step_request.schema.json` |
| 结果 | StepResult 必填 `status, status_version(≥1), output_artifact_ids, validation_report_ids, log_artifact_ids, failure_artifact_ids`；`awaiting_human` 必带 `resume_token` 与 `pending_queue_artifact_ids`；`failed` 的失败修订至少 1 个 | `step_result.schema.json` allOf |
| 读取纪律 | 只读 StepRequest 中冻结的 `rev_`，不得解析为「最新」 | 【规格】207、261 |
| 上游包过滤 | 解析上游 StagePackage 时，其所属 `step_run_id` 的状态必须为 `succeeded`，**只接受 succeeded StepRun 的包**；归属 `failed`/`running` 等非 succeeded StepRun 的包一律拒绝（下游以 ValidationRefused / CompileRefused 等拒绝），严禁消费失败运行遗留的包 | 【实际】impl-02 ACCEPTANCE §5.3；【规格】836 |
| 运行粒度 | 一个 StepRun = 一个 EditionPart 的一个阶段任务及其全部人工队列；不得每条人工决定另建 StepRun | 【规格】211 |
| stage 推导 | StepRequest 不含 stage，由配置修订内容的 `"stage"` 键推导 | 【实际】fixture_ingest.py 280–297、corpus_compiler/step.py 87 |
| 配置修订 | `put_run_artifact` 只允许 `configuration`、`technique_profile` | 【实际】service.py 66 |
| 事务序列 | 建 StepRun → 冻结输入 → 验输入契约 → 执行 → 存原始输出与日志 → 哈希 → 验输出 → Transformation → StepManifest → 终态；失败与部分输出也封存 | 【规格】836；模板见 impl-02 `act/03.yaml` 30–65 |
| 失败封存 | 写 `failure_report` 修订 → `fail_step_run` | 【实际】step.py 373 |
| 人工事件 | `record_human_event(step_run_id, resume_token, event_rev, decision_type=None)`；事件修订的 artifact_type 必须为 `human_event`；`decision_type` 取 §8.2 的 8 类 | 【实际】service.py 824、922–930；【规格】349–364 |
| 进度事件 | 各 Module 须向 Orchestrator 实时上报 | 【规格】226；【未定义】事件形状（Orchestrator 包定义） |
| 热点文件写权 | `fixture_ingest.py` 首纵切不改（P9）；`openspec/schemas/**` 首纵切不新增文件（P3） | G7-RULINGS §9 第 5/13 条 |
| Ledger 只读查询缺口 | 优先 `LedgerReader` 公开方法；缺口（`frozen_inputs`、`artifacts.artifact_type`、`stage_packages`、按 `step_run_id` 取 sealed `stage_package`）允许 `reader.store.conn` 只读 SELECT，清单见 impl-00 README §5.2，impl-08 补公开读方法 | G7-RULINGS §9 第 13 条、§9.1 第 25 条 |
| 页图字节 | SourceAssetPack 页图字节登记进 Ledger（薄 M1 `source_asset_page`，`rights_scope=internal`）；fixture 内不出现图像 | G7-RULINGS §9 第 16 条 |
| M5 包下游消费 | 消费 M5 包须同时满足所属 StepRun `succeeded` 与 `validation.passed == true` | G7-RULINGS §9 第 21 条 |

### 1.2 StagePackage 信封

六段结构（【规格】232–241）：`payload / manifest / validation / lineage / logs / failures`。Schema 中 `payload` 只要求是 object（`stage_package.schema.json` 22–24），`counts` 只要求值为非负整数（59–65）。

**【实际】现存两种形状（必须知晓）：**

| 维度 | fixture expected/m1–m3（信封金标） | 生产 `run_m3` |
|---|---|---|
| `manifest.input_artifacts` | 只列上一阶段输出 1 条 | 全部冻结输入（mini_ed01 为 6 条） |
| `payload` | 含 `*_path`，指向 fixture 文件 | 含 `*_revision_id` 与 `gate_profile` |
| `validation.report_artifacts`、`logs` | 空 | 非空 |
| `lineage.upstream_artifacts` | 空 | ocr_page_set + manifest |

**【草案】对账原则（D-05/D-06）**：下游只能依赖 `manifest.output_artifacts`、`manifest.counts`、`manifest.content_sha256`，以及 payload 中的 `*_revision_id(s)` 键；任何模块不得依赖 `*_path` 键。

**content_sha256 规则**：
- 【实际】（verify.sh 362–366）m1 = sha256(`manifest.yaml` 字节)；m2 = sha256(按页名排序的各页 JSON sha256 以 `"\n"` 连接后再加 `"\n"`)；m3 = sha256(`spans.yaml` 字节)。
- 【草案】m4–m8 = sha256(本阶段主内容 Artifact 字节)，主内容见 §4。

### 1.3 StageCheckpoint

- 必含字段【规格】844：`edition_part_id, stage, step_run_id`、已完成任务、已封存人工决定、待办剩余（含五个专用队列）、下一步指针、`actor_ref`、时间、前一 Checkpoint 修订、ReworkImpactReport 引用。
- 粒度【规格】843：人工阶段（M2 校订、M3 边界、M4 类别、M6 审核）每接受一个人工决定就落盘一次；非人工任务每完成一个 task 落盘一次。
- 【实际】签名 `write_checkpoint(step_run_id, *, edition_part_id, stage, completed_tasks, human_decisions, pending_queue, next_pointer, rework_impact_report_revision_id=None, artifact_id=None, artifact_revision_id=None)`（service.py 1364–1377）；`completed_tasks` 元素键为 `{task_id, artifact_revision_id, status, terminal_state}`（fixture_ingest.py 240–246）。
- 链键「EditionPart × Stage」只有一条链（842）；【G7-RULINGS §9 第 4 条】ReleaseRun（m7/m8）首纵切单 Part：`edition_part_id` 取该 Part，跨 Part Release 纵切后改 Ledger 再议。

### 1.4 标识

- 可用前缀（ids.py 14–34；registry §3.1–§3.4）：`src_ ss_ ku_ as_ pr_ co_shared_ co_ hg_ art_ rev_ prun_ srun_ pkg_m[1-8]_ rel_ sch_ sv_ cg_ pat_ ent_`。
- 业务身份（entity_id）与物理修订（artifact_revision_id）分离（【规格】257–267）。ReviewDecision / EvidenceLink / Annotation 必须同时记录两者（265）。
- 规格要求有身份但无前缀的对象：EvidenceLink、ApplicabilityRule、Case、Interpretation、Alias、四类 Proposal、CorrectionRequest、ReworkImpactReport、CanonicalKnowledgeSnapshot → 【未定义】D-08。

### 1.5 状态、门禁与错误码

- 四个正交状态轴（【规格】433–440）：Artifact status 5 值、StepRun status 6 值、content_status 7 值、ReviewDecision type 8 值。
- 门禁代号只允许 `G1…G7`（【规格】586）。M2/M3/M4/M6/M7 的阶段 Gate **不得**冠 G 代号，统一称「M<n> Gate」，检查名用 snake_case。
- 错误码只允许 9 个（【规格】368–380）；新失败类别的映射见 D-17。

---

## 2. 阶段接口卡

每卡字段：运行归属 / 冻结输入 / 任务与 Checkpoint / 输出 artifact_type / StagePackage / Gate / 人工队列 / 下游实际消费键 / 未定义。

### 2.1 M1 Source Intake（首纵切：薄接入）

| 项 | 内容 |
|---|---|
| 运行归属 | EditionRun，`stage=m1`【实际】 |
| 规格输入 | PDF/PNG/EPUB/TXT/Markdown/旧库等 SourceSubmission【规格】446 |
| 冻结输入 | 无（`input_artifact_ids=[]`；expected/m1 `input_artifacts: []`）【实际】 |
| 任务与 Checkpoint | 1 个 task，`task_id=ingest_source`，共 1 个 Checkpoint【实际】fixture_ingest.py 54、171–178 |
| 输出 artifact_type | 任务级与阶段输出均为 `source_manifest`（manifest.yaml 原字节）【实际】STAGE_OUTPUT_TYPES 44 |
| payload | `source_manifest{source_id, source_manifest_path, edition_part_artifact_id}`【实际】expected/m1 6–10 |
| counts | `{pages, source_assets}`；content_sha256 = sha256(manifest.yaml)；operation `ingest_source` |
| Gate | 【未定义】§9 只列输出清单（448–453），无 Gate 条款；首纵切不设 |
| 人工队列 | 无 |
| 下游实际消费键 | M3 compiler（impl-02 act/01 R1–R8）：`source_id, work_title, technique_id, edition_part.artifact_id, edition_part.pages[], source_assets[].page/.sha256`；【草案】M8 另读 `source_assets[].width/.height/.path_ref`（714、717）以及 `rights_status, release_policy`（717–723） |
| 未定义 | 权利与准入决定的结构（452）；`rights_status` 闭集（manifest 为自由文本，与 SCHEMA.md §1 枚举不一致）→ D-16；转录重放（875 行差距，`m1-replay.sh`）纵切后 |

### 2.2 M2 Digitization & Correction（首纵切：薄接入）

| 项 | 内容 |
|---|---|
| 运行归属 | EditionRun，`stage=m2` |
| 冻结输入 | m1 `source_manifest` 修订【实际】expected/m2 24–29 |
| 任务与 Checkpoint | 每页一个 task（`task_id` = 页名），每页 1 个 Checkpoint；异常页附 `human_event`，并累积写入后续 Checkpoint 的 `human_decisions`【实际】fixture_ingest.py 179–199、217–252。规格要求人工校订每个决定一个 Checkpoint（843） |
| 输出 artifact_type | 任务级：`ocr_page`（页 JSON 原字节）、`human_event`（anomaly entry，JSON sort_keys）；阶段输出：`ocr_page_set`（expected payload 的 JSON，fixture_ingest.py 329–338）【实际】 |
| payload | `ocr_pages[{page, path, sha256}], anomalies_path, terminal_states{页: 终态}`【实际】 |
| counts | `{ocr_pages, lines, chars, anomalies}`；operation `digitize_pages` |
| Gate | 【规格】480、490–494：`deferred` 阻断；`known_unrecognizable` 必须附理由与证据 Artifact；`manually_transcribed` 可放行 |
| 人工队列 | 队列 1「M2 异常页与低置信字」【规格】120 |
| 下游实际消费键 | M3（impl-02 act/03 36–39）：`ocr_page_set.ocr_pages[].page/.sha256`、`ocr_page_set.terminal_states`、human_event 内容中的 `page`；页 JSON 的 `lines[].id/.text/.box`、`chars[].id/.char/.box/.parent`、`width/height` |
| 未定义 | `path` 指向 fixture，生产 M2 不应产出（D-05）；OCRProfile 修订作为冻结输入（476）、DigitizationPackage 的扫描/置信度/质量报告（474）、EPUB/TXT 四件产物（478）——纵切后（`m2-export-integrity.sh`） |

### 2.3 M3 Corpus Compilation（首纵切内；结构层已实现，语义层 BLOCKED）

| 项 | 内容 |
|---|---|
| 运行归属 | EditionRun，`stage=m3` |
| 冻结输入 | `ocr_page_set` + `source_manifest` + 各页 `ocr_page` + M2 `human_event`（mini_ed01 共 6 条）【实际】impl-02 act/03 34 |
| 任务与 Checkpoint | 每批一个 task，`task_id=<work>_b<3位>`，mini_ed01 共 5 个 Checkpoint【实际】；语义层每个边界人工裁决一个 Checkpoint【规格】843（未实现） |
| 输出 artifact_type | `corpus_batch`、`corpus_spans`（字节 = 金标 spans.yaml）、`coverage_report`、`validation_report`、`step_log`、`corpus_package`（阶段输出）；失败时 `failure_report`【实际】step.py 159/182/200/215/227/247/373 |
| corpus_package 内容 | `{spans_revision_id, coverage_report_revision_id, coverage, excluded_pages, gate_profile:"structural_only", semantic:"not_evaluated"}`【实际】 |
| payload | 生产 `{spans_revision_id, coverage, excluded_pages, gate_profile}`；金标 `{spans_path, coverage, excluded_pages}`【实际】 |
| counts | `{spans: 43, batches: 5}`；content_sha256 = sha256(spans.yaml) = `ec6d77b9…44ef`；operation `compile_corpus` |
| corpus_spans 键序 | 顶层 `work, source_id, edition_part_artifact_id, evidence_level, content_status, span_count, batch_count, spans`；每条 `span_id, batch_id, page, line_index, start_offset, end_offset, text, source_anchor{page, image_sha256, line_id, bbox{x,y,w,h}, chars[{char_index, glyph_id, char, box}]}`【实际】act/01 R6–R8 |
| Gate | 【规格】521：同层 100% 覆盖、无缺口、无重叠、拼接等于原文、未解决语义分歧为 0；【实际】结构层 8 项检查（`m3-coverage.sh`），语义层 BLOCKED |
| 人工队列 | 队列 2「M3 边界分歧」【规格】121 |
| 下游消费键 | 【草案】M4：`spans[].span_id/.text/.page`；M5：全部 span 与锚点字段；M8：`source_anchor` 整体随包发布（713） |
| 未定义 | SemanticSpan 形状（504、513–519）→ D-12；spans 没有 quote hash（527、G3 67）→ D-12 取 A 时由 M4 以 `sha256(quote)` 写入 evidence |

### 2.4 M4 Knowledge Extraction（纵切后，不在首纵切）

| 项 | 内容 |
|---|---|
| 运行归属 | EditionRun，`stage=m4`【规格】143 |
| 冻结输入【草案】 | m3 `corpus_package` + `corpus_spans`；`technique_profile` 修订；L1 canon / L2 homographs 表修订（128、540、547——仓库中不存在，D-11）；`model_run` 录制修订（D-11 取 A 时） |
| 任务与 Checkpoint【草案】 | 按「类别 × 批次」一个 task，因为不同类别不得由一个模型一次混合完成（572）；`task_id = m4_<category>_<batch_id>`，category ∈ `term_layering, concept, assertion, school_view`（`rule / case_editorial` 在 D-08 前锁 0）；模型运行记录在 task 内部，不另立 Checkpoint；类别分歧每个人工决定 1 个 Checkpoint（843） |
| 输出 artifact_type【草案】 | 任务级 `candidate_batch`、`model_run`（Prompt/输入/Response/参数/版本/解析/错误，574）、`candidate_diff_report`；人工 `human_event`（类别 ReviewDecision）；主内容 `candidate_set`；阶段输出 `candidate_package`；另有通用 `validation_report`、`step_log` |
| payload【草案】 | `stage_payload_m4`：`{candidate_set_revision_id, span_layer, extraction_mode, unresolved_disputes: 0}` |
| counts【草案】 | `{concepts, assertions, evidence_links, applicability_rules, school_views, cases}`；content_sha256 = sha256(candidate_set 字节)；operation `extract_knowledge` |
| Gate | 【规格】572：未解决语义分歧为 0 才能通过；【草案】检查名 `category_isolation, ab_independence, c_rereads_source, disputes_resolved, raw_model_artifacts_complete, evidence_present(SEM_001)` |
| 人工队列 | 队列 3「M4 类别分歧」【规格】122 |
| Tag 字段 | `omen_carrying`、`condition_affordance`、`school_variance_display`、`concept_id`、「是否改变当前判断」由 M4 生产（803–815）；candidate_set 预留对应字段（§3.2） |
| 下游消费键 | M5：candidate_set 全量；M6：`assertions[]/concepts[]` 与 evidence；M7：获批子集 |
| 未定义 | ApplicabilityRule AST 结构（738–743 只列 operator 集与 `ast_schema_version`）；L1/L2 表；模型调用方式 → D-08、D-11、D-12 |

### 2.5 M5 Automatic Validation（首纵切内）

| 项 | 内容 |
|---|---|
| 运行归属 | EditionRun，`stage=m5` |
| 冻结输入 | 【G7-RULINGS §9 第 2 条】`scope: corpus_only`：m3 包及其血缘输入（含 M3 自身冻结的 M1/M2），共 17 个修订；配置修订增加 `target_consumption_level` |
| 任务与 Checkpoint【草案】 | 每个门禁一个 task：`g1_source_replay, g2_coverage, g3_identity_evidence, g4_layering, g5_concept_retrieval, g6_rule_executability`，共 6 个 Checkpoint；无人工队列 |
| 输出 artifact_type【草案】 | 主内容 `gate_results`；阶段输出索引 `validation_package`；每 task 复用通用 `validation_report`（G7-RULINGS §9.1 第 24 条）；另有 `step_log` |
| payload【草案】 | `stage_payload_m5`：`{gate_results_revision_id, target_consumption_level, gate_status{G1..G6: passed/failed/blocked}, m5_gate_passed}` |
| counts【草案】 | `{checks_passed, checks_failed, checks_blocked, warnings, broken_relations, rework_tasks}`；content_sha256 = sha256(gate_results)；operation `validate_candidates` |
| Gate | G1–G5 全部、G6 前半由 M5 执行（【规格】588–603）；放行条件 606；fail-closed 608；blocked 的放行语义 → D-09 |
| 约束 | 不修改 Candidate、不生产 Tag 字段（580、610）；规则只用声明式 AST/YAML/JSON（612）；不用模型替代规则判断（580） |
| 下游消费约束 | 【G7-RULINGS §9 第 21 条】M5 StagePackage `validation.passed` 如实反映 Gate；下游消费 M5 包须同时满足所属 StepRun `succeeded` 与 `validation.passed == true` |
| 下游消费键 | M6：`gate_results.gates[].checks[]`、`rework_tasks[]`、`broken_relations[]`；M8：`known_defects` 取 blocked 项 |
| 未定义 | 输入清单、目标消费级别入参（D-02）；新失败类别的错误码（D-17） |

### 2.6 M6 Review & Curation（纵切后，不在首纵切）

| 项 | 内容 |
|---|---|
| 运行归属 | EditionRun，`stage=m6` |
| 冻结输入 | m4 `candidate_package`、m5 `validation_package`、m3 `corpus_package`【规格】618、624；M2 扫描与字框只读（629）；【草案】前置条件为 `m5_gate_passed=true` |
| 任务与 Checkpoint | 每个人工决定被 Ledger 接受后即时 1 个 Checkpoint【规格】843；【草案】`task_id = m6_review_<entity_id>_<decision_type>` |
| 人工挂起 | StepRun 转 `awaiting_human`，`pending_queue_artifact_ids` 指向 `review_queue` 修订【草案】；恢复语义按 §7.1 213–224 |
| 输出 artifact_type【草案】 | `human_event`（内容符合 `review_decision.schema.json`）、`correction_request`（629，退回 M2）、`rework_impact_report`（641）；主内容 `reviewed_edition`；阶段输出 `reviewed_edition_package` |
| payload【草案】 | `stage_payload_m6`：`{reviewed_edition_revision_id, decision_revision_ids, unresolved_count: 0}` |
| counts【草案】 | `{approved, rejected, decisions, correction_requests}`；content_sha256 = sha256(reviewed_edition)；operation `review_candidates` |
| Gate | 【规格】631 未解决项为 0；【草案】检查名 `decisions_complete, decision_anchor_pair(265), decision_types_closed(349–364), no_save_as_verified(889 回归)` |
| 人工队列 | 队列 4「M6 待签发」【规格】123 |
| 失效传播 | CorrectionRequest → M2 返工 → 按 §14.1 635–645 精确失效；`rework_round ≥ 3` 或单轮失效 ≥ 30% 时登记 `rework_threshold_exceeded`（642） |
| 未定义 | verdict 枚举与 content_status 迁移（D-14）；Review Console 与 Ledger 的写入通道（620，Flutter 客户端纵切后） |

### 2.7 M7 Incremental Knowledge Assembly（纵切后，不在首纵切）

| 项 | 内容 |
|---|---|
| 运行归属 | ReleaseRun（【规格】153–175），`stage=m7`；Ledger 归属 → D-04 |
| 冻结输入 | 既有 `canonical_snapshot` 修订（首个 Release 为空）+ ≥1 个 `reviewed_edition_package` 修订【规格】157–159 |
| 任务与 Checkpoint【草案】 | 每个 ReviewedEditionPackage 一个 `assemble_<rev>` task；每条人工合并裁决 1 个 Checkpoint |
| 输出 artifact_type【草案】 | `merge_proposal, alias_proposal, conflict_proposal, evidence_relation_proposal`（160、653）；`human_event`（归属 ReleaseRun 的合并 ReviewDecision，173）；主内容 `canonical_snapshot`；阶段输出 `assembly_package` |
| payload【草案】 | `stage_payload_m7`：`{canonical_snapshot_revision_id, previous_snapshot_revision_id|null, reviewed_edition_package_revision_ids, canonical_hash}` |
| counts【草案】 | `{concepts, assertions, proposals_auto, proposals_human, decisions}`；content_sha256 = sha256(canonical_snapshot)；operation `assemble_knowledge` |
| Gate | 【未定义】规格无 M7 Gate 条款；【草案】`proposals_resolved, sealed_edition_untouched(175), release_scoped_decisions(173), no_default_school_fold(570)` |
| 人工队列 | 队列 5「M7 待裁决」【规格】124 |
| 约束 | 保留同名异义、异名同义、多套规则、不同流派与相反结论（653）；不修改已封存的 ReviewedEditionPackage（175） |
| 未定义 | 首纵切是否包含（D-03）；Alignment/VariantReading（655）首纵切为单 Edition，不涉及 |

### 2.8 M8 Dataset Compilation（首纵切内）

| 项 | 内容 |
|---|---|
| 运行归属 | ReleaseRun，`stage=m8` |
| 冻结输入 | 【G7-RULINGS §2 D1-A 尾链、§9 第 3/15 条】首切片只读 M3 StagePackage 及其血缘输入（m1 `source_manifest`、m2 `ocr_page_set`/`ocr_page`）+ 薄 M1 登记的派生页图；TechniqueProfile 只有 `technique_profile_id="qizheng"` 字符串；发布范围/ReleasePolicy/消费级别写进配置修订键 `release_scope, release_policy, consumption_level` |
| 任务与 Checkpoint【草案】 | 首切片 4 个 task（`source_asset_pack, evidence_map_pack, release_manifest, validation_report`），每 task 一个 Checkpoint；纵切后随子包集合扩展 |
| 输出 artifact_type【草案】 | 首切片 5 个独立 Artifact（699）：`source_asset_pack`、`evidence_map_pack`、`release_manifest`（主内容）、`validation_report`、`publication_package`（阶段输出）；纵切后另有 `knowledge_data_pack`、`query_contract_pack`、`anchor_contract_pack`、`rule_index_pack`、`search_index_pack`、`graph_projection_pack`、`technique_profile_pack` |
| payload【草案】 | `stage_payload_m8`：`{release_id, consumption_level, release_manifest_revision_id, subpack_revision_ids{type: rev}, canonical_snapshot_revision_id}` |
| counts【草案】 | `{entries, assertions, evidence_chains, source_assets, subpacks}`；content_sha256 = sha256(release_manifest)；operation `compile_dataset` |
| Gate | 首切片只闭合尾链四段 SourceSpan→SourceAnchor→OcrPage→SourceAsset（705–713），三段知识链（KnowledgeEntry/Assertion/EvidenceLink）记 `knowledge_chain: "not_compiled"`；G6 复验（603）blocked、G7（604）；拒绝 `source_release=dev` 进入 PUBLIC_RELEASE（697）；消费级别只签发 `INTERNAL_DEMO`，`DEV_SEARCH`/`PUBLIC_RELEASE` 在 begin 之后以 `admission` 失败封存（670–678） |
| 下游 | APP 后端与客户端（黑箱外，§1 22–27）、注解社区锚点（`openspec/annotation-community`，`anc_` 三要素 731） |
| 未定义 | 子包范围、`min_app_version`、`source_release` 闭集（D-15）；KnowledgeEntry 主体选 Concept 还是 Pattern 的规则（86 只说「一个 Concept 或 Pattern」）；GraphProjectionPack 格式（纵切后） |

---

## 3. 需要新增的 JSON Schema（草案）

> 纵切后（P3）：首纵切内不向 `openspec/schemas/` 新增文件，以下结构以代码内草案契约表达，正式化随 impl-08 Contract Registry。

通用约束：Draft 2020-12；除特别说明外均为 `additionalProperties: false`；`schema_version` 复用 `artifact_ref.schema.json#/$defs/schemaVersion`（const `"1.0.0"`）；ID 与枚举复用 §3.1 的 `$defs`。文件平铺在 `openspec/schemas/` 下（便于 `verify.sh` 的 `--check-metaschema *.schema.json` 自动覆盖，并与 check-jsonschema 的相对 `$ref` 解析一致）。

### 3.1 `contract_common.schema.json`（只有 `$defs`，不单独校验实例）

| $def | 内容 | 来源 |
|---|---|---|
| `sourceId` `sourceSpanId` `assertionId` `propositionId` `sharedConceptId` `techniqueConceptId` `homographAnchorId` `patternId` `schoolId` `schoolViewId` `conflictGroupId` `entryId` `releaseId` | 正则逐字取 `pipeline/ledger/ids.py` PATTERNS | ids.py 14–34；规格 271–318 |
| `conceptId` | `oneOf[sharedConceptId, techniqueConceptId]`（不得为 `hg_`，550） | 549–550 |
| `contentStatus` | 7 值 | 339–347 |
| `reviewDecisionType` | 8 值 | 355–364 |
| `errorCode` | 9 值 | 370–380 |
| `gateCode` | `G1…G7` | 586 |
| `gateStatus` | `passed / failed / blocked`【草案】 | D-09 |
| `consumptionLevel` | `INTERNAL_DEMO / DEV_SEARCH / PUBLIC_RELEASE` | 666 |
| `evidenceLevel` | `offset_level / glyphbox_level` | 527–528 |
| `terminalState` | `manually_transcribed / known_unrecognizable / deferred` | 486–488 |
| `sourceAssetPolicy` | `full_scan / derived_page_images_only / reference_and_hash_only` | 719–721 |
| `anchorStability` | `permanent / migratable / best_effort` | 730 |
| `migrationChangeType` | `migrated / merged / split / retired` | 732 |
| `anchorableType` | `KnowledgeEntry / Assertion / SourceSpan / SourceAnchor` | 729 |
| `queueName` | `m2_anomaly_low_confidence / m3_boundary_dispute / m4_category_dispute / m6_pending_signoff / m7_pending_adjudication`【草案】 | 119–124 |
| `sha256Hex` | `^[0-9a-f]{64}$` | — |
| `box` | `{x, y, w, h}`，均为 number | spans.yaml 实际 |
| `sourceAnchor` | `{page, image_sha256, line_id, bbox: box, chars[{char_index, glyph_id, char, box}]}` | spans.yaml 实际；528 |
| `evidenceLink` | `{source_span_id, support_type: direct|interpreted, char_start ≥0, char_end ≥1, quote (minLength 1), quote_sha256}` | SCHEMA.md 52–54；G3 67–68；D-08/D-12 |
| `entityRevisionAnchor` | `{entity_id: string, artifact_revision_id}` | 265 |
| `omenCarrying` | `canonical / none` | 811 |

### 3.2 `candidate_set.schema.json`（M4 主内容）

必填顶层键及草案：

| 键 | 类型 / 约束 | 来源 |
|---|---|---|
| `schema_version` | const "1.0.0" | §8 |
| `source_id` / `edition_part_artifact_id` / `technique_id` | sourceId / artifactId / `^[a-z][a-z0-9]*$` | 271、290 |
| `corpus_package_revision_id` | artifactRevisionId | 207 |
| `span_layer` | `structural / semantic` | D-12 |
| `extraction_mode` | `fixture_rule / model_replay / model_live` | D-11 |
| `term_layers` | `{l1_hits[{surface, concept_id: sharedConceptId, span_id}], l2_hits[{surface, homograph_id, concept_id: techniqueConceptId|null, span_id, uncertain: bool}], l3_new_concept_candidates[{surface, span_ids[] minItems 1}]}`；`l2_hits` 中 `concept_id` 为 null 时 `uncertain` 必须为 true | 534–557 |
| `concepts[]` | `{concept_id: conceptId, canonical_name, aliases[], layer: L1|L2|L3, homograph_id: hg|null, mention_span_ids[] minItems 1, omen_carrying: omenCarrying|null, status: contentStatus}` | 90、549、811 |
| `patterns[]` | `{pattern_id, concept_id, assertion_ids[], status}` | 91、317 |
| `assertions[]` | `{assertion_id, proposition, proposition_id, subject_entity_id: conceptId|patternId, relation: supports|qualifies|opposes|corresponds|equivalent, evidence[evidenceLink] minItems 1, conditions[], exceptions[], school_ids[schoolId], canon_refs[sharedConceptId], layer: general|case|editorial, status: contentStatus}` | SCHEMA.md 44–66；G4 601；SEM_001 |
| `applicability_rules` / `cases` / `editorial_notes` | array，`maxItems: 0`（D-08 前锁死） | D-08 |
| `school_views[]` | `{school_view_id, school_id, subject_entity_id, claim_refs[assertionId], conflict_group_id|null, changes_current_judgment: bool, source_refs[sourceSpanId]}` | 570 |
| `uncertainties[]` | `{span_id, surface, reason}` | 550 |
| `model_run_revision_ids[]` | artifactRevisionId | 574 |

### 3.3 `gate_results.schema.json`（M5 主内容；M8 的 `release_validation_report` 复用）

| 键 | 约束 | 来源 |
|---|---|---|
| `stage` | `m5 / m8` | — |
| `technique_id`、`target_consumption_level` | — / consumptionLevel | 590 |
| `subject_revision_id` | artifactRevisionId（m5 为 candidate_package，m8 为 publication 前的 release_manifest） | — |
| `validators[]` minItems 1 | `{name, version}` | 606 |
| `gates[]` | `{gate: gateCode, status: gateStatus, checks[{check: snake_case, status: gateStatus, error_code: errorCode|null, detail, subject_ids[]}], blocked_reason: string|null}`；if `stage=m5` 则 gate ∈ G1..G6 且恰 6 项；if `stage=m8` 则 gate ∈ {G6, G7} | 588–604 |
| `release_checks[]` | 结构同 checks；只允许在 m8 出现（如 `evidence_chain_closure, anchor_migration_rate, source_release_not_dev`） | 715、734、697 |
| `broken_relations[]` | `{from_id, to_id, error_code}` | 606 |
| `rework_tasks[]` | `{task_id, target_entity_id, error_code, note}` | 606 |
| `summary` | `{critical_errors, failed_checks, blocked_checks, warnings, broken_relations, rework_tasks}`，均为非负整数 | 606 |
| `gate_passed` | bool | 606、D-09 |

### 3.4 `review_decision.schema.json`（`human_event` 内容）

`{decision_type: reviewDecisionType, verdict: accept|modify|reject|request_evidence|school_dispute, target: entityRevisionAnchor, stage: m3|m4|m6|m7, scope_consumption_level: consumptionLevel|null, rationale (minLength 1), modified_revision_id: rev|null, content_status_after: contentStatus|null, actor_ref}`；约束：`verdict=modify` 时 `modified_revision_id` 必填且非 null；`content_status_after=expert_verified` 时 `verdict` 必须为 `accept`。来源 265、351–364、618、622–625、830；D-14。

### 3.5 `reviewed_edition.schema.json`（M6 主内容）

`{edition_part_artifact_id, candidate_package_revision_id, validation_package_revision_id, approved[{entity_id, artifact_revision_id, content_status}], rejected[{entity_id, artifact_revision_id, decision_revision_id}], decision_revision_ids[] minItems 1, correction_request_revision_ids[], unresolved_count: const 0}`。来源 631。

### 3.6 `rework_impact_report.schema.json`（M6 / Orchestrator）

`{edition_part_artifact_id, trigger_correction_request_revision_id, rework_round ≥1, invalidated_count, carried_forward_count, needs_review_count, affected_queues[queueName], invalidated[entityRevisionAnchor], carried_forward[{entity_id, carried_from_revision_id}], needs_review[entityRevisionAnchor], threshold_exceeded: bool}`。来源 637–643。

### 3.7 `canonical_snapshot.schema.json`（M7 主内容）

`{technique_id, previous_snapshot_revision_id: rev|null, reviewed_edition_package_revision_ids[] minItems 1, edition_part_artifact_ids[] minItems 1, concepts[{concept_id, canonical_name, aliases[], source_entity_revisions[entityRevisionAnchor]}], assertions[{assertion_id, proposition, subject_entity_id, evidence[evidenceLink], school_ids[], status}], school_views[], conflict_groups[{conflict_group_id, school_view_ids[], changes_current_judgment}], proposals{merge[], alias[], conflict[], evidence_relation[]}（元素 {proposal_revision_id, resolution: auto|human, decision_revision_id|null}）, release_decision_revision_ids[], canonical_hash: sha256Hex}`。`canonical_hash` 规则【草案】：`sha256(json.dumps({"concepts","assertions","school_views","conflict_groups"}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))`。来源 160–165、653、725；D-04。

### 3.8 `release_manifest.schema.json`（M8）

`{release_id, previous_release_id: rel|null, technique_id, consumption_level, source_release: internal|dev|release, canonical_snapshot_revision_id, canonical_hash, schema_versions{name: "1.0.0"}, profile_versions{fact_set_profile: string|null, ast_schema_version: string|null}, min_app_version, release_policy: sourceAssetPolicy, rights[{source_id, rights_status, distribution_note}], subpacks[{artifact_type, artifact_revision_id, sha256, byte_size}] minItems 1, source_revision_reconciliation[{source_id, edition_part_artifact_id, corpus_spans_sha256, reviewed_edition_package_revision_id}] minItems 1, known_defects[string], watermark: bool, retired_anchor_disclosures[{from_entity_id, orphaned_reason}], anchor_migration_rate: number[0,1]|null}`。约束：`consumption_level=PUBLIC_RELEASE` 时 `source_release` 不得为 `dev` 且 `anchor_migration_rate` 必须为 1；`INTERNAL_DEMO` 时 `watermark` 为 true 且 `known_defects` minItems 1。来源 676–678、697、734；D-15。

### 3.9 `knowledge_data_pack.schema.json`

`{release_id, technique_id, consumption_level, watermark: string|null, entries[{entry_id, subject_entity_id: conceptId|patternId, title, assertion_ids[] minItems 1, school_view_ids[], content_status, mark_binding{omen_carrying|null, condition_affordance: array|null, school_variance_display: array|null, changes_current_judgment: bool|null}}], concepts[{concept_id, name, basic_imagery: string|null}]（最小盘面概念字典，additionalProperties false，不含规则 DSL）, assertions[{assertion_id, proposition, subject_entity_id, status}], school_views[], conflict_groups[{conflict_group_id, school_view_ids[], first_layer_display: bool}]}`。`INTERNAL_DEMO` 时 `watermark` 非 null；`PUBLIC_RELEASE` 时 `entries[].content_status` 与 `assertions[].status` 必须为 `expert_verified`。来源 24–27、92、676–678、713、736、782–815。

### 3.10 `evidence_map_pack.schema.json`

`{release_id, chains[] minItems 1}`；每条 chain 必须恰含 7 个键 `entry_id, assertion_id, evidence_link{assertion_id, source_span_id, char_start, char_end, quote_sha256}, source_span{source_span_id, source_id, page, start_offset, end_offset, text}, source_anchor: sourceAnchor, ocr_page{page, glyph_ids[] minItems 1}, source_asset{page, image_sha256}`。JSON Schema 无法约束键序，**键序由 fixture `verify.sh` V11 与 M8 验收检查**。来源 705–714。

### 3.11 `source_asset_pack.schema.json`

`{release_id, policy: sourceAssetPolicy, assets[{source_id, page, image_sha256, width, height, ref{object_store: local|authorized_backend, path_ref}, rights_note, bytes_included: bool}] minItems 1}`；`policy=reference_and_hash_only` 时 `bytes_included` const false。来源 717–723、944；D-16。

### 3.12 `anchor_contract_pack.schema.json`

`{release_id, anchorable_types[anchorableType]（恰 4 项）, stability{KnowledgeEntry: const migratable, Assertion: const migratable, SourceSpan: const permanent, SourceAnchor: const permanent}, anchor_required_fields: const ["entity_id","artifact_revision_id","release_id"], identity_migration_map{release_id, previous_release_id|null, entries[{from_entity_id, to_entity_ids[], change_type, release_id, reason_ref, span_allocation: array|null, orphaned_reason: string|null}]}}`；条件约束：`retired` 时 `to_entity_ids` 为空且 `orphaned_reason` 非 null；`split` 时 `to_entity_ids` 至少 2 项且 `span_allocation` 非 null；`migrated/merged` 时恰 1 项。来源 727–734。

### 3.13 `query_contract_pack.schema.json`

`{release_id, contract_version, interfaces[{name: getEntry|getSourceSpan|searchKnowledge|matchFacts, params[string], returns: string}]（恰 4 项且名字不重复）, backward_compatible: const true}`。来源 745–751。

### 3.14 `stage_payload_m4..m8.schema.json`（D-05 取 A 时）

五份，键见 §2.4–§2.8 的 payload 行；全部 `additionalProperties: false`，禁止出现以 `_path` 结尾的键（`propertyNames: {not: {pattern: "_path$"}}`）。

### 3.15 不在本包范围

`rule_index_pack / search_index_pack / graph_projection_pack / technique_profile_pack`（规格字段不足，纵切后，D-15）；四类 Proposal、`model_run`、`term_layer_report`、`correction_request`、`review_queue`（由 M4/M6/M7 包各自起草，回填到本表 §4）。

---

## 4. artifact_type 总表（在 Contract Registry 落地前充当临时闭集，D-10）

登记纪律：唯一登记处为本表，直至 impl-08 Contract Registry 接管（P2）；同一时刻只有一路写本表。未入本表的类型名，实现不得使用；M5 任务级报告已按 G7-RULINGS §9.1 第 24/26 条删除，每 task 复用通用 `validation_report`。

| 阶段 | artifact_type | 角色 | 内容 Schema | 状态 |
|---|---|---|---|---|
| 通用 | `configuration` / `technique_profile` | 运行配置（put_run_artifact） | — | 【实际】 |
| 通用 | `validation_report` / `step_log` / `failure_report` | 每个 StepRun 的自检、日志、失败；M5 每 task 复用 `validation_report` | — | 【实际】 |
| 通用 | `human_event` | 人工决定（含 ReviewDecision） | `review_decision`（纵切后，M6） | 【实际】类型；【草案】内容 |
| Ledger | StepManifest、StageCheckpoint、StagePackage 修订 | Ledger 内部 | — | 【实际】以 service.py 为准 |
| M1 | `source_manifest` | 任务级 + 阶段输出 | — | 【实际】 |
| 薄 M1 | `source_asset_page` / `source_asset_register` | 派生页图字节（rights_scope=internal）/ 页图登记 | 代码草案（P3） | 首纵切（impl-04 shim，D2；impl-09 M1 落地后替换） |
| M2 | `ocr_page` / `ocr_page_set` | 任务级 / 阶段输出 | — | 【实际】 |
| M3 | `corpus_batch` / `corpus_spans` / `coverage_report` / `corpus_package` | 任务级 / 主内容 / 报告 / 阶段输出 | — | 【实际】 |
| M4 | `candidate_batch` / `model_run` / `candidate_diff_report` / `candidate_set` / `candidate_package` | 任务级 / 模型留痕 / 差异 / 主内容 / 阶段输出 | candidate_set | 纵切后（D-11） |
| M5 | `gate_results` | 主内容 | 代码草案 0.1.0-draft（P3） | 首纵切（§9 第 10 条） |
| M5 | `validation_package` | 阶段输出索引 | 代码草案（P3） | 首纵切（§9 第 10 条） |
| M6 | `review_queue` / `correction_request` / `rework_impact_report` / `reviewed_edition` / `reviewed_edition_package` | 队列 / 退回 / 失效报告 / 主内容 / 阶段输出 | rework_impact_report、reviewed_edition | 纵切后（D-14） |
| M7 | `merge_proposal` / `alias_proposal` / `conflict_proposal` / `evidence_relation_proposal` / `canonical_snapshot` / `assembly_package` | 提案 / 主内容 / 阶段输出 | canonical_snapshot | 纵切后（§9 第 3 条） |
| M8（首纵切） | `source_asset_pack` / `evidence_map_pack` / `release_manifest` / `publication_package` | 子包 / 主内容（release_manifest）/ 阶段输出 | 代码草案（P3）；ValidationReport 复用通用 `validation_report` | 首纵切（D4、§9 第 15 条） |
| M8（纵切后） | `knowledge_data_pack` / `query_contract_pack` / `anchor_contract_pack` / `rule_index_pack` / `search_index_pack` / `graph_projection_pack` / `technique_profile_pack` | 子包 | 纵切后 | 纵切后（D-15） |

---

## 5. 并行实现依赖图与派发批次

```text
L0 契约（已冻结）  L1 Ledger（impl-01 ACCEPTED）  M3 结构层（impl-02 返工中）
        │
批次 0（串行）impl-00/10：INTERFACES §4 临时闭集登记与首纵切裁决对齐（首纵切唯一 ACT）
        │         （纵切后）原 K1 Schema → K2 金标 + verify → K3 golden ingest 全部 DEFERRED
        │         （并行进行：impl-02 ACT 05 返工，只写 corpus_compiler，与本包无写冲突）
        ▼
批次 1（契约冻结后并行；每个包都用 ingest(stages=前缀) 灌金标上游作输入，比对本阶段金标投影）
  ├─ A  M5 impl-03           输入 m1..m4 金标 → 比对 m5
  ├─ B  M8 impl-04           输入 m1..m7 金标 → 比对 m8（D-03/D-04/D-15/D-16）
  ├─ C  M4 薄接入            输入 m1..m3（可用 run_m3 真实输出）→ 比对 m4（D-11/D-12）
  ├─ D  M6 薄接入            输入 m1..m5 金标 → 比对 m6（D-14）
  ├─ E  M7 薄直通            输入 m1..m6 金标 → 比对 m7（D-03/D-04）
  ├─ F  M1/M2 薄接入         只替换 fixture_ingest 的 m1/m2 常量路径，输出契约不变
  ├─ G  Contract Registry 最小版：load_schema、artifact_type 闭集、golden_projection（D-06/D-10/D-13）
  └─ H  M3 语义层            D-12 取 A 时可并行；只能新增 payload 版本，不得改 spans.yaml
        │
批次 2（串行，端到端）：真实 M1→M6 EditionRun，再 M7→M8 ReleaseRun，逐段用真实上游替换金标；
        最薄驱动脚本；此批次才改 run_all.sh（20.1 / 20.4 / 20.8 的判定）
        │
批次 3：Local Orchestrator 状态机与六项只读查询（116–127）；D-01 裁定后的真实页范围
```

**必须串行的**：K1→K2→K3（金标要过 Schema；ingest 要读金标）；批次 2 各段（真实上游替换）；G 的 `load_schema` 须早于 A–E 中任何一个在生产代码里加载新 Schema 的 ACT（它们可以先写纯函数与测试）。

**可以并行的理由**：A–E 的输入全部来自已冻结的金标，互不读取对方的实现；输出只和本阶段金标投影比对。

**写入热点归属（D-13 推荐）**

| 文件 | 唯一写入方 | 其他包 |
|---|---|---|
| `pipeline/ledger/fixture_ingest.py` | impl-00 ACT 09 → 之后归 Orchestrator | 只调用 |
| `pipeline/corpus/_fixture/mini_ed01/**` | impl-00 | 只读；需要新金标就另立 impl-00 后续包 |
| `openspec/schemas/*.schema.json`、`verify.sh` | impl-00 → 之后归 Contract Registry | 只读 |
| `openspec/acceptance/run_all.sh` | 批次 2 端到端包 | 各包只新增自己的 §19.0 脚本 |
| `pipeline/ledger/service.py` | Ledger 维护包 | 不得各自扩 `_load_validator` 或 `RUN_ARTIFACT_TYPES` |

---

## 6. 给并行草案的对账清单

每个模块草案在 README 的「上游输入契约 / 下游输出契约」中应能逐条勾对以下项；对不上就引用条目号上报。

1. 【I-1】冻结输入的 artifact_type 与 §2 卡片一致；M5 为 6 个修订（D-02），M8 另冻结 `corpus_spans` 与 `source_manifest`（D-03）。
2. 【I-2】输出采用「主内容 + 阶段输出索引」双修订；StagePackage `manifest.output_artifacts[0]` 指向索引修订；`content_sha256` = sha256(主内容字节)（D-05/D-10）。
3. 【I-3】payload 键与 `stage_payload_mN.schema.json` 一致，不含 `*_path`（D-05）。
4. 【I-4】Checkpoint `task_id` 命名与 §2 卡片一致；人工阶段每个决定 1 个 Checkpoint（843）。
5. 【I-5】验收脚本以 `ingest(stages=上游前缀)` 取金标上游，比对本阶段金标的**身份归一化投影**（D-06），并永远调用仓库内规范 `verify.sh`。
6. 【I-6】门禁代号只用 G1–G7，放在 M5（G1–G6）或 M8（G6 复验、G7）；阶段 Gate 不冠 G 代号；错误码只用 9 个（D-17）。
7. 【I-7】ReviewDecision 即 `human_event` 修订，`decision_type` 取 8 类，内容符合 `review_decision.schema.json`，并同时带 `entity_id` 与 `artifact_revision_id`（265、D-14）。
8. 【I-8】m7/m8 属 release_run，`edition_part_id` 取首个 Part（D-04）。
9. 【I-9】生产代码经 Contract Registry `load_schema(name)` 加载新 Schema；不得修改 Ledger 私有 loader（D-13）。
10. 【I-10】不新增 ID 前缀；无前缀对象按 D-08 取身份；`applicability_rules / cases / editorial_notes` 在 v1.0.0 中锁 0。
11. 【I-11】quote hash = sha256(quote 的 UTF-8 字节)；evidence 的 `char_start/char_end` 相对所引 span 的 `text`（D-12）。
12. 【I-12】目标消费级别为 INTERNAL_DEMO 时 blocked 门禁可放行，但必须在 gate_results 与 ReleaseManifest `known_defects` 逐条披露；DEV_SEARCH/PUBLIC_RELEASE 时 blocked 视同 failed（D-09）。
13. 【I-13】M5 等下游解析上游 StagePackage 时只接受所属 StepRun 状态为 `succeeded` 的包（impl-02 ACCEPTANCE §5.3 登记的下游约束）。
