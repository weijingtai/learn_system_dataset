# impl-06：M6 Review & Curation 最薄接入（§14、§14.1、§16.3.2、§22.3）

状态：`READY_FOR_REVIEW`（W5-H 定稿 2026-09-13，依 `G7-RULINGS.md` §1 P1–P9、§4 impl-06、§9.3 第 34–43 条、§9.5 第 45–46 条、§9.6–§9.11 第 47–58 条；未经实现；派发前置见 §7 与 `PROMPT-H1.md`）。

## 1. 目标

在 `pipeline/review/` 落地规格 §14 的 M6 **最薄接入**与 §14.1 精确失效传播的首切片（`G7-RULINGS` §4：D-02 采纳 CLI、D-11 采纳 fixture 金标注入）：

1. 从 Artifact Ledger 冻结读取 M3 `corpus_package`/`corpus_spans`、M4 `candidate_package`/`candidate_set`、M5 `validation_package`/`gate_results`，按 `review_events.required_decision_types` 逐对象推导必审类型并确定性生成审核队列（第 67 条）。
2. 复用 impl-05 已冻结的 `pipeline.knowledge_extraction.review_events`（`build_review_decision`/`required_decision_types`/`derive_content_status`，§8.2 八类 × D-08 verdict 闭集），把每条人工决定写成不可变 `human_event` 修订，**每条决定被 Ledger 接受后即时写一个 StageCheckpoint**（§17.1:840-846）。
3. 以独立实现的 M6 Review Gate 判定零未解决项，产出 `reviewed_edition`（主内容）、`reviewed_edition_package`（阶段输出）与 m6 StagePackage，并登记带全部人工决定的 Transformation（§20.3）。
4. 最薄 Review Console：命令行 `python -m pipeline.review`（D-02 A），只读对照原文/字框锚点/校验结果，执行接受、修改、驳回、补证、流派分歧与 CorrectionRequest。
5. 精确失效传播：按对象级引用血缘机器判定失效/继承/待复核，封存 `ReworkImpactReport`，复审只重放待复核项（§14.1:633-645）。
6. （依第 61 条，D-01 归 M7）Snapshot 不在本包：`CanonicalKnowledgeSnapshot` 由 M7 创世汇编薄切片产出（impl-07 先行）；落地前相关验收项 BLOCKED（本包删除 ACT 10）。

M4 已实现（impl-05 `ACCEPTED`，`pipeline/knowledge_extraction/**`），M5 已实现但 `scope: corpus_only`（`pipeline/validation/**`）；M5 尚未消费 M4 候选，candidate 级校验由 M6 自身独立完成。本包对**尚不存在**的部分——真实 `expert_verified` 签发（P7）、M4' 重跑与 M5' 候选校验——以非生产测试桩与合成金标推进（D-11），并在验收中如实 BLOCKED（第 52/53 条标注）。

