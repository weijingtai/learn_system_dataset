# IMPL-06 四查审查 R1（独立审查者 W4-R5）

- 审查对象：`work-items/impl-06-review/`（M6 Review & Curation 最薄接入），定稿 `981156c` + 裁定落实 `1eca795`，以 HEAD（`91e5348`）文本为准；与 impl-00 `act/13.yaml`（`950349b`）的接口登记联动见 IMPL-00-W5H-REVIEW-R1。
- 依据：G7-RULINGS §1 P1–P9、§4 impl-06、§9.3 第 34–43 条、§9.5 第 45–46 条、§9.6–§9.11 第 47–58 条、§9.12 第 61–62 条；规格 §5–§8.2、§14、§14.1、§16.3.2、§17、§17.1、§19/§19.0、§20、§22；已落地代码 `pipeline/knowledge_extraction/`、`pipeline/validation/`、`pipeline/orchestrator/`、`pipeline/contract_registry/`、`pipeline/dataset_compiler/`、`pipeline/ledger/`（只读逐字核对）；fixture `mini_ed01/`。

## 一、忠实性

- P1/第 43 条：M6 最薄接入、首纵切外；`legacy_workbench_seed`/`upstream_real`/`snapshot_projection` 恒 BLOCKED 不伪造 PASS；本批不改 `run_all.sh`（README §1 完成判据基线逐字相同）。
- P2/P3/第 54 条：新类型只提名（D-13 四类型），登记归 act/13；前提与门禁全部为「末行 `fail=0` 且 exit 0，且所需类型 PASS 行存在」，包内无写死 pass 总数（grep 证实，仅 m6-data-fields 自身 SUMMARY pass=11 属脚本输出格式）。
- P5/第 21 条：只认 succeeded 上游；M5 另须 StagePackage `validation.passed == true`（act/04 m5 规则、Gate `validation_intake`）。
- P6：零模型调用（act/01 verify grep）。
- P7/第 52/53 条：无真实签发；合成决定标注 `synthetic_fixture` 于非生产测试数据外层，不进 `review_decision` 顶层键（`review_events.py:85-90` 拒收多余键，§5.2 已明示此偏离及原因）；`upstream_real` BLOCKED 说明「不得计为真实 expert_verified」。
- 第 45 条：carrier 判定引用 `orchestrator/gate.py` `effective_step_runs`（:130，实测在）；D-14 不产 StagePackage 的 succeeded 运行不判 Gate 通过。
- 第 50 条：M6 Gate 结果作为自身 StepRun `validation_report` 落盘（act/06 步骤 3）。
- 第 58 条：同阶段后续运行经 `supersede_step_run`（README §5.1 拒绝条件、act/08 步骤 2、act/09 步骤 3；`inputs.py:58` `latest_succeeded_step_run` docstring 即引第 32/58 条）。
- 第 61 条：ACT 10 WITHDRAWN（README §4.1、ACT.yaml、TDD/BDD/ACCEPTANCE 全链一致），`snapshot_projection` 恒 BLOCKED。
- 第 62 条：`propagation.py`/`rework.py` 禁 `invalidate_revision`（verify grep + `test_module_does_not_reference_invalidate_revision` + `no_cross_module_status_change` 验收项），旧 candidate_set 由 M4' `supersede_revision` 替换。
- 忠实性发现：F1、F2、F3（契约内部矛盾，见下）。

## 二、覆盖性

- BDD 1–11 场景均有具名用例或 verify 落点（1.x→act/01，2.x→act/02，3.x→act/03，4.x→act/04，5.x→act/05，6.x→act/06，7.x→act/07，8.x→act/08，9.x→act/09，11.x→act/11）；ACT 10 撤回有 BDD §10 对应说明。
- m6-data-fields 14 项 = 11 PASS（inputs_frozen/queue_from_upstream/decisions_as_human_events/checkpoint_per_decision/decision_anchor_fields/reviewed_edition_contract/transformation_record/recovery_replays_pending_only/precise_invalidation/no_cross_module_status_change/rework_rereview_scope）+ 3 BLOCKED（snapshot_projection/legacy_workbench_seed/upstream_real）；`SUMMARY pass=11 fail=0 blocked=3`、exit 2 可达；BLOCKED 行名「M6 Review Workbench」「M4 Knowledge Extraction」逐字属 §19 第一列，「M7 创世汇编」为第 61 条授权措辞。
- 依赖无环：01→02→03；04 依赖 03+impl-05/impl-03 ACCEPTED；05→06→07；08→09→11；ACT 10 WITHDRAWN 不计入。时长 60/60/75/75/90/90/60/90/75/90 全部 ≤110。
- 覆盖性发现：F4（阈值与具名用例累计不符）。

## 三、可执行性（代码逐字核对，均实测通过）

