# impl-06：M6 Review & Curation 与 Review Console 最薄接入（§14、§14.1、§22.3）

状态：`DRAFT`（起草 Agent 产出；§4 待裁决条目未经主 Agent 定案前不得派发，不写 PROMPT 与 ACCEPTANCE）

## 1. 目标

在 `pipeline/review/` 落地规格 §14 的 M6 **M6 模式**最薄实现，以及 §14.1 精确失效传播的首切片：

1. 从 Artifact Ledger 冻结读取 CorpusPackage（M3）、CandidatePackage（M4）、ValidationPackage（M5），确定性生成审核队列（Candidate × 必审 ReviewDecision 类型）；
2. 经 §7.1 `await_human` → `record_human_event` → `resume` 接口，把每条人工决定写成不可变 `human_event` 修订，**每条决定被 Ledger 接受后即时写一个 StageCheckpoint**（§17.1）；
3. 以独立实现的 M6 Review Gate 判定零未解决项，产出 `ReviewedEditionPackage` 与 m6 StagePackage，并登记带全部人工决定的 Transformation（§20.3）；
4. 最薄 Review Console：命令行（推荐，见 D-02），只读对照原文/字框锚点/校验结果，并执行接受、修改、驳回、补证、流派归属与 CorrectionRequest；
5. 精确失效传播：上游 Span 修正后按对象级血缘机器判定失效/继承/待复核，封存 `ReworkImpactReport`，复审只重放待复核项；
6. （依 D-01）为 M8 提供 `CanonicalKnowledgeSnapshot` 首切片直通投影。

M4/M5 尚未实现，本包以**非生产测试桩**（`pipeline/review/testing/`）把最小 Candidate/Validation 注入真实 Ledger 推进（D-11）。