完成判据（本批唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/review/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"   # OK（用例 ≥ 129）
bash openspec/acceptance/m6-data-fields.sh; echo exit=$?
# 期望：11 行 PASS + BLOCKED snapshot_projection（第 61 条）+ BLOCKED legacy_workbench_seed + BLOCKED upstream_real
#       末行 SUMMARY pass=11 fail=0 blocked=3；exit=2
bash openspec/acceptance/run_all.sh | tail -1      # 与开工基线逐字相同（本批不改 run_all.sh，D-17）
bash openspec/acceptance/m3-coverage.sh | tail -1  # 与开工基线相同（不得回退）
```

返回 2 而非 0 的原因：M5 仍是 `corpus_only`（candidate 级校验缺失）、Snapshot 归 M7 创世汇编（第 61 条，本包未落地）、旧工作台数据体（§19:880，`original_text` 非空 0/496）未迁入、真实人工签发由用户撰写（P7）。

## 2. 依据（只读来源，文件:行号）

### 2.1 规格 `openspec/learn-system-blackbox-architecture.md`

- §5:103-110（M1→M8）、§5:119-124（第 4 队列「M6 待签发」）、§5:126（ReworkImpact）、§5:130（Review Console 不是第九 Module）
- §6.1:138-149（ReviewedEditionPackage 在链上）、§6.2:153-175（Snapshot 由 ReleaseRun/M7 产出）
- §7:181-207（StepRequest/StepResult、只读冻结修订）、§7.1:209-226（一阶段多任务、`awaiting_human`、`record_human_event`、`resume`）
- §8:232-243（StagePackage 信封）、§8.1:257-267（`entity_id` 与 `artifact_revision_id` 双锚）、§8.1:288-322（UUIDv4/人工闭集前缀）
- §8.2:335-347（内容成熟度 7 态）、§8.2:349-364（ReviewDecision 8 类）、§8.2:384-404（Artifact status）、§8.2:432-440（四轴正交）
- §14:614-631（M6 输入、动作、Console 模式、CorrectionRequest、输出）
- §14.1:633-645（精确失效传播全文；`:638` 失效对象、`:639-640` 继承/待复核、`:641-642` 计数与阈值、`:643` 禁止整队列批量失效）
- §16:661-678（M8 冻结 Snapshot 输入、消费级别门槛）、§16:725（`canonical_hash`）、§16.3.2:813-815（M6 供给 `school_variance_display` 与「是否改变当前判断」）
- §17:826-836（本地进程、ActorProvider、事务序列）、§17.1:840-846（人工阶段每次决定即时 Checkpoint）
- §18:852-859（LineageGraph 含审核决定）
- §19:880（M6 行）、§19:884（Local Orchestrator 缺失失效传播）、§19.0:910（`m6-data-fields.sh`）
- §20:937（20.1）、§20:943（20.7）、§20:944（20.8）、§20:945（20.9）、§22.1:966-969（统一验收宿主）、§22.2:973-984、§22.3:991（M6 薄用「只读对照与签发」）、§22.4:1000（失效传播先以 Ledger 事件记录）

### 2.2 已落地代码（只读；本包不得修改）

- `pipeline/knowledge_extraction/__init__.py:16-27`：`M4_TOOL`、`CANDIDATE_SCHEMA_VERSION="0.1.0-draft"`、`CATEGORIES`、`M4_STATUS_CEILING`
- `pipeline/knowledge_extraction/review_events.py:16`：`VERDICTS = (accept, modify, reject, request_evidence, school_dispute)`（D-08）；`:18-23` `ENTITY_KINDS`；`:24` `REVIEW_STAGE="m6"`；`:26-41` 事件顶层键（**校验拒绝多余键**）；`:43` `build_review_decision`；`:80` `validate_review_decision`；`:144` `required_decision_types`；`:152` `derive_content_status`
- `pipeline/knowledge_extraction/inputs.py:58` `latest_succeeded_step_run`（同阶段后续运行经 supersede，第 32/58 条）；`:115` `resolve_m3_outputs`；`:186` `m4_is_sealed`；`:245` `resolve_m4_inputs`
- `pipeline/knowledge_extraction/step.py:268-283`：`candidate_package` 内容（`candidate_set_revision_id`、`candidate_set_sha256`、`corpus_stage_package_revision_id`、`spans_revision_id`、`technique_profile_revision_id`、`gate_profile`、`span_layer`、`cross_model`、`term_layering`）；`:311-362` m4 StagePackage（`payload`、`manifest.counts`=candidate_set.counts、`content_sha256`=candidate_sha256）；`:373-390` `finish_step_run` 的 `output_artifact_ids=[stage_package, candidate_set, candidate_package]`；`:1-6` 同阶段后续运行经 `supersede_step_run`
- `pipeline/validation/package.py:52` `assemble_gate_results`（`scope`、`gates{G1..G7}`、`passed_checks`、`failures`、`warnings`、`broken_relations`、`rework_tasks`、`not_evaluated`、`gate`、`counts`）；`:171` `assemble_validation_package`（`gate_results_revision_id`、`corpus_package_revision_id`、`corpus_spans_revision_id`、`candidate_package_revision_id: None`、`gate`）
- `pipeline/validation/step.py:59` `run_m5(service, edition_part_id, *, target_consumption_level="INTERNAL_DEMO")`；`:251` `scope: corpus_only`；`:275` StagePackage `validation.passed` 如实反映 gate（第 21 条）
- `pipeline/dataset_compiler/packs.py:35` M8 四 task；`:262` `knowledge_chain: "not_compiled"`；`:301-307` `knowledge_chain_not_compiled` 缺陷；`:71` `source_asset_pack`、`:144` `evidence_map_pack.entries`（`knowledge_chain` 前三段）
- `pipeline/dataset_compiler/gate.py:392-404` `knowledge_chain` 检查（`not_compiled` → `not_evaluated`；声称 `compiled` → 失败）；`:434` `knowledge_chain: not_evaluated`
- `pipeline/contract_registry/registry.yaml:44-133`：首纵切登记 m1/m2/m3/m5/m8 五个 Module，**无 m6 行**；`catalog.py` Module 描述符键（`module_id, stage, kind, binding, entry, version, consumes, produces, human_queue, supports_recovery, entry_kwargs, owns_processing_run`）、`module_for(stage)` 唯一
- `pipeline/orchestrator/gate.py:14-23` 八项 Stage Gate 检查；`effective_step_runs`（第 45 条 carrier 判定）；`_read_package_content` 用 `yaml.safe_load`（第 57 条）
- `pipeline/orchestrator/module.py`：`ModuleBinding`、`binding ∈ {step_request, legacy_self_driving, imported}`、`StepOutcome`（`awaiting_human` 须带非空 `pending_queue_artifact_ids`）
- `pipeline/ledger/service.py`（impl-01 已验收，只读调用）：`put_artifact` 442-526（`artifact_type` 正则 `^[a-z][a-z0-9_]*$` 459；返回二元组）；`put_run_artifact` 528-597（只收 configuration/technique_profile，写入即 sealed）；`seal_revision` 599-638；`invalidate_revision` 664-676（**只作用于整条修订**）；`supersede_revision` 678-716（同 artifact、新修订 sealed、`prev` 指向旧）；`register_stage_package` 718-774；`record_transformation` 777-843（`human_event_revision_ids` 只收 `human_event`，822-829；输出必须属本 StepRun）；`await_human` 885-920；`record_human_event` 922-963（**不消费 token**）；`resume` 965-989；`create_processing_run` 319-345（kind ∈ edition_run/release_run）；`supersede_step_run` 412-440；`write_checkpoint` 1364-1398（`_write_checkpoint_locked` 1280-1285：阶段被 succeeded 运行封存后只允许 supersedes 链续写）；`_backfill_checkpoint_if_needed` 1400-1428；`recover_from_checkpoint` 1430-1482（**不迁移旧运行终态**）；`finish_step_run` 1132；`fail_step_run` 1187
- `pipeline/ledger/states.py`：`CONTENT_MATURITY`、`REVIEW_DECISION_TYPES`（8 类）；`pipeline/ledger/store.py:160-179`：`human_events`、`stage_checkpoints.rework_impact_report_revision_id`
- 参考先例：`docs/blackbox-spec-rework/work-items/impl-05-knowledge/`（已四查定稿样式、`PROMPT-G1.md`、`acceptance.py`/`m4-stage-gate.sh`）、`impl-04-dataset/`（知识链 `not_compiled`）

## 3. 范围

写（全部新建）：`pipeline/review/**`（含非生产 `testing/` 与 `tests/`）、`openspec/acceptance/m6-data-fields.sh`（ACT 11）。

主 Agent/impl-00 写（执行者不写）：INTERFACES §4 登记本包新 artifact_type（impl-00 act/13）、fixture m6 金标独占 ACT（若加 fixture 金标）。Snapshot 归 M7（第 61 条）。

禁止：改规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/knowledge_extraction/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`pipeline/orchestrator/**`、`pipeline/contract_registry/**`、`openspec/acceptance/run_all.sh`、`m3-coverage.sh`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、`G7-*.md`、其他 work-items、任何 `ACCEPTANCE.md` 的 §5、`pattern_knowledge_workbench/`；新增依赖、新增 ID 前缀、调用模型 API；执行者写台账、写 `ACCEPTED`、伪造人工签发（P7）。

前置：impl-05 `ACCEPTED`（`pipeline/knowledge_extraction/**` 可用）；impl-03 `ACCEPTED`（M5）；D-01（第 61 条）、D-08（第 62 条）已由 `G7-RULINGS` §9.12 裁定；其余 D-02～D-18 见 §4。

## 4. 主 Agent 决定（执行者不重议）

裁决来源：`G7-RULINGS` §1 P1–P9、§4 impl-06、§9.3 第 34–43 条、§9.5 第 45–46 条、§9.6–§9.11 第 47–58 条。**未单列的细节默认采纳原草稿推荐**；与已落地 impl-05 契约冲突处以 §4.2 的定稿为准。

- **D-02 Console 形态 → A**。命令行 `python -m pipeline.review`（子命令 open/queue/show/decide/decide-batch/correct/close/recover/rework/rework-open），零新依赖，`§22.3:991` 只要求「只读对照与签发」。
- **D-03 ReviewDecision 结构 → 复用 impl-05 已冻结契约**。不新造 verdict 闭集；`verdict ∈ {accept, modify, reject, request_evidence, school_dispute}`（`review_events.py:16`），事件顶层键逐字取 `review_events.py:26-41`（校验拒收多余键，故 `standing`/`carried_from_revision_id` **不得**写进 `human_event` 内容，只存 M6 运行内的 `reviewed_edition`/Checkpoint）。
- **D-04 必审维度 → 由 `review_events.required_decision_types` 推导（第 67 条）**。必审类型以已验收 impl-05 `pipeline.knowledge_extraction.review_events.required_decision_types` 为唯一来源（P9），**M6 不另立映射**：逐对象调用（`review_source_fidelity` 恒必需；`school_view` 或 `school_ids` 非空时另需 `review_school_attribution`）。合成队列 4 对象（3 assertion + 1 school_view）→ **5 项**（school_view 含 source_fidelity）。推导结果写进运行配置修订 `required_decision_types`（entity_id → 类型列表）可审计；`expert_verified` 由 `derive_content_status` 推导（P7：仅合成测试替身可触发，验收如实 BLOCKED）。
- **D-05 失效粒度 → 修订级失效 + 对象级逻辑登记（因 P9 修正原草稿）**。impl-05 已把候选放在**单条** `candidate_set` 修订内（`step.py:208-215`），不存在逐对象 `knowledge_candidate` 修订；因此 §14.1:638 的「把可达 Candidate 置 invalidated」以 **`ReworkImpactReport.invalidated[]` 逐对象登记**表达，`candidate_set` 修订的物理替换由 M4' 重跑（`supersede_revision`，同 artifact + prev 指针）完成；M6 不逐对象 `invalidate_revision` 整条 `candidate_set`（§14.1:643）。
- **D-06 `carried_forward`/`needs_review` → A（不进 Ledger 状态表）**。作为 M6 内容（`reviewed_edition.decisions[].standing`、Checkpoint）字段，不进 §8.2 五状态；不改规格。
- **D-07 规范化内容哈希与「被修正 Span」判定键 → A**。Span 变更键 = `text` + `source_anchor`（页、图像哈希、行号、行框、逐字框），**排除** `start_offset/end_offset/batch_id`；对象内容哈希 = 对象字段（剔除修订号/成熟度/模型运行引用）+ 解引用的引文文字，`json.dumps(sort_keys=True, ensure_ascii=False, separators=(",",":"))` 后 SHA-256。
- **D-09 计数口径 → A（逐类明细；首切片校验条目为空）**。`invalidated_count` = 可达候选对象数 + 可达校验条目数；`carried_forward_count` = 不可达候选数 + 继承决定数；`needs_review_count` = 降级决定数；`valid_object_count` = 修正前有效候选对象数 + 校验条目数；阈值 `rework_round ≥ 3` 或 `ratio ≥ 0.30`；告警写入 `warnings`，复审须显式 `acknowledge_rework_warning=True` 并写成 `human_event`（`event_kind=rework_threshold_ack`）。**首切片 M5 `scope: corpus_only`**（`pipeline/validation/step.py:251`）**无 candidate 级校验条目**，`validation_entries=[]`，故 BDD 3.1 取 `invalidated_count=3`、`valid_object_count=4`；candidate 级校验条目随 M5 读 M4 的扩展到位（接口需求见 §5.1）。
- **D-10 CorrectionRequest → A**。`artifact_type=human_event`、内容 `event_kind=correction_request`（经 `record_human_event`，`decision_type=None`），列出 `source_span_ids`、`target_stage="m2"`；不阻断后续决定与结审，结审包登记 `correction_request_revision_ids`。**不新增 `correction_request` artifact_type**（与 INTERFACES §4 M6 行现列的 `correction_request` 不同，见 §4.2 对账）。
- **D-11 M4/M5 缺席时的注入 → A**。非生产子包 `pipeline/review/testing/` 以真实 Ledger 写路径注入 M4' 重跑、M5' 候选校验与合成决定；合成人工决定须显式标注 `synthetic_fixture: true`（第 52 条），M5/M6/消费级别判定不得计为真实 `expert_verified`（第 53 条）；验收以 `upstream_real` 行 BLOCKED 如实标注。
- **D-12 验收脚本 → A**。实现 `m6-data-fields.sh`（11 项 PASS + `snapshot_projection`（第 61 条）+ `legacy_workbench_seed` + `upstream_real` 三项 BLOCKED，本批 exit 2），沿用 impl-02/impl-05「脚本=§19.0 判据、本批返回 2」先例。
- **D-13 新 artifact_type → 只提名，登记由该波独占 ACT 写 INTERFACES §4（P2）**。提名：`review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report`（登记见 impl-00 `act/13.yaml`）。复用：`human_event`、`configuration`、`validation_report`、`step_log`、`failure_report`、`stage_package`。**不提名** `correction_request`（D-10）。Snapshot 类型归 M7（第 61 条）。
- **D-14 返工 StepRun 链 → A**。单线链 `首审 review（succeeded）← 失效传播 rework_propagation（succeeded，无 StagePackage）← 复审 review（succeeded，新 m6 包）`；上游旧修订须在失效传播 StepRun 冻结之后才可 `superseded`。`stage_progress` 对不产 StagePackage 的 succeeded 运行不判 M6 Gate 通过（`orchestrator/gate.py` carrier 判定，第 45 条）。
- **D-15 `recover_from_checkpoint` 不迁移旧运行 → A（P9 修正原草稿）**。Ledger 不改；本包照用，旧运行保持 `awaiting_human`，测试断言现状（`service.py:1430-1482`）。
- **D-16 `resume_token` 跨进程保管 → A + C**。`open`/`recover` 打印 token，后续显式 `--resume-token`；另提供 `decide-batch --from-file`（逐条落事件、逐条 Checkpoint）。
- **D-17 run_all 与 20.3 → A**。本批不改 `run_all.sh` 与 `pipeline/ledger/acceptance.py`；在 `acceptance.py` 中对 M6 Transformation 复刻 20.3 八项；登记「20.3 计数硬编码需在全链落地时泛化」为后续项。
- **D-18 契约对账 → A**。以 impl-05/impl-03 已落地契约为唯一来源；本包 §5 按实际代码逐字改写（见 §4.2）。

### 4.1 已由 G7-RULINGS §9.12/§9.14 裁定（记录，执行者不重议）

**第 61 条（D-01）｜CanonicalKnowledgeSnapshot 归 M7。** Snapshot 归 ReleaseRun/M7（§6.2:153-175）；M7 创世汇编薄切片由 impl-07 先行。本包**删除 ACT 10**（`act/10.yaml` 标 `status: WITHDRAWN`，保留备查），不产 `canonical_knowledge_snapshot`；Snapshot 相关验收项 `snapshot_projection` 在 M7 创世汇编落地前**恒 BLOCKED**，说明逐字「前置缺失: M7 创世汇编」。

**第 62 条（D-08）｜采纳 B。** M6 **不**调用 `invalidate_revision` 改 M4 修订状态；失效以 `ReworkImpactReport.invalidated[]` 逐对象登记，旧 `candidate_set` 由 M4' 重跑经 `supersede_revision`（`service.py:678-716`）替换。验收项 `no_cross_module_status_change` 据此判定 Ledger 无修订被 M6 置为 `invalidated`。

**第 67 条（F1/D-04）｜队列以 `review_events.required_decision_types` 为唯一来源。** M6 不另立映射；BDD/期望/计数按推导重算：合成 4 对象（3 assertion + 1 school_view）→ 队列 **5 项**（school_view 含 source_fidelity），首审 5 决定 / 6 Checkpoint，失效计数 **3/3/3/4/0.75**，复审队列 3 项（active 3 / carried_forward 2）。

**第 68 条（F2）｜事件锚点恒为 `seen_revision_id`。** `modify` 决定另携 `modified_revision_id`，纳入 `decision_entry` 键集并由 Gate `decision_anchoring` 校验存在性；act/01/02/05 与 BDD 1.3/5.5 统一。

### 4.2 草稿与已落地代码的对账（定稿修正清单）

| # | 草稿假设 | 已落地事实（文件:行号） | 定稿处理 |
|---|---|---|---|
| C1 | M4 每对象一个 `knowledge_candidate` 修订（D-05） | `step.py:208-215` 单条 `candidate_set` 修订；无 `knowledge_candidate` | 改为「修订级 + 对象级逻辑登记」（§4 D-05） |
| C2 | 候选包索引含 `candidates[{entity_id, kind, candidate_revision_id}]` | `step.py:268-283` 索引只有 `candidate_set_revision_id` 等 13 键 | `resolve_m6_inputs` 从 `candidate_set.assertions[]`/`school_views[]` 取对象 |
| C3 | M5 `gate{passed,severe_error_count,failed_task_count,pending_rework_count}` + `entries[{entity_id,…}]` | `validation/package.py:52-169` `gate_results` 用 `gates{G1..G7}`、`gate`、`counts`；`package.py:171-197` `validation_package` 绑 `candidate_package_revision_id: None` | Gate 的 `validation_intake` 改用 `validation_package.gate` 与 m5 StagePackage `validation.passed`；candidate 级校验由 M6 自算 |
| C4 | M5 校验候选、绑定候选包 | `validation/step.py:59,251` `scope: corpus_only`；`package.py:190` `candidate_package_revision_id: None` | M6 不要求 candidate 绑定的 M5；`upstream_real` 行 BLOCKED |
| C5 | 决定事件 `verdict ∈ {accept,amend,reject,request_evidence}`、`queue_item_id`/`seen_artifact_revision_id`/`standing` | `review_events.py:16,26-41,43`：verdict 5 值、事件顶层键固定、校验拒收多余键 | 复用 `review_events`；`standing` 移出事件内容 |
| C6 | `changes_current_judgment` 由 M6 决定字段 | `assemble` 的 `school_views[].changes_current_judgment` 已在候选；`review_events` 无此键 | 从候选读取，写入 `reviewed_edition.school_views[]` |
| C7 | 新 artifact_type 含 `correction_request`（INTERFACES §4 M6 行） | `service.py:822-829,940-945` `record_human_event` 只收 `human_event` | CorrectionRequest = `human_event`（D-10），不提名新类型 |
| C8 | 主内容名为 `reviewed_edition_package` | `INTERFACES.md:169-171` M6 主内容 `reviewed_edition` + 阶段输出 `reviewed_edition_package` | 采用双修订（主内容 + 索引） |
| C9 | 队列项 task_id `<entity_id>#<decision_type>` | `INTERFACES.md:167` `m6_review_<entity_id>_<decision_type>` | 队列项 id 用 `<entity_id>#<decision_type>`（任务标签，非登记册 ID）；Checkpoint `task_id` 用 `m6_review_<entity_id>_<decision_type>` |
| C10 | Snapshot 类型 `canonical_knowledge_snapshot` 在本包 | `INTERFACES.md:289-291` M7 主内容 `canonical_snapshot` + `assembly_package`；`G7-RULINGS` §9.12 第 61 条 | 归 M7；本包删 ACT 10，不提名 Snapshot 类型 |
| C11 | 回归取行 `\| tail -1` | 第 27 条 | 统一 `2>&1 \| grep -E "^(Ran\|OK\|FAILED)"` |
| C12 | 闭集前提写死 `pass=N` | 第 54 条 | 写 `check_interfaces.py` 末行 `fail=0` 且 exit 0，且所需类型 PASS 行存在 |

## 5. 接口契约

### 5.1 上游输入契约（只经 Ledger 读接口）

| 来源 | 定位方式 | artifact_type | M6 读取的字段 |
|---|---|---|---|
| M3 | m4 `candidate_package.corpus_stage_package_revision_id` / `spans_revision_id`；其 StepRun 须 `succeeded`（P5） | `corpus_package`（JSON）、`corpus_spans`（YAML） | Span：`span_id`、`page`、`line_index`、`start_offset`、`end_offset`、`text`、`source_anchor{page,image_sha256,line_id,bbox,chars}`；文档：`source_id`、`evidence_level`、`edition_part_artifact_id` |
| M4 | `list_checkpoints(ep,"m4")` 最新项所属 StepRun `succeeded`；其输出恰 1 个 `candidate_package`（P5） | `candidate_package`（JSON）+ `candidate_set`（JSON） | 包：`candidate_set_revision_id`、`candidate_set_sha256`、`corpus_stage_package_revision_id`、`spans_revision_id`、`technique_profile_revision_id`、`gate_profile`、`span_layer`、`cross_model`、`term_layering`；`candidate_set`：`technique_id`、`source_id`、`edition_part_artifact_id`、`assertions[{assertion_id, proposition_id, proposition, relation, evidence[{source_span_id, support_type, start_offset, end_offset, quote, quote_sha256}], conditions, exceptions, concept_refs, school_ids, layer, content_status, origin}]`、`school_views[{school_view_id, school_id, subject_entity_id, claim_refs, conflict_group_id, changes_current_judgment, source_refs, evidence, content_status, origin}]`、`rejected[]`、`disputes[]`、`counts{}` |
| M5 | `list_checkpoints(ep,"m5")` 最新项所属 StepRun `succeeded`；其输出恰 1 个 `validation_package`；m5 StagePackage `validation.passed == true`（第 21 条） | `validation_package`（JSON）+ `gate_results`（JSON） | 包：`gate_results_revision_id`、`corpus_package_revision_id`、`corpus_spans_revision_id`、`gate`、`scope`、`target_consumption_level`；`gate_results`：`gates{G1..G7}`、`passed_checks[]`、`failures[]`、`warnings[]`、`broken_relations[]`、`rework_tasks[]`、`not_evaluated[]`、`gate`、`counts{}` |

M6 拒绝条件：任一上游 StepRun 非 `succeeded`、修订非 `sealed`、M5 StagePackage `validation.passed` 非真、M4 `candidate_package` 与 M3 `corpus_package` 血缘不符、m6 链已有 succeeded 的首审运行（返工走 `rework.py`）。同阶段后续运行经 `supersede_step_run` 接替（第 58 条）。

### 5.2 本包内部对象

- **ReviewQueue 项**：`queue_item_id="<entity_id>#<decision_type>"`、`target_entity_id`、`kind`、`decision_type`、`seen_artifact_revision_id`（=`candidate_target_revision_id`，首审为首审运行立场所依据的候选修订，返工为 M4' 新 `candidate_set` 修订）。队列由 `review_events.required_decision_types` 逐对象推导（第 67 条）。
- **decision_entry（M6 运行内决定记录，供 Gate 与 `reviewed_edition`）**：`{decision_revision_id, queue_item_id, target_entity_id, kind, decision_type, verdict, standing, seen_artifact_revision_id, modified_revision_id, carried_from_revision_id, rationale}`。**事件锚点恒为 `seen_artifact_revision_id`**；`modify` 决定另携 `modified_revision_id`（=`reviewed_candidate` 修订），纳入本键集并由 Gate `decision_anchoring` 校验存在性（第 68 条）。
- **ReviewDecision（`human_event` 内容）**：逐字复用 `review_events.build_review_decision`（`schema_version`、`event_kind="review_decision"`、`stage="m6"`、`decision_type`、`verdict`、`target{entity_kind,entity_id,artifact_revision_id}`、`processing_run_id`、`step_run_id`、`actor_ref`、`rationale`、`evidence_refs`、`consumption_level`）；决定身份 = 该修订的 `artifact_revision_id`，无新前缀。同一队列项的后续决定为该队列项重新写入的新事件（历史保留）。`synthetic_fixture: true` 仅出现在 fixture 合成事件中（第 52/53 条），**不得**写进 `review_decision` 顶层键（会被 `validate_review_decision` 拒收）——合成标记写在外层测试数据/README，不进入事件内容。
- **CorrectionRequest（`human_event`，D-10）**：`{schema_version, event_kind:"correction_request", stage:"m6", step_run_id, source_span_ids[], description, target_stage:"m2", actor_ref}`。
- **ReworkThresholdAck（`human_event`）**：`{schema_version, event_kind:"rework_threshold_ack", stage:"m6", step_run_id, rework_impact_report_revision_id, warnings[], actor_ref}`。
- **ReworkImpactReport（`rework_impact_report`）**：`{schema_version, trigger_correction_request_revision_id, rework_round, changed_span_ids[], removed_span_ids[], reachable_entity_ids[], invalidated[{kind,entity_id,revision_id}], carried_forward[{kind,entity_id,revision_id,carried_from_revision_id}], needs_review[{decision_revision_id,target_entity_id,queue_item_id,reason}], invalidated_count, carried_forward_count, needs_review_count, valid_object_count, invalidated_ratio, warnings[], affected_queues[]}`（§14.1:641 必含字段全覆盖）。
- **StageCheckpoint（m6）**：首个 task `build_review_queue`；此后每条决定/人工事件一个 Checkpoint，`completed_tasks` 累积（`task_id = m6_review_<entity_id>_<decision_type>` → 最新决定修订），`human_decisions` 累积全部人工事件修订，`pending_queue` 为未决项，返工时带 `rework_impact_report_revision_id`。

### 5.3 下游输出契约（只写接口需求，不改其他包）

- **`reviewed_edition`（JSON，m6 主内容）**：`{schema_version, edition_part_artifact_id, candidate_set_revision_id, candidate_package_revision_id, validation_package_revision_id, approved[{entity_id, kind, artifact_revision_id, content_status:"expert_verified", decision_revision_ids}], rejected[{entity_id, kind, artifact_revision_id, content_status, decision_revision_ids}], decisions[{decision_revision_id, queue_item_id, target_entity_id, seen_artifact_revision_id, current_target_revision_id, modified_revision_id, decision_type, verdict, standing, carried_from_revision_id, trigger_correction_request_id}], evidence_links[{entity_id, source_span_id, corpus_spans_revision_id, start_offset, end_offset, quote_sha256}], school_views[{school_view_id, school_id, subject_entity_id, conflict_group_id, changes_current_judgment}], correction_request_revision_ids[], rework_impact_report_revision_id|null, unresolved_count:0}`。

  本节取代原 §5.2 草案；`reviewed_edition` 消费者为 M7（`CanonicalKnowledgeSnapshot` 由 M7 创世汇编薄切片产出，第 61 条）。
- **`reviewed_edition_package`（JSON，m6 阶段输出索引）**：`{schema_version, reviewed_edition_revision_id, decision_revision_ids[], decision_count, approved_count, rejected_count, unresolved_count:0, correction_request_revision_ids[], rework_impact_report_revision_id|null}`。
- **m6 StagePackage**：形状同 impl-02/m4 先例；`payload{reviewed_edition_revision_id, decision_revision_ids, unresolved_count:0}`；`manifest.counts{approved, rejected, decisions, correction_requests}`；`content_sha256 = sha256(reviewed_edition 字节)`；`lineage.upstream_artifacts=[corpus_package, candidate_package, validation_package]`。
- **M8（impl-04，已验收；只写接口需求）**：知识链前三段（KnowledgeEntry→Assertion→EvidenceLink）依赖 M4 `candidate_set`（`aggregate` 见 impl-05 README §6.6），M6 只供给 `content_status`（`expert_verified`）与 `school_variance_display`（§16.3.2:813-815，含 `changes_current_judgment`）；`GraphProjectionPack` 仍需 M8 编译前三段（本次 `knowledge_chain: not_compiled`，`packs.py:262`；`gate.py:392-404`）。
- **Orchestrator 登记 m6 Module 所需接口**（由 `contract_registry` 包写入 `registry.yaml`，本包不写）：`{module_id:"m6.review_curation", stage:"m6", kind:"production", binding:"legacy_self_driving", entry:"pipeline.review.step:run_m6", version:"0.1.0", consumes:[{artifact_type:"candidate_package", from_stage:"m4"},{artifact_type:"validation_package", from_stage:"m5"},{artifact_type:"corpus_package", from_stage:"m3"}], produces:[{artifact_type:"reviewed_edition_package"}], human_queue:true, supports_recovery:true, entry_kwargs:{}, owns_processing_run:false}`。Stage Gate carrier 判定按 `orchestrator/gate.py`（第 45 条）：m6 有效运行中恰 1 个承载 m6 StagePackage；返工/恢复运行经 supersedes 链续写、不承载包时保留在有效集。

### 5.4 与 INTERFACES §4 M6 行的差异（交登记 ACT 对账）

| 项 | 本包定稿 | INTERFACES §4/§2.6 现状 | 建议 |
|---|---|---|---|
| artifact_type | 提名 `review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report` | M6 行含 `correction_request`，主内容 `reviewed_edition` + 阶段输出 `reviewed_edition_package`（:169） | 删 `correction_request` 类型（D-10 用 `human_event`）；其余按本包提名写入（P2，第 47 条模式；impl-00 act/13） |
| 队列 task_id | `<entity_id>#<decision_type>`（队列项 id）/ `m6_review_<entity_id>_<decision_type>`（Checkpoint task_id） | `m6_review_<entity_id>_<decision_type>`（:167） | 一致，登记 ACT 不必改 |
| Snapshot | 不产（第 61 条归 M7） | `canonical_snapshot`（M7 主内容，:184） | 由 M7 创世汇编薄切片产出（impl-07 先行） |

## 6. 执行约束（主 Agent 决定，执行者不重议）

1. 纯函数优先：`model.py`、`propagation.py`、`gate.py`、`snapshot.project_snapshot` 不读文件、不访问 Ledger、不取时间、不用随机数。
2. Gate 独立：`gate.py` 不 import `model`/`propagation`/`step`/`rework`；`acceptance.py` 不信任 `close_review` 返回的 Gate 报告，自行重算。
3. 写入原子性：`begin_step_run` 之前的拒绝不留任何 Ledger 写入；`record_decision`/`close_review` 的前置拒绝不消费 token、不写修订；`begin` 之后的异常一律失败封存（检查名 `internal`，沿用 impl-02 教训）。
4. 每条人工决定：`put_artifact(human_event)` → `seal_revision` → `record_human_event` → `write_checkpoint`，四步不得合并多条决定；决定内容用 `review_events.build_review_decision`。
5. 禁止由操作者挑选失效对象：失效传播函数签名中不存在任何「对象清单」参数（§14.1:643）。
6. 同阶段后续运行一律 `supersede_step_run`（第 58 条）；恢复用 `recover_from_checkpoint`（第 15 条）。
7. 退出码纪律同 impl-02/impl-05：3 仅限宿主缺失；准备/运行异常为 FAIL 退出 1；验收脚本永远调用仓库内规范 `verify.sh`。

## 7. 目录规划（落地后）

```text
pipeline/review/
  __init__.py        M6_TOOL / M6_TOOL_VERSION
  errors.py          ReviewRefused
  model.py           队列、规范化内容哈希、决定折叠与 outcome（纯函数；事件经 review_events）
  gate.py            M6 Review Gate（纯函数、独立实现、九项检查）
  propagation.py     §14.1 精确失效传播（纯函数）
  inputs.py          resolve_m6_inputs（只读 Ledger）
  step.py            open_review / record_decision / recover_review / close_review / run_m6
  rework.py          request_correction / run_rework_propagation / open_rework_review
  console.py         CLI 子命令实现
  __main__.py        python -m pipeline.review
  acceptance.py      m6 验收判定
  testing/           非生产：__init__.py upstream_stub.py data/*.yaml
  tests/             test_model test_gate test_propagation test_inputs test_step_open test_step_close
                     test_console test_rework test_rework_review test_acceptance
openspec/acceptance/m6-data-fields.sh
```

## 8. 派发分组

- K1（纯函数，无 Ledger）：ACT 01–03。
- K2（Ledger 集成与 Console）：ACT 04–07，前置 impl-05 `ACCEPTED`。
- K3（返工链与验收）：ACT 08、09、11（ACT 10 已 WITHDRAWN，第 61 条）。

## 9. 用户待办

1. **真实专家签发决定表（P7 / D-03 / D-04）**：本包只冻结并复用 `review_events` 契约，不产生任何真实签发。任何需要真实 `expert_verified` 的条目，其决定表必须由用户本人撰写；在用户提供之前，依赖它的判定一律 **BLOCKED**，不得以测试替身或合成事件充数、不得写 `expert_verified`。
2. **fixture m6 金标（若需）**：若为 M6 增加 fixture 金标，须作为 impl-00 目录下的独占 ACT（P4），与本包实现分离；本包不写 fixture。

## 10. 待主 Agent 裁决

无遗留：D-01（第 61 条）、D-08（第 62 条）已由 `G7-RULINGS` §9.12 裁定（见 §4.1）；其余条目已由原则与已落地契约唯一推出，写入 §4「主 Agent 决定」。