- `review_events.py:16` VERDICTS 五值、`:18-23` ENTITY_KINDS、`:24` REVIEW_STAGE="m6"、`:26-41` 顶层键、`:43` build、`:80` validate（`:85-90` 拒收多余键）、`:144` required_decision_types、`:152` derive_content_status——README §2.2 与 D-03 引用逐字成立。
- `knowledge_extraction/inputs.py:58` `latest_succeeded_step_run`、`:115` `resolve_m3_outputs`、`:186` `m4_is_sealed`、`:245` `resolve_m4_inputs`、`:1-6` supersede 文档——逐字成立。
- `knowledge_extraction/step.py:1-6`（supersede 文档）、`:208-215`（单条 `candidate_set` 修订，C1 对账属实）、`:265-285`（`candidate_package` 13 内容键，C2 属实）、`:311-362`（m4 StagePackage）、`:373-390`（finish 输出 [stage_package, candidate_set, candidate_package]）——§5.1 M4 行字段全部存在。
- `validation/package.py:52` `assemble_gate_results`（`scope="corpus_only"` 默认）、`:171` `assemble_validation_package`（返回含 `scope`/`target_consumption_level`/`gate`/`gate_results_revision_id`/`corpus_package_revision_id`/`corpus_spans_revision_id`/`candidate_package_revision_id: None`）——C3 对账属实、§5.1 M5 行字段全部存在。
- `validation/step.py:59` `run_m5` 签名、`:251` `scope: corpus_only`、`:275-278` StagePackage `validation.passed=gate["passed"]`——C4 属实。
- `orchestrator/gate.py:14-23` 八项 GATE_CHECKS、`:124` `_read_package_content` 用 `yaml.safe_load`（第 57 条）、`:130` `effective_step_runs`；`orchestrator/module.py:108` `ModuleBinding`、`:83-89` StepOutcome awaiting_human 须带非空 `pending_queue_artifact_ids`——逐字成立。
- `contract_registry/registry.yaml:44-133` 登记 m1/m2/m3/m5/m8 无 m6 行；`catalog.py:142` `module_for`、描述符 12 键——§5.3 Orchestrator 登记需求的落点成立。
- `dataset_compiler/packs.py:35` 四 task、`:71`、`:144`、`:262` `knowledge_chain: "not_compiled"`、`:301-307` 缺陷码；`gate.py:392-404`（not_compiled→not_evaluated）、`:434`——逐字成立。
- Ledger 引用（service.py 442-526/528-597/599-638/664-676/678-716/718-774/777-843（:822-829 human_event 校验）/885-920/922-963/965-989/319-345/412-440/1364-1398/1400-1428/1430-1482/1132/1187；store.py:160-166 human_events、:168-179 stage_checkpoints.rework_impact_report_revision_id）与 impl-05 R1 实测一致。
- 场景数据实测：`spans.yaml` 中 s08=`七政旺宮星度`（第 4 字「宮」，corrections `char_index: 3` 吻合）、s05 bbox.x 可加 1.0、s03=`三辰通載目錄`、s04=`卷第一`、p0001_s02=`（宋）錢如璧撰`（as_003 modify 内容吻合）；BDD 3.1 计数 3/3/2/4/0.75 与 act/03 公式、expected_review.rework 全链自洽。fixture `m4/` 金标五件在（act/04 桩可用）；m4 finish 输出恰 1 `candidate_package`+1 `candidate_set`。
- 可执行性发现：F1、F2、F3（阻断）。

## 四、独立性

- `gate.py` 不 import model/propagation/step/rework（contract + verify grep + AST 用例）；`acceptance.py` 不 import 五模块、不信任 close_review 返回报告、自算可达集与引文哈希；`propagation.py` 允许只 import `model.content_hash`。
- 写范围仅 `pipeline/review/**` + `openspec/acceptance/m6-data-fields.sh`；与 knowledge_extraction/orchestrator/contract_registry/dataset_compiler/validation/ledger 零写交集；不写 run_all.sh、fixture；`testing/` 非生产隔离有 grep 判据且仅 tests/ 与 acceptance.py 可 import。
- 防同错同过：m6-data-fields.sh 永调仓库内规范 `verify.sh`；acceptance 十四项自行重算（含按 revision_status_events 判冻结时刻 sealed）。

## 发现（编号｜严重度｜文件:行号｜问题｜依据 文件:行号｜修改建议）