完成判据（本批唯一的「做完」定义，按 D-12 推荐方案书写，裁决后改写）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/review/tests -t . 2>&1 | tail -1   # OK（用例数 ≥ 110）
bash openspec/acceptance/m6-data-fields.sh; echo exit=$?
# 期望：12 行 PASS + BLOCKED legacy_workbench_seed + BLOCKED upstream_real
#       末行 SUMMARY pass=12 fail=0 blocked=2；exit=2
bash openspec/acceptance/run_all.sh | tail -1      # 仍为 SUMMARY pass=2 fail=1 blocked=8（本批不改 run_all.sh，D-17）
bash openspec/acceptance/m3-coverage.sh | tail -1  # 仍为 SUMMARY pass=8 fail=0 blocked=1（不回退）
```

返回 2 而非 0 的原因：上游是测试桩（M4/M5 未实现），旧工作台数据体（§19 M6 行实测 `original_text` 非空 0/496）未迁入；§19.0「M6 数据体字段缺失」差距仍标记为未关闭。

## 2. 依据（只读来源，文件:行号）

- 规格 `openspec/learn-system-blackbox-architecture.md`
  - §5 Review Console 不是第九 Module、人工决定归属原 StepRun：130；PendingQueue 第 4 队列「M6 待签发」：119-124；`ReworkImpact`：126
  - §6.1 EditionRun 链到 ReviewedEditionPackage：138-147；§6.2 Snapshot 由 ReleaseRun/M7 产出：153-175
  - §7 冻结输入：181-207；§7.1 一个 StepRun 覆盖整条人工队列、`resume_token`、`record_human_event`/`resume`：209-226
  - §8 包结构与不可变：232-243；§8.1 `entity_id`/`artifact_revision_id` 分离、ReviewDecision 双锚：257-267；UUIDv4/人工闭集前缀：288-322
  - §8.2 内容成熟度 7 态：335-347；ReviewDecision 8 类：349-364；Artifact status 与迁移：384-404；StepRun 迁移：406-430；四轴正交：432-440
  - §12.2 SchoolView 字段与 `review_school_attribution`：570；模型候选与人工决定留痕：572-574
  - §13 M5 不修改 Candidate、Gate 通过条件：580、606
  - §14 M6 输入、动作、Console 模式、SQLite 仅投影、CorrectionRequest、输出：614-631
  - §14.1 精确失效传播全文：633-645
  - §15 M7 产出 Snapshot Revision：651-653；§16 M8 冻结 Snapshot 输入：661-668；消费级别门槛：670-678；`canonical_hash`：725；SchoolViewPack：736；§16.3.2 M6 供给 `school_variance_display` 与「是否改变当前判断」：813-815
  - §17 本地进程、ActorProvider、事务序列：826、830、836；§17.1 人工阶段每次决定即时 Checkpoint、恢复语义：840-846
  - §18 LineageGraph 含审核决定、双向追溯：852-859
  - §19 M6 行（首纵切后、旧数据体实测）：880；Local Orchestrator 缺失失效传播：884；§19.0 `m6-data-fields.sh`：910
  - §20 第 2、3 条：938-939；§22.1 统一验收宿主：969；§22.2 纵切终点：973-984；§22.3 M6 薄用「只读对照与签发」：991；§22.4 失效传播先以 Ledger 事件记录：1000
- `pipeline/ledger/service.py`（impl-01 已验收，只读调用）：`_NAME_RE`/`RUN_ARTIFACT_TYPES` 59-66；可写状态 `running|awaiting_human` 253-262；`_configuration_stage` 295；`create_processing_run` kind 闭集 319-327；`supersede_step_run` 412-440；`put_artifact` 442；`seal_revision` 599；`invalidate_revision` 664-676；`supersede_revision` 678-716；`register_stage_package` 718-774；`record_transformation`（`human_event_revision_ids` 只收 `human_event`）777-843；`await_human` 885-920；`record_human_event`（decision_type 限 8 类）922-963；`resume` 965-989；`suspend` 991；`fail_step_run` 1187；`_write_checkpoint_locked`（阶段被 succeeded 运行封存后只允许 supersedes 链续写）1242-1290；`_backfill_checkpoint_if_needed` 1400；`recover_from_checkpoint`（不迁移旧运行状态）1430-1482
- `pipeline/ledger/store.py`：`human_events` 160-166；`stage_checkpoints.rework_impact_report_revision_id` 168-179
- `pipeline/ledger/states.py`：`CONTENT_MATURITY` 46；`REVIEW_DECISION_TYPES` 57
- `pipeline/ledger/acceptance.py`：20.3 `transformations_count == 3` 硬编码 311-315
- `pipeline/ledger/fixture_ingest.py`：人工事件 + 每 task Checkpoint 写法 217-252
- `pipeline/corpus_compiler/step.py`：`run_m3` 事务模板 35-66、失败封存 `_fail` 404；impl-02 `act/03.yaml` 第 13 步 StagePackage 形状
- `pipeline/corpus/_fixture/mini_ed01/`：`spans.yaml`（43 条 Span，页 001/003）、`expected/m3.stage_package.yaml`；M4–M8 期望产物不存在
- `openspec/id-prefix-registry.md` §3.1-§3.4（`as_`、`sv_`、`cg_`、`sch_`、`ss_`、`rev_`、`art_` 已登记）
- `docs/blackbox-spec-rework/SUBAGENT_TODO.md`:599-600（现登记 impl-03=M5、impl-04=M8，编号见 D-18）

## 3. 范围

写（全部新建）：`pipeline/review/**`（含 `testing/` 非生产子包与 `tests/`）、`openspec/acceptance/m6-data-fields.sh`（ACT 11，名称依 D-12）。

禁止：改规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`openspec/acceptance/run_all.sh`、`m3-coverage.sh`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`；新增依赖（仅标准库 + PyYAML + jsonschema）；新增 ID 前缀（队列项号 `<entity_id>#<decision_type>` 是任务标签，不是登记册 ID）；调用任何模型 API；生产代码读 fixture 路径、工作目录「最新文件」或 `testing/`（只读 Ledger 冻结修订；Console 仅在 `--amended-content-file`/`--from-file` 读操作者提供的人工输入）；改写 `pattern_knowledge_workbench/`（Flutter 工作台本批不动）。

前置：impl-02 `ACCEPTED`（ACT 04 起依赖真实 `run_m3`）；D-01～D-18 裁决完成。

## 4. 待主 Agent 裁决

每条给 2–3 个选项，「推荐」仅为起草者意见，不代表定案。

**D-01 CanonicalKnowledgeSnapshot 由谁产出。** 任务要求本包产出 M8 输入 Snapshot，但规格把 Snapshot 归 ReleaseRun/M7（§6.2:153-169，§15:651），首纵切链路又跳过 M7（§22.2:973-979，§22.3:991）。
- A：本包 ACT 10 实现「M7 首切片直通投影」：独立 `release_run` + `stage=m7` StepRun，单 Edition、无既有 Snapshot、只投影已获批对象，不做合并/对勘；宿主暂放 `pipeline/review/snapshot.py`，M7 落地时迁出。
- B：M6 StepRun 直接附带产出 Snapshot（stage m6），违反 §6.2 归属。
- C：首切片 M8 直接读 ReviewedEditionPackage，不产 Snapshot，与 §16:662 冻结项不符。
- 推荐 A：保留 §6.2 的运行与阶段归属，M8 输入契约从第一天就是 Snapshot；若主 Agent 把它派给 M7 草案，删除 ACT 10，验收第 12 项改 BLOCKED（前置缺失: M7 Incremental Assembly）。

**D-02 Review Console 首切片形态。** §14:620 设想 Flutter 工作台演进，§17:826 要求其经本地客户端调 Ledger，§22.3:991 只要求「只读对照与签发」。
- A：命令行 `python -m pipeline.review`（open/queue/show/decide/decide-batch/correct/close/recover/rework），原文与字框以文本形式显示，不渲染页图。
- B：改造 `pattern_knowledge_workbench`（Flutter + Ledger 客户端）。
- C：复用 OCR FastAPI + Vue 工具加 M6 页。
- 推荐 A：零新依赖、可测试、与 §22.3「薄用」一致；B 依赖 Ledger 网络客户端与 Dart 侧契约，放到首纵切后。

**D-03 ReviewDecision 结构。** §8.2:351-364 只定义 8 个审核**维度**，§14:618 列出的「接受、修改、驳回、补证、流派分歧」动作没有闭集。
- A：决定 = `decision_type`（8 类维度之一）+ `verdict` ∈ {`accept`,`amend`,`reject`,`request_evidence`}；`amend` 由 M6 封存 `reviewed_candidate` 新修订（`entity_id` 不变）；流派分歧通过 `review_school_attribution` 决定上的 `changes_current_judgment` 布尔字段表达（§16.3.2:815）；「专家签发」= 该对象全部必审维度的立场都是 accept/amend。
- B：动作并入内容成熟度（accept→`expert_verified`、reject→`deprecated`），混淆 §8.2:432-440 四轴正交。
- C：每种动作一个 human_event 子类，不设 verdict 字段。
- 推荐 A；`verdict` 闭集需主 Agent 确认是否回写规格 §8.2。

**D-04 必审维度集合与获批推导。** 规格未定义哪些 Candidate 类别必须经过哪些 ReviewDecision 类型才算获批（§8.2:351，§16.1:678 仅对 PUBLIC_RELEASE 要求 `expert_verified`）。
- A：配置修订 `required_decision_types` 按类别映射，首切片默认 `assertion→[review_source_fidelity]`、`school_view→[review_school_attribution]`；全部必审维度通过 → 内容成熟度 `expert_verified`；任一 reject → `rejected` 列表且成熟度保持原值（不写 `deprecated`，它表示撤回已获批内容）。
- B：每个对象 8 维全审。
- C：由 TechniqueProfile 登记（Contract Registry 未实现，§19:885）。
- 推荐 A：10 页内部验收包消费级别为 INTERNAL_DEMO（§22.1:968），映射写进配置修订可审计，将来移入 TechniqueProfile。

**D-05 失效粒度与 Artifact status 落点。** §14.1:638 要求把可达的 Candidate、ValidationReport 条目、ReviewDecision 目标对象置为 `invalidated`（§8.2 状态），但 Artifact status 作用于整条修订（§8.2:384-404），而 §14.1:643 禁止整队列批量失效。
- A：M4 每个 Candidate 独立落 `knowledge_candidate` 修订，失效时逐个 `invalidate_revision`；ValidationReport 条目只在 `ReworkImpactReport.invalidated` 逻辑登记（M5 重跑产出新包）；ReviewDecision 修订保持 `sealed`，其继承立场见 D-06。
- B：候选与校验都只存包级大文件，失效仅记逻辑清单，旧包整体 `superseded`。
- C：A 基础上要求 M5 也逐条目落 `validation_entry` 修订。
- 推荐 A：只有逐对象修订才能让 §8.2 状态真正精确；C 对 M5 成本过高且 M5 必然重跑。此项构成对 M4 草案的硬接口要求。

**D-06 `carried_forward` / `needs_review` 不属于任何 §8.2 闭集。** §14.1:639-640 称其为「状态标记」，但既不在 Artifact status 5 态，也不在内容成熟度 7 态。
- A：作为 ReviewDecision 在 M6 内容中的「继承立场」字段 `standing` ∈ {`active`,`carried_forward`,`needs_review`}，不进 Ledger 状态表。
- B：`needs_review` 映射到内容成熟度 `needs_expert`。
- C：主 Agent 增补 §8.2 第五轴后再实现。
- 推荐 A，并请主 Agent 决定是否把第五轴写回规格（C 的文档部分）。

**D-07 规范化内容哈希与「被修正 Span」判定键。** §14.1:640 未定义规范化规则与目标对象内容边界；§14.1:637 以 Span 为影响面，但 `corpus_spans` 是整份修订，前一行改长会让后续 Span 的 offset 平移。
- A：Span 变更键 = `text` + `source_anchor`（页、图像哈希、行号、行框、逐字框），**排除** `start_offset/end_offset/batch_id`；对象内容哈希 = 对象字段（剔除修订号、成熟度、模型运行引用）+ 按证据链接**解引用的引文文字**，`json.dumps(sort_keys=True, ensure_ascii=False, separators=(",",":"))` 后 SHA-256；字框几何变化使对象「可达」但内容可能「等价」。
- B：对象内容哈希只含对象字段，不解引用引文（OCR 改字永远判等价，违背 §14.1 意图）。
- C：按 `decision_type` 选择字段集。
- 推荐 A：宁可多降级为待复核，不漏判；排除 offset 防止无关 Span 被连带失效。

**D-08 血缘可达的数据来源与传播宿主。** §14.1:635 要求 LineageGraph（§18）机器判定，但 LineageGraph 与 Local Orchestrator 均未实现（§19:883-884，§22.4:1000）。
- A：对象级引用图（`evidence_links.source_span_id`、`source_refs`、`subject_entity_id`、`claim_refs` 传递闭包）判定可达；纯函数放 `pipeline/review/propagation.py`，由 M6 返工 StepRun 调用并经 Ledger `invalidate_revision` 落状态，将来迁入 Orchestrator。
- B：只用 Ledger Transformation 的修订级输入输出（粒度为整份包，等于批量失效，违反 §14.1:643）。
- C：先实现 L1' LineageGraph 再做本项。
- 推荐 A；需主 Agent 确认 M6 StepRun 调用 `invalidate_revision` 改写 M4 修订状态不违反 §2:32「Module 不直接修改其他 Module 数据」（经 Ledger 接口）。

**D-09 ReworkImpactReport 计数口径与阈值确认。** §14.1:641-642 未说明 N/M/K 以对象还是决定计、30% 的分母是什么；`BlockingReasons` 所在 Orchestrator 不存在。
- A：`invalidated_count` = 可达 Candidate 数 + 可达校验条目数；`carried_forward_count` = 不可达 Candidate 数 + 继承的决定数；`needs_review_count` = 降级决定数；分母 `valid_object_count` = 修正前有效 Candidate 数 + 校验条目数；报告另附逐类明细。告警写入报告 `warnings`；复审 `open_rework_review` 在有告警时须显式 `acknowledge_rework_warning=True`，确认本身写成 `human_event`（`event_kind=rework_threshold_ack`）。
- B：三个计数都只按决定计。
- C：三个计数都只按对象计，决定另列。
- 推荐 A：与 §14.1:641 并列「失效 N / 继承 M / 待复核 K」的字面最接近，逐类明细消除歧义。

**D-10 CorrectionRequest 形态与闭环。** §14:629 要求 M6 发现 OCR 错误时创建 CorrectionRequest 退回 M2，但 M2 修正流程与该对象形态未定义，M2 首纵切外（§22.4:998）。
- A：`artifact_type=human_event`、内容 `event_kind=correction_request`（经 `record_human_event`，`decision_type=None`），列出 `source_span_ids`；**不阻断**后续决定与结审，结审包登记 `correction_request_revision_ids`；上游修正到达后，返工链（ACT 08-09）按 §14.1 机器判定哪些决定待复核。
- A'：同 A，但证据触及这些 Span 的未决项禁止决定、`close_review` 拒绝。缺点：未决项永远无法结审，而返工链要求首审已 succeeded，形成死锁。
- B：独立 `artifact_type=correction_request`（`record_human_event` 只收 `human_event`，service.py:940-945，需改 Ledger）。
- C：CorrectionRequest 直接让 M6 StepRun `failed`。
- 推荐 A：不改 Ledger、无死锁，§20.3 人工决定记录自然覆盖该事件；「在错字上作出的决定」由 §14.1 内容哈希比较降级待复核，不靠人工挑选。

**D-11 M4/M5 缺席时的输入注入。** 统一验收宿主只有 m1-m3 期望产物（§22.1:969）。
- A：本包 `pipeline/review/testing/`（非生产子包，生产模块禁止 import）内置合成 Candidate/Validation/决定/修正数据，经真实 Ledger 写路径注入；验收以 `upstream_real` 行 BLOCKED 如实标注。
- B：主 Agent 在 `mini_ed01` 增补 `expected/m4|m5|m6.stage_package.yaml` 与候选、校验、决定期望产物（需改 fixture 与 `verify.sh`）。
- C：等 M4/M5 实现后再做 M6。
- 推荐 A 立即推进、B 在 M4/M5 契约定稿后补；注意 fixture 前 3 页为书名页与目录，合成候选只验证结构与血缘，不含术理内容。

**D-12 验收脚本名与 §19.0 对应。** §19.0:910 的 `m6-data-fields.sh` 登记的是旧工作台数据体差距（§19:880），与新 M6 流水线语义不完全一致。
- A：实现 `m6-data-fields.sh`，12 项新 M6 数据体检查（决定双锚、审核留痕、状态、失效传播）+ `legacy_workbench_seed` BLOCKED（旧库准入仍由 run_all 20.7 FAIL 承担，本脚本不重复判 FAIL）+ `upstream_real` BLOCKED，本批 exit 2。
- B：新建未登记的 `m6-review.sh`，由主 Agent 登记进 §19.0。
- C：不出脚本，只靠单元测试。
- 推荐 A：沿用 impl-02「脚本=§19.0 判据、本批返回 2」的先例。

**D-13 新增 artifact_type 清单与上游类型名。** Ledger 不设 artifact_type 闭集（service.py:59-61），但 20.3 判据按类型识别（acceptance.py:365-400）。
- 本包新增（推荐）：`review_queue`、`reviewed_candidate`、`reviewed_edition_package`、`rework_impact_report`、`canonical_knowledge_snapshot`（依 D-01）；沿用 `human_event`、`configuration`、`validation_report`、`step_log`、`failure_report`、`stage_package`。
- 本包假设的上游类型（需与 M4/M5 草案对账）：`candidate_package`、`knowledge_candidate`、`validation_package`；M3 沿用 `corpus_package`、`corpus_spans`（impl-02）。
- 选项：A 按上表；B 上游名由 M4/M5 草案先定、本包跟随；C Contract Registry 统一登记后再实现。推荐 A 并以 B 对账。

**D-14 返工 StepRun 链与上游修订取代时机。** Checkpoint 写入要求：阶段被 succeeded 运行封存后只允许 supersedes 链上的新运行续写（service.py:1280-1285），链是单线；`begin_step_run` 要求冻结输入全部 `sealed`（service.py:405、§8.2:388-392）。
- A：单线链 `首审 review（succeeded）← 失效传播 rework_propagation（succeeded，无 StagePackage）← 复审 review（succeeded，产出新 m6 包）`；上游旧 corpus/候选修订必须在失效传播 StepRun 冻结之后才可 `superseded`，否则无法冻结。
- B：失效传播与复审合并为一个 StepRun，M4'/M5' 输出到达后追加输入（违反 §7:207 冻结输入）。
- C：失效传播挂在 Orchestrator 伪 StepRun 上（Orchestrator 未实现）。
- 推荐 A；同时请确认「rework_propagation 以 succeeded 结束但不产 StagePackage」不被 `stage_progress` 误读为 M6 Gate 通过（§7.1:211 允许一阶段多任务）。

**D-15 Ledger `recover_from_checkpoint` 不迁移旧运行。** service.py:1459-1482 只建新 StepRun 并写 recovery 事件，旧运行若为 `awaiting_human` 会一直停留在非终态，`run_status` 聚合取末个非终态（service.py 只读聚合段）。
- A：本包照用，旧运行保持 `awaiting_human`，测试断言现状。
- B：impl-01 小返工：`recover_from_checkpoint` 对非终态旧运行同步置 `superseded`（§8.2:430 语义）。
- C：本包改用 `supersede_step_run` 并自行补写 Checkpoint（重复 Ledger 的补写逻辑）。
- 推荐 B；ACT 05 按 B 书写，若裁 A 则改测试断言。

**D-16 `resume_token` 在 CLI 跨进程保管。** token 只在 `await_human` 返回一次、库里只存哈希（service.py:885-920），§7.1:220 明确它不是鉴权凭据。
- A：`open`/`recover` 打印 token，后续 `decide`/`correct`/`close` 显式 `--resume-token` 传入；丢失时走 `recover`。
- B：token 写 Ledger 根目录旁的本地会话文件（Ledger 之外的状态，违背「只经 Ledger」）。
- C：只提供单进程 `decide-batch --from-file`。
- 推荐 A + C 并存（批量文件仍逐条落事件、逐条 Checkpoint）。

**D-17 run_all.sh 与 20.3 是否纳入 M6。** 20.3 判据在 m1-m3 灌入 Ledger 上运行且 `transformations_count == 3` 硬编码（acceptance.py:311-315）；§20 没有任何一条会因 M6 单独落地由 BLOCKED 变 PASS（20.1 缺 Orchestrator，20.4 缺 M8）。
- A：本批不改 `run_all.sh` 与 `pipeline/ledger/acceptance.py`，在 m6 验收中对 M6 Transformation 复刻 20.3 八项。
- B：本批扩展 20_3 纳入 M6（改 Ledger 验收与 run_all）。
- C：等 Orchestrator 统一驱动全链后再扩展。
- 推荐 A，并登记「20_3 计数硬编码需在全链落地时泛化」为后续项。

**D-18 与并行草案的契约对账顺序。** 本包依赖 impl-05-knowledge（M4）、impl-03-validation（M5）的输出类型名与字段，并与 impl-07-assembly（M7）、impl-04-dataset（M8）争用 Snapshot 归属（D-01）；impl-00-interfaces 可能统一登记类型名。
- A：以 impl-00-interfaces 为唯一类型与字段来源，本包 §5 在裁决后逐字改写。B：本包 §5.1 作为 M4/M5 的需求方约束，由上游草案跟随。C：主 Agent 逐对并行草案人工对账。
- 推荐 A；D-05（逐对象 `knowledge_candidate` 修订）与 D-07（证据 offset 相对 Span 文字）是本包对 M4 的硬约束，对账时不得丢失。

## 5. 接口契约（供与 M3/M4/M5/M7/M8 草案对账）

### 5.1 上游输入契约（本包假设）

| 来源 | 定位方式（只经 Ledger 读接口） | artifact_type | 本包读取的字段 |
|---|---|---|---|
| M3 | `list_checkpoints(ep,"m3")` 最新项所属 StepRun 必须 `succeeded`；其 Transformation 输出恰 1 个 `corpus_package` | `corpus_package`（JSON，含 `spans_revision_id`）、`corpus_spans`（YAML，impl-02 act/01 R7/R8 键序） | Span：`span_id`、`page`、`text`、`source_anchor{page,image_sha256,line_id,bbox,chars}`；文档：`source_id`、`evidence_level` |
| M4 | 同上，stage `m4`，输出恰 1 个 `candidate_package` | `candidate_package`（JSON）+ 每对象一个 `knowledge_candidate`（JSON，D-05） | 包：`schema_version`、`edition_part_id`、`technique_id`、`corpus_package_revision_id`、`candidates[{entity_id,kind,candidate_revision_id}]`；对象：`entity_id`、`kind`（首切片 `assertion`/`school_view`）、`content_status`、`content`、`evidence_links[{source_span_id,start_offset,end_offset,quote_sha256}]`（offset 相对 Span `text`）、`source_refs`、`subject_entity_id`、`claim_refs`、`school_ids`、`conflict_group_id`、`model_run_refs` |
| M5 | 同上，stage `m5`，输出恰 1 个 `validation_package` | `validation_package`（JSON） | `candidate_package_revision_id`（必须等于 M6 冻结的候选包）、`validator_version`、`gate{passed,severe_error_count,failed_task_count,pending_rework_count}`（§13:606）、`entries[{entity_id,candidate_revision_id,check,result∈pass/warn/fail,code,message}]`、`broken_relations`、`rework_tasks` |

每个上游 StepRun 均按 §17.1 每 task 写 Checkpoint；M6 拒绝条件：任一上游 StepRun 非 `succeeded`、修订非 `sealed`、M5 `gate.passed` 非真或三项计数非零、M5 绑定的候选包与冻结的候选包不一致。

### 5.2 本包内部对象

- **ReviewQueue 项**：`queue_item_id="<entity_id>#<decision_type>"`、`target_entity_id`、`kind`、`decision_type`、`seen_artifact_revision_id`（冻结的候选修订）。
- **ReviewDecision（`human_event` 修订内容）**：`schema_version`、`event_kind="review_decision"`、`stage="m6"`、`step_run_id`、`queue_item_id`、`target_entity_id`、`seen_artifact_revision_id`、`decision_type`、`verdict`、`amended_revision_id`、`rationale`、`evidence_refs`、`changes_current_judgment`、`standing`、`carried_from_revision_id`、`trigger_correction_request_id`、`actor_ref`；决定身份 = 该修订的 `artifact_revision_id`，无新前缀。
- **CorrectionRequest（`human_event`，D-10）**：`event_kind="correction_request"`、`source_span_ids`、`description`、`target_stage="m2"`。
- **ReworkImpactReport（`rework_impact_report`）**：`schema_version`、`trigger_correction_request_id`、`rework_round`、`changed_span_ids`、`reachable_entity_ids`、`invalidated[]`、`carried_forward[]`、`needs_review[]`、`invalidated_count`、`carried_forward_count`、`needs_review_count`、`valid_object_count`、`invalidated_ratio`、`warnings`、`affected_queues`（§14.1:641 必含字段全覆盖）。
- **StageCheckpoint（m6）**：首个 task `build_review_queue`；此后每条决定一个 Checkpoint，`completed_tasks` 累积（队列项号 → 最新决定修订），`human_decisions` 累积全部决定与人工事件修订，`pending_queue` 为未决项，返工时带 `rework_impact_report_revision_id`。

### 5.3 下游输出契约

- **`reviewed_edition_package`（JSON，m6 StagePackage 的唯一业务输出）**：`schema_version`、`edition_part_id`、`technique_id`、`review_step_run_id`、`inputs{corpus_package_revision_id,corpus_spans_revision_id,candidate_package_revision_id,validation_package_revision_id}`、`approved[{entity_id,kind,reviewed_revision_id,content_status:"expert_verified",decision_revision_ids}]`、`rejected[{entity_id,kind,seen_revision_id,content_status,decision_revision_ids}]`、`decisions[{decision_revision_id,queue_item_id,target_entity_id,seen_artifact_revision_id,current_target_revision_id,decision_type,verdict,standing,carried_from_revision_id,trigger_correction_request_id}]`、`evidence_links[{entity_id,source_span_id,corpus_spans_revision_id,start_offset,end_offset,quote_sha256}]`（仅获批对象）、`school_views[{school_view_id,school_id,subject_entity_id,conflict_group_id,changes_current_judgment}]`、`unresolved_count:0`、`correction_request_revision_ids`（本运行冻结与自有的 CorrectionRequest，D-10）、`rework_impact_report_revision_id`。
- **m6 StagePackage**：形状同 impl-02 act/03 第 13 步；`payload{reviewed_edition_package_revision_id,approved_count,rejected_count,decision_count,unresolved_count}`；`manifest.counts{candidates,approved,rejected,decisions}`；`content_sha256`= 包字节哈希；`lineage.upstream_artifacts`=[corpus_package, candidate_package, validation_package]。
- **`canonical_knowledge_snapshot`（依 D-01，stage m7，`release_run`）**：`schema_version`、`technique_id`、`snapshot_kind:"first_slice_passthrough"`、`based_on{reviewed_edition_package_revision_ids,previous_snapshot_revision_id:null}`、`entities[{entity_id,kind,artifact_revision_id,content_status}]`、`school_views`、`conflict_groups{cg_id:[sv_id]}`、`evidence_links`、`canonical_hash`（§16:725）。M8 草案应只读此对象，不回读 M6 内部修订。

### 5.4 与并行草案 impl-00-interfaces 的差异（起草末期只读对照 `impl-00-interfaces/INTERFACES.md`，双方均为草案，交 D-18 裁决）

| 项 | 本包草案 | impl-00 草案（INTERFACES.md 行号） | 起草者建议 |
|---|---|---|---|
| M4 候选存放 | 每对象 `knowledge_candidate` 修订 + `candidate_package` 索引（D-05） | 主内容 `candidate_set` 单修订 + `candidate_package`（131、328） | **保留本包要求**：单修订无法逐对象 `invalidated`（§14.1:638 与 :643 冲突）；可折中为 `candidate_set` 之外另落逐对象修订 |
| M5 入参键 | `gate{passed,severe_error_count,failed_task_count,pending_rework_count}`、`entries[{entity_id,…}]` | 主内容 `gate_results`：`gate_passed`、`summary{critical_errors,failed_checks,…}`、`gates[].checks[].subject_ids`、`rework_tasks[]`（147、260-265） | 采用 impl-00 键名；M6 以 `gate_passed`、`summary.critical_errors`、`rework_tasks` 判入口，以 `checks[].subject_ids` 反查实体条目 |
| verdict 闭集 | `accept/amend/reject/request_evidence` + `changes_current_judgment` 字段 | `accept/modify/reject/request_evidence/school_dispute`，`modified_revision_id`、`content_status_after`、`scope_consumption_level`（269） | 名称跟随 impl-00（`modify`/`modified_revision_id`）；`school_dispute` 与「是否改变当前判断」布尔的关系需 D-03 定案 |
| 决定锚点 | 显式 `target_entity_id` + `seen_artifact_revision_id` | `target: entityRevisionAnchor`（269） | 语义等价，跟随 impl-00 结构，验收仍分别检查两部分（§8.1:265） |
| M6 主内容 | `reviewed_edition_package` 即主内容 | 主内容 `reviewed_edition` + 阶段输出 `reviewed_edition_package`（163、273、330） | 跟随 impl-00，与 M3 `corpus_spans`/`corpus_package` 模式一致；ACT 06 改为先封存 `reviewed_edition` |
| CorrectionRequest | `human_event`（`event_kind=correction_request`，D-10） | 独立 `correction_request`（163、330） | **保留本包**：`record_human_event` 只收 `human_event`（service.py:940-945），独立类型需改 Ledger 或脱离人工事件记录 |
| ReworkImpactReport 键 | `trigger_correction_request_id`、`warnings[]`、逐类明细 | `trigger_correction_request_revision_id`、`threshold_exceeded: bool`、`edition_part_artifact_id`（277） | 键名跟随 impl-00，另保留 `warnings`、`valid_object_count`、`invalidated_ratio`（D-09 口径需要） |
| 队列项 task_id | `<entity_id>#<decision_type>` | `m6_review_<entity_id>_<decision_type>`（161） | 跟随 impl-00 |
| payload / counts / operation | `approved_count…`；operation `review_curate` | `stage_payload_m6{reviewed_edition_revision_id,decision_revision_ids,unresolved_count}`；counts 含 `correction_requests`；operation `review_candidates`（164-165） | 跟随 impl-00 |
| Snapshot | `canonical_knowledge_snapshot`，本包 ACT 10 直通 | M7 主内容 `canonical_snapshot` + `assembly_package`，impl-00 D-03 推荐 M7 薄直通（176-179、281） | 见 D-01 更新：倾向交 M7 包 |

名称类差异裁决后由主 Agent 在 ACT contract 中机械替换，不改变 ACT 划分与测试矩阵；结构类差异（第 1、6 行）影响 ACT 03/04/08，须先定案。

## 6. 起草者建议的执行约束（裁决后改为「主 Agent 决定」）

1. 纯函数优先：`model.py`、`propagation.py`、`gate.py`、`snapshot.project_snapshot` 不读文件、不访问 Ledger、不取时间、不用随机数。
2. Gate 独立：`gate.py` 不 import `model`、`propagation`、`step`；`acceptance.py` 不信任 `close_review` 返回的 Gate 报告，自行重算。
3. 写入原子性：`begin_step_run` 之前的拒绝不留任何 Ledger 写入；`record_decision`/`close_review` 的前置拒绝不消费 token、不写修订；`begin` 之后的异常一律失败封存（检查名 `internal`，沿用 impl-02 act/05 教训）。
4. 每条人工决定：`put_artifact(human_event)` → `seal_revision` → `record_human_event` → `write_checkpoint`，四步不得合并多条决定；Checkpoint 写失败时恢复靠 `_backfill_checkpoint_if_needed` 补写，测试覆盖。
5. 禁止由操作者挑选失效对象：失效传播函数签名中不存在任何「对象清单」参数。
6. 退出码纪律同 impl-02：3 仅限宿主缺失；准备/运行异常为 FAIL 退出 1；验收脚本永远调用仓库内规范 `verify.sh`。

## 7. 目录规划（落地后）

```text
pipeline/review/
  __init__.py        M6_TOOL / M6_TOOL_VERSION
  errors.py          ReviewRefused
  model.py           队列、决定事件、规范化内容哈希、决定折叠（纯函数）
  gate.py            M6 Review Gate（纯函数，独立实现）
  propagation.py     §14.1 精确失效传播（纯函数）
  inputs.py          resolve_m6_inputs（只读 Ledger）
  step.py            open_review / record_decision / recover_review / close_review
  rework.py          request_correction / run_rework_propagation / open_rework_review
  snapshot.py        project_snapshot / run_snapshot（依 D-01）
  console.py         CLI 子命令实现
  __main__.py        python -m pipeline.review
  acceptance.py      m6 验收判定
  testing/           非生产：__init__.py upstream_stub.py data/{m4_candidates,m5_validation,m6_decisions,corrections,expected_review}.yaml
  tests/             test_model test_gate test_propagation test_inputs test_step_open test_step_close
                     test_console test_rework test_rework_review test_snapshot test_acceptance
openspec/acceptance/m6-data-fields.sh
```

## 8. 派发分组（建议）

- K1（纯函数，无 Ledger）：ACT 01–03
- K2（Ledger 集成与 Console）：ACT 04–07，前置 impl-02 `ACCEPTED`
- K3（返工链、Snapshot、验收）：ACT 08–11，ACT 10 依 D-01