- F1｜阻断｜act/05.yaml:15（步骤 2）｜默认映射公式 `{kind: list(review_events.required_decision_types(对象, entity_kind=kind)) 合并}` 对 school_view 恒返回 `(review_source_fidelity, review_school_attribution)`（`review_events.py:144-149` 恒含 source_fidelity），合成队列 5 项；而 D-04 默认映射、BDD 1.1「队列 4 项」、BDD 5.2「record_decision 4 次」、testing/data/m6_decisions.yaml 4 条、expected_review（decisions 4/checkpoints 5、rereview.queue 的 sv 项仅 school_attribution）全链为 4 项——按 contract 实现金标路径 `close_review` 必因 1 项未决被拒｜act/05.yaml:15；README.md:82（D-04）；BDD.md:9,39；act/04.yaml:15,18-20；`review_events.py:144-149`｜步骤 2 默认改为 D-04 映射 `{assertion: ["review_source_fidelity"], school_view: ["review_school_attribution"]}`（或在 D-04 处改口径并同步 BDD/expected 为 5 项——不得两处并存）。
- F2｜阻断｜act/01.yaml:53-54、BDD.md:11、BDD.md:42、act/02.yaml:21｜modify/锚点语义三处矛盾：(a) act/01 两个具名用例 `test_decision_modify_requires_event_verdict_modify`、`test_decision_accept_forbids_modified_revision` 与 BDD 1.3 前两支要求 `build_review_decision`/`decision_event` 校验 `modified_revision_id`，但两者契约均无该参数（`review_events.py:43-56`、act/01 decision_event 签名），测试按名不可写出；(b) BDD 5.5 称 modify 决定事件 `target.artifact_revision_id` 指向 modified_revision_id，与 act/05 步骤 2（事件锚恒 = 队列 seen）矛盾；(c) act/02 `decision_anchoring` 的「修订锚点 == seen_revision_id」所依据的字段不在 `decision_entries` 九键集内｜act/01.yaml:26-28,53-54；BDD.md:11,42；act/02.yaml:15,21；act/05.yaml:25-29；`review_events.py:43-56,85-90`｜统一语义：事件 `target.artifact_revision_id` 恒 = seen（候选集修订），modify 的替换锚走 `current_target_revision_id`（act/06 已有）；删除/改名 act/01 两个用例与 BDD 1.3 前两支（或把 modified_content 校验明确放在 record_decision 层并改用例名）；act/02 `decision_anchoring` 改为校验 `carried_from_revision_id`/`decision_revision_id` 形态，或在 `decision_entries` 契约中显式增补锚点键。
- F3｜阻断｜act/01.yaml:19 vs act/05.yaml:21｜`build_review_queue(*, candidates, required_decision_types)` 契约签名缺 `seen_revision_id`，同句行文「seen_artifact_revision_id 由调用方以同参 seen_revision_id 传入」与 act/05 步骤 5 调用（`seen_revision_id=…`）均含该参——签名两种理解，按契约实现将在 act/05 调用处 TypeError｜act/01.yaml:19,25；act/05.yaml:21｜act/01 签名补 `seen_revision_id`（keyword-only）。
- F4｜重要｜ACCEPTANCE.md:19、TDD.md:25-37｜「用例数阈值等于具名用例累计（16/36/50/58/70/80/88/98/104/110）」不成立：逐条点数各 ACT 具名用例为 18/19/14/8/14/11/9/12/8/9，累计 18/37/51/59/73/84/93/105/113/122，每档阈值均低于累计（差 2/1/1/1/3/4/5/7/9/12）；TDD §1 亦无 impl-05 式「以 tests 段列名逐条计数」口径｜act/01–11.yaml tests 段（awk 实测计数）；ACCEPTANCE.md:19｜把阈值改为 18/37/51/59/73/84/93/105/113/122（或在 TDD 明示「阈值为下限、具名用例为必写集」并同步 ACCEPTANCE 措辞）。
- S1｜建议｜act/11.yaml:65｜commit.message「12 checks PASS, workbench seed and real upstream BLOCKED」与 contract 11 PASS + 3 BLOCKED（含 snapshot_projection）不符｜act/11.yaml:22-36｜改为「11 checks PASS, snapshot / workbench seed / real upstream BLOCKED」。
- S2｜建议｜act/11.yaml:34｜snapshot_projection 说明逐字「BLOCKED 前置缺失: M7 创世汇编」含输出行前缀，按 `BLOCKED <名> <说明>` 格式将双重；且「M7 创世汇编」非 §19 第一列（第 61 条授权措辞）｜act/11.yaml:34；TDD.md:51｜说明定为「前置缺失: M7 创世汇编」，并在 TDD §2 注明该项经第 61 条豁免 §19 行名校验。

## 判定

**REWORK**（阻断 3：F1、F2、F3；重要 1：F4；建议 2：S1、S2。阻断修复并复审前不得派发 K1；F1/F2/F3 均为文本级语义统一，不动摇包结构。）

（审查者：W4-R5；以 HEAD `91e5348` 只读核查；`git diff --check` 无输出。）
