# impl-05：M4 Knowledge Extraction（§12）最薄接入

状态：`READY_FOR_REVIEW`（W4-G 定稿 2026-09-13，依 `G7-RULINGS.md` §1 P1–P9、§3 impl-05、§9 第 2/10/13/17/21 条、§9.2 第 27 条、§9.3 第 43 条；未经实现；派发前置见 §7 与 `PROMPT-G1.md`）

## 1. 目标

在 `pipeline/knowledge_extraction/` 落地规格 §12 的 M4 **最薄接入**（§22.3 阶段 1：M4 属「首纵切后、薄用」；G7-RULINGS §9.3 第 43 条将其排入下一波，用于让 §20.1/§20.4/§20.8/§20.9 由 BLOCKED 转判）：

1. **不调用任何模型**（P6）。候选来自「现有任务管线形态」的产出——人或外部 Agent 按工位 5 格式写出的草稿（`run_task.py --model manual` 的上游），以及 fixture 金标；二者经 Adapter 规范化为「提交件」，每路（类别 × 路别）一个 m4 submit StepRun 登记为 Ledger 已封存修订。
2. M4 assemble StepRun 只读 Ledger 冻结修订：M3 StagePackage、`corpus_spans`、`technique_profile`（Contract Registry 快照）与全部提交件；确定性完成证据定位（页块 offset + quote + quote 哈希）、状态上限、类别分离、双路差异检出、人工闭集 ID 分配，输出 `candidate_set` 与 m4 StagePackage。
3. 双路不一致时进入 §5 的「M4 类别分歧」队列：`awaiting_human` → 类别裁决人工事件（每条即时 Checkpoint）→ `resume`。
4. 以独立实现的候选 Gate 判定输出契约；以独立实现的 `acceptance.py` 重算 13 项判定。
5. 冻结「专家审核决定」人工事件形态与内容成熟度推导纯函数（`review_events.py`），供 M6 签发复用；**签发 StepRun 本身归属 M6（D-07），本包不建签发运行，也不伪造任何 `expert_verified`（P7）**。

本批不做（报 BLOCKED 或推迟）：生产模型 A/B 与复核模型 C（§12.2:572）；SemanticSpan 输入（§12.2:561）；L1/L2/L3 自动扫描判层（§12.1）；`omen_carrying` / `condition_affordance` 等 Tag 字段（§16.3.2:801-815）；ApplicabilityRule 与条件 AST（§13 G6）；legacy 工作台候选导入进 run_all（§20.7，见 §5.3）；专家签发 StepRun（D-07）。

完成判据（本批唯一的「做完」定义；数字按 §4 全部裁决固定）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/knowledge_extraction/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"   # OK（用例 ≥ 129，K4 止；K5 另加 5 条）
bash openspec/acceptance/m4-stage-gate.sh; echo exit=$?
# 期望：13 行 PASS + 3 行 BLOCKED（cross_model_extraction / semantic_span_input / term_layering_scan）
#       末行 SUMMARY pass=13 fail=0 blocked=3；exit=2
bash openspec/acceptance/run_all.sh | tail -1            # 与开工基线逐字相同（本批不改 run_all.sh；20.6 仍 BLOCKED、20.7 仍 FAIL）
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?   # 与开工基线相同（本批不得改变 M3 结果）
test ! -e pipeline/tools/import_legacy_candidates.py; echo $?   # 0（D-12：本批不得创建）
```

`m4-stage-gate.sh` 是规格 §19.0:908 已登记的「M4 分类与人工裁决缺口」判据（修复后应 exit 0）。本批只做无模型薄接入，跨模型抽取、语义 Span 输入与自动判层未做，所以返回 **2**（无 FAIL、有 BLOCKED），差距仍未关闭。

## 2. 依据（只读来源）

规格 `openspec/learn-system-blackbox-architecture.md`：

- §2:40（模型输出只能成为候选，不能绕过校验与人工审核）
- §5:103-110（M1→M8 顺序）、§5:119-124（PendingQueue 第 3 队列「M4 类别分歧」、第 4 队列「M6 待签发」）、§5:128（canon / homographs 由 Contract Registry 登记为 M4 冻结输入）、§5:130（Review Console M4 模式）
- §6.1:141-149（CandidatePackage 位于 CorpusPackage 与 ValidationPackage 之间；失败为零）
- §7:181-207（StepRequest/StepResult；只读冻结修订）、§7.1:211-226（一阶段多任务；awaiting_human、`record_human_event`、`resume`）
- §8:232-251（StagePackage 信封）、§8.1:257-267（entity_id 与 artifact_revision_id；ReviewDecision 必记二者）、§8.1:273-282（`as_`/`pr_`/`co_`/`hg_` 冻结格式）、§8.1:298（StagePackage 的 ArtifactRef 携带 `stage_package_id`）、§8.1:312-318（`sch_`/`sv_`/`cg_`/`pat_`）
- §8.2:337-347（七个内容成熟度状态）、§8.2:351-364（八类审核决定，禁止单一 expert_verified）、§8.2:368-380（九个错误码）、§8.2:432-440（多轴正交）
- §11:511-521、§11.1:525-528（evidence_level）
- §12.1:534-557（三层判层；543 行「L1 零歧义、100% 准确」；550 行禁止裸绑字面；557 行 new_concept_candidates）
- §12.2:559-574（候选类别；570 行 SchoolView 最小字段；572 行不同类别不得一次混合完成、A/B 独立、C 重读原文、分歧进人工队列；574 行全部留痕）
- §13:580（M5 不修改 Candidate）、§13.1:590-592（G3、G4；G4 明确「命例入 Case 层、注文/异文/校勘入独立 editorial layer」——**本包 assertion.layer 闭集由此与 INTERFACES §3.2 对齐为 `general / case / editorial`**）
- §14:618-627（M6 签发；M4 模式输出类别 ReviewDecision；Model Adapter 属 M4）
- §16.1:674-678（消费级别准入）、§16.3.2:801-815
- §17:836（事务序列）、§17.1:840-846（每 task 一个 Checkpoint；人工决定即时落盘）
- §19:878（M4 差距行）、§19:880（M6 行：496 rules、original_text 非空 0）、§19.0:908（`m4-stage-gate.sh`）、§19.1:929-931（units 与工作台库冻结）
- §20:935（BLOCKED 行名取 §19 第一列）、§20:937（20.1）、§20:943（20.7 准入阈值）、§20:944（20.8）、§20:945（20.9）
- §22.1:966-969、§22.2:977-980（M4 候选沿用现有任务管线，少量人工签发；QizhengFactSet 匹配）、§22.3:991、§22.4:999

其他：

- `openspec/id-prefix-registry.md` §3.1–§3.4（:54 七政首批流派「正式登记随 M4 首次抽取时冻结」）
- `openspec/legacy-storage-transition.md:26,28,52,54`（units 冻结、新 M4 从 CorpusPackage 生成；工作台库只能经独立 legacy_candidate 导入）
- `openspec/acceptance/run_all.sh:242-270`（20.7 判定逻辑）
- `openspec/schemas/stage_package.schema.json`、`artifact_ref.schema.json`（`artifact_kind: stage_package` 分支）、`step_request.schema.json`、`step_result.schema.json`（`validation_report_ids` 允许空数组）
- **Ledger（impl-01，已验收 `1f32177`；本包只读）**：
  - `service.py:66`（`RUN_ARTIFACT_TYPES = ("configuration", "technique_profile")`）、`:129-131`（`list_transformations(step_run_id)` **只返回 `transformations` 表行，不含输入/输出修订号**——步骤 1 修正点 F1）、`:150`（`list_checkpoints(edition_part_id, stage)`）、`:405-410`（`begin_step_run`，stage 由配置内容 `"stage"` 推导）、`:442-457`（`put_artifact`，`rights_scope="internal"`，返回 `(artifact_id, revision_id)`）、`:528-597`（`put_run_artifact` 只收 configuration/technique_profile，写入即 sealed，**返回二元组**——修正点 F2）、`:599`（`seal_revision`）、`:718`（`register_stage_package`）、`:777-790`（`record_transformation` 含 `model_ref`、`human_event_revision_ids`）、`:885`（`await_human`）、`:922-963`（`record_human_event`，`decision_type` 只收八类或 None，**不消费 token**）、`:965`（`resume`）、`:1132-1185`（`finish_step_run`，只校验 StepResult；无 StagePackage 亦可）、`:1187`（`fail_step_run`）、`:1364-1377`（`write_checkpoint`）、`:1606`（`read_object`）
  - `store.py:71-75`（`stage_packages(stage_package_id, artifact_id, stage)`）、`:126-166`（`transformations` / `transformation_inputs` / `transformation_outputs` / `human_events` 表）、`:552-576`（`list_transformations` 与 `list_transformation_inputs/outputs`）
  - `states.py:57-66`（`REVIEW_DECISION_TYPES` 八类）、`ids.py:13-33`（19 个前缀家族；`new_id` 支持 `school_view_id` / `conflict_group_id`；`validate` / `kind_of`）、`errors.py`（`LedgerError` / `NotConsumable` / `SchemaViolation` / `InvalidIdentifier`）
  - `fixture_ingest.py:40-47`（`STAGES=("m1","m2","m3")`、m3 阶段输出类型 `corpus_package`；**灌入 m3 时不写 `corpus_spans`**）
- `pipeline/corpus_compiler/step.py:236-251,272-330,335`（`run_m3` 的 `corpus_package`、StagePackage `payload.spans_revision_id`、`manifest.content_sha256`、`output_artifact_ids`）
- `pipeline/validation/inputs.py`（M5 当前 `scope: corpus_only`，经 `m3_step["result_json"]["output_artifact_ids"]` + `artifacts.artifact_type` 只读 SELECT 定位 M3 输出——本包 `resolve_m3_outputs` 与之一致）
- `docs/blackbox-spec-rework/work-items/impl-04-dataset/README.md` §4 D1 与知识链 `not_compiled`、§7 的 `evidence_map_pack` 只有尾链四段
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md` §2.4 M4 卡片、§3.1 `evidenceLink`、§3.2 `candidate_set.schema.json`、§4 临时闭集（M4 行仍为旧命名，见 §10 待裁决 N1）、§6 I-11；`check_interfaces.py`（`REQUIRED_TYPES` 未枚举 M4 类型）
- 任务管线（只读调研，见 §5）：`pipeline/HANDBOOK.md:41-54,89-96,137,249-261,263-304`、`pipeline/schemas/core/SCHEMA.md:44-76`（`relation` 五值；**无 `layer` 字段**，M4 的 `layer` 取 §13.1 G4 语义）、`pipeline/runner/run_task.py:89-135,143-178`、`pipeline/runner/config.yaml`、`pipeline/validators/compare_drafts.py:65-160`、`pipeline/validators/validate_assertion_task.py:40-90`、`pipeline/tools/gen_assertion_task.py`、`pipeline/tools/merge_assertions.py`、`pipeline/TASKGEN_HANDOFF.md:147-157`、`pipeline/task-templates/stage5_assertions*/INSTRUCTIONS.md`、`pipeline/schemas/shared/canon/*.yaml`（6 文件，`closed_set_size` 合计 49）、`pipeline/registry/schools/`（只有 `_TEMPLATE.yaml`）
- `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二–§三；`knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §3.2–§3.3
- fixture `pipeline/corpus/_fixture/mini_ed01/`：`spans.yaml`（sha256 `ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef`；43 条，page_001 4 条、page_003 39 条）、`source/transcript_v1.md`（仅书名页与目录）、`verify.sh:333-400`（**V5/V6 只覆盖 m1–m3**，m4 金标需同步扩展——修正点 F5）、`README.md` §1（内容不作知识来源）
- `pattern_knowledge_workbench/assets/ge_ju_database.sqlite`（sqlite 实测 `ge_ju_rules` 496 行、`original_text` 非空 0；`ge_ju_schools` 中 `guo_lao` 类型为 book）

## 3. 范围

写：`pipeline/knowledge_extraction/**`（新建）、`openspec/acceptance/m4-stage-gate.sh`（ACT 07 新建）。

主 Agent 写（执行者不写，且属共享面独占 ACT，P4）：附录 A 的 fixture 金标 `pipeline/corpus/_fixture/mini_ed01/m4/` 与 `expected/m4.stage_package.yaml`，以及 fixture `verify.sh` V5/V6 的 m4 扩展（见 §10 待裁决 N2 与 §9 用户待办）。

禁止：

- 改 `openspec/acceptance/run_all.sh`、`m3-coverage.sh`、规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`pipeline/orchestrator/**`、`pipeline/contract_registry/**`；
- 改 `pipeline/TASKS/`、`task-templates/`、`runner/`、`tools/`、`validators/`、`units/`、`registry/`、`schemas/`、`pattern_knowledge_workbench/`；创建 `pipeline/tools/import_legacy_candidates.py`（D-12）；
- 改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、`G7-*.md`、其他 work-items 目录、任何 `ACCEPTANCE.md` 的 §5；
- 新增依赖、新增 ID 前缀；调用模型 API，或 import `requests`/`openai`/`anthropic`/`httpx`；
- 生产代码读 fixture 路径或工作目录「最新文件」（例外只有 Adapter 入口：`adapters/registry.py` 读 `--canon-dir`、`adapters/task_pipeline.py` 读调用方传入的草稿与模板、`adapters/legacy_workbench.py` 以只读方式打开工作台库；它们的产物必须先登记进 Ledger，M4 核心只读 Ledger）；
- 生产代码 import `pipeline/validators`、`pipeline/tools`、`pipeline/runner` 下的脚本（只作规则参照，按本包契约重写）；
- M4 产出任何对象的 `content_status` 高于 `needs_expert`（不得出现 `cross_model_reviewed`、`expert_verified`）；
- 执行者写台账、写 `ACCEPTED`、伪造人工签发（P7）。

## 4. 主 Agent 决定（执行者不重议）

本节取代原 §4 待裁决清单。裁决来源：`G7-RULINGS.md` §1 P1–P9、§3 impl-05、§9 第 2/10/13/17/21 条、§9.2 第 27 条、§9.3 第 43 条，与 `reviews/G7-DRAFTS-REVIEW-R2.md` §4 的 G7-Q01～Q16（impl-05 条目）。**未单列的细节默认采纳草稿推荐**。原 16 条 D-xx 与 R2 编号一一对应如下。

- **D-01 / G7-Q01 首切片零模型调用 → A（P6）**。候选只经提交件 Adapter 登记，渠道闭集中只收 `fixture_gold`、`task_pipeline_manual`；`model_adapter` 渠道在 `run_m4_submit` begin 前拒收；验收 `cross_model_extraction` 恒 BLOCKED。Ledger `record_transformation` 已有 `model_ref` 参数（`service.py:787`），日后接入 Model Adapter 只新增渠道，不改 M4 Interface。
- **D-02 / G7-Q02 fixture 候选金标 → A，且金标进 fixture 必须作为独立独占 ACT（P4）**。主 Agent 在 `pipeline/corpus/_fixture/mini_ed01/m4/` 增四个金标文件（assertion 两路、concept_mention 一路、类别裁决一份）与 `expected/m4.stage_package.yaml`，并同步扩展 fixture `verify.sh` V5/V6 到 m4；该写入是与 impl-05 实现分离的独占 ACT（见 §9 用户待办 / §10 N2 / ACT.yaml `preconditions`）。K4 以它落地为强制前置，缺失即停手。
- **D-03 / G7-Q03 Span 层 → A**。薄接入消费 StructuralSpan；`candidate_set` 与 m4 包写 `span_layer: structural`；验收 `semantic_span_input` 恒 BLOCKED。
- **D-04 / G7-Q04 提交件登记形态 → A**。每路（category × lane）一个 m4 submit StepRun：配置 `task: submit`，冻结输入仅 M3 包与 `corpus_spans`，输出 `candidate_submission`；assemble StepRun 再把全部提交件修订列为冻结输入。路间隔离由 Ledger 冻结输入集合证明。
- **D-05 / G7-Q05 Contract Registry 冻结输入 → A**。Registry Adapter 读 canon 目录（`pipeline/schemas/shared/canon/`，6 文件，`closed_set_size` 合计 49）生成运行级 `technique_profile` 修订（含 canon 快照与文件哈希、`homographs: []`、`glossary: []`、`schools: []`）；流派闭集本批不冻结，任何 `school_id` 一律 REF_001 拒收。
- **D-06 / G7-Q06 术语判层 → A（只校验不扫描）**。提交件自带的 `co_shared_*` / `co_qizheng_*` 引用必须存在于冻结 profile，字面 ∈ {surface, aliases} 且等于证据 quote；自动扫描报 BLOCKED `term_layering_scan`。起草实测（canon 全部字面对 43 条 Span 子串匹配 → 6 次命中且全为误命中：5×「辰」、1×「胎」）作为 §12.1 规格问题的证据留存于 README §10。
- **D-07 / G7-Q07 签发归属 → A，且 P7 加裁**。签发 StepRun 归属 M6 薄接入；本包只冻结 `review_decision` 事件形态与 `derive_content_status` 纯函数（ACT 06）。**不得伪造人工签发**：测试只用 fixture 已登记的人工事件（类别裁决 `ruling_m4_d001.yaml`）或明确标注的测试替身（合成 `review_decision` 事件仅用于纯函数单测，不代表任何真实专家决定）；真实 `expert_verified` 需要用户撰写的决定表时，依赖它的判定一律 BLOCKED 而非 PASS（§9 用户待办）。
- **D-08 / G7-Q08 expert_verified 齐备条件与 verdict 闭集 → A**。首切片最小集：`review_source_fidelity` 必需；候选 `school_ids` 非空或对象是 SchoolView 时 `review_school_attribution` 也必需；verdict 闭集 `accept / modify / reject / request_evidence / school_dispute`；推导优先级：必需类型有 `reject` → `deprecated`；有 `school_dispute` → `disputed`；有 `modify` 或 `request_evidence` → `needs_expert`；必需类型全 `accept` → `expert_verified`；否则保持原状态。所见修订与当前候选修订不同的决定不计入。**仅适用首切片 INTERNAL_DEMO；PUBLIC_RELEASE 前须由用户重定。**
- **D-09 / G7-Q09 人工闭集 ID → A**。assemble 配置修订写 `id_range`（首切片 as / pr / pat 均为 1–99），同一 `candidate_set` 内查重（ID_002）；本批拒绝 M4 重跑，重跑保号推迟到重跑工作包。
- **D-10 / G7-Q10 新 artifact_type 与内容 Schema → P2 + P3**。artifact_type **只提名**（清单见 §6.1.1），由该波登记 ACT 一次性写入 `INTERFACES.md` §4 临时闭集；本包不写该文件。内容结构以代码内草案契约表达，`schema_version: "0.1.0-draft"`；准入层对 `PUBLIC_RELEASE` 以 `draft_schema` 拒绝；首纵切不向 `openspec/schemas/` 新增文件。
- **D-11 / G7-Q11 §19.0 判据脚本 → A**。新建 `openspec/acceptance/m4-stage-gate.sh`（13 PASS + 3 BLOCKED，exit 2）。BLOCKED 行名逐字取 §19 第一列：「M4 Knowledge Extraction」「M3 Corpus Compilation」「Contract Registry」。
- **D-12 / G7-Q12 §20.7 legacy 候选 → A**。首切片不接 run_all，不在 `pipeline/tools/` 建 `import_legacy_candidates.py`；可选 ACT 08 在本包宿主内写 fail-closed 纯函数 `admit_legacy_rules`（实库 496 条全部以 SCH_001 拒收），只作准入规则的可执行说明。M4 薄接入**不能也不应**改变 20.7 的 FAIL。
- **D-13 / G7-Q13 被拒候选不阻断 Gate → A**。被拒条目逐条写入 `rejected`（原因码取 §8.2 九码），**不阻断 Gate，只计数**，计数进 m4 包、由 M5 报告。提交件整体形状错误仍在 begin 之前拒绝。
- **D-14 / G7-Q14 类别裁决 decision_type → A**。`decision_type=None`，事件内容写 `event_kind: category_ruling`。
- **D-15 / G7-Q15 M3 产出定位 → A，且上游只认 succeeded 的 M3 包（P5）**。只认「`status == "succeeded"` 且 Transformation `operation == "compile_corpus"` 的输出恰含 1 个 `corpus_package`、1 个 `corpus_spans`」的 m3 StepRun；0 个或多于 1 个即拒绝。输出定位改用该 StepRun 的 `result_json.output_artifact_ids` + `artifacts.artifact_type` 只读 SELECT（与已验收的 impl-03 `resolve_m5_inputs` 同法，修正点 F1），**不得依赖 `list_transformations` 返回输出**（它只返回 `transformations` 表行）。测试脚手架 = `ingest(stages=("m1","m2"))` → `run_m3` → M4。
- **D-16 / G7-Q16 任务包模板与术语表 → A**。`export_task_inputs` 只导出输入（segments/spans 取自 Ledger `corpus_spans`），INSTRUCTIONS 由调用方指定模板路径（默认通用 `stage5_assertions`），`task.yaml` 记录 `instruction_version` 与 `id_range`。

## 5. 已固化默认（执行者不重议）

1. **消费级别与状态上限**：M4 产出 `content_status ∈ {machine_extracted, disputed, needs_expert}`；不得出现 `cross_model_reviewed` / `expert_verified`。
2. **路别闭集**：`lane ∈ {a, b, c}`；首切片拒收 `c`（复核路预留）。渠道闭集 `{fixture_gold, task_pipeline_manual, model_adapter, legacy_workbench}`；首切片只收前两个。
3. **规范化字节**：`canonical_json(obj) = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")`；`sha256_hex(data)`。YAML 导出用 `yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)`。
4. **Checkpoint 粒度**（§17.1:843）：submit StepRun 1 个；assemble 每路 1 个 → `reconcile` → 每条裁决 1 个（task_id = dispute_id）→ `assemble`。
5. **Gate 独立**：`gate.py` 不 import `assemble` / `submission`，页块自算；`acceptance.py` 不 import `assemble` / `gate` / `submission`，不读 `run_m4`/`resume_m4` 返回的 gate 报告。
6. **异常分层**照搬 impl-02：begin 之前的解析、拒绝原样外抛；begin 之后分 `input_contract`/`candidate_gate`/`internal`（以及 assemble 的 `assemble`）失败封存。
7. **测试宿主**：测试只用 `tempfile` 目录；读 fixture `spans.yaml` 仅作只读输入；生产代码非测试文件不出现 `_fixture`。
8. **派发分组**：K1 = ACT 00–02（纯函数）；K2 = 03–04（Ledger，前置 impl-02 `ACCEPTED`）；K3 = 05–06；K4 = 07（前置 fixture 金标独占 ACT 落地）；K5 = 08（可选）。

## 6. 契约

### 6.1 上游输入契约

**M3（impl-02，已验收）**

- m3 StepRun `status == "succeeded"`；`list_transformations(m3_step_run_id)` 中存在 `operation == "compile_corpus"` 的记录（`service.py:129-131` 只返回表行，故仅用于确认 operation）。
- 该运行 `result_json["output_artifact_ids"]` 中按 `artifacts.artifact_type` 只读 SELECT 恰有 1 个 `corpus_package`、1 个 `corpus_spans`、1 个 `coverage_report`（与 `pipeline/validation/inputs.py` 的 `_M3_CONTENT_TYPES` 同口径）。
- m3 StagePackage（经 `stage_packages` 表只读 SELECT 定位：`stage == "m3"` 恰 1 条，`store.py:71-75`）内容 JSON：`payload.spans_revision_id` 等于上面的 corpus_spans 修订；`payload.gate_profile == "structural_only"`；`manifest.content_sha256 == sha256(corpus_spans 字节)`。
- `corpus_spans` 字节为 YAML。顶层键：`work, source_id, edition_part_artifact_id, evidence_level, content_status, span_count, batch_count, spans`。Span 键：`span_id, batch_id, page, line_index, start_offset, end_offset, text, source_anchor`。`start_offset/end_offset` 相对页块（同页 Span 文本以 `"\n"` 连接），偏移语义见 §6.3。
- M4 继承 `evidence_level`（mini_ed01 为 `glyphbox_level`），不得提升。
- `fixture_ingest` 灌入的 m3 包没有 `spans_revision_id`，必须拒绝。

**Contract Registry（D-05，运行级 `technique_profile`，canonical JSON）**

```yaml
schema_version: 0.1.0-draft
technique_id: qizheng
canon:
  files: [{name: bagua.yaml, sha256: <hex>}, ...]          # 按文件名排序，6 个
  concepts: [{concept_id: co_shared_stem_01, surface: 甲, aliases: [], domain: stem, rev: 1}, ...]   # 按 concept_id 排序，合计 49
homographs: []     # 首切片为空（目录不存在）
glossary: []       # 首切片为空（qizheng 术语表不存在）
schools: []        # 首切片为空（流派闭集未冻结）
```

**Ledger（impl-01，不改其行为）**：`put_run_artifact`、`begin_step_run`、`put_artifact`、`seal_revision`、`write_checkpoint`、`await_human`、`record_human_event`、`resume`、`record_transformation`、`register_stage_package`、`finish_step_run`、`fail_step_run`；读：`get_revision`、`get_step_run`、`list_step_runs`、`list_transformations`、`list_checkpoints`、`read_object`；允许经 `reader.store.conn` 只读 SELECT（`artifacts.artifact_type`、`stage_packages`、`frozen_inputs`、`human_events`、`processing_runs`；缺口清单以 impl-00 README §5.2 为唯一清单）。

#### 6.1.1 artifact_type 提名（P2；本包只提名，登记由该波独占 ACT 写入 INTERFACES §4）

- **新增（提名）**：`candidate_submission`、`candidate_lane_set`、`dispute_queue`、`candidate_set`、`candidate_package`。
- **复用（已在闭集）**：`configuration`、`technique_profile`、`human_event`、`validation_report`、`step_log`、`failure_report`、`stage_package`。
- `candidate_set` 的内容结构以代码内草案契约表达（§6.3），`schema_version: "0.1.0-draft"`（P3）；`PUBLIC_RELEASE` 以 `draft_schema` 拒绝。
- 与 `INTERFACES.md` §4 M4 行现有旧命名（`candidate_batch` / `model_run` / `candidate_diff_report`）的对账见 §10 待裁决 N1。

### 6.2 提交件 `candidate_submission`（canonical JSON；一件一类，§12.2:572）

```yaml
schema_version: 0.1.0-draft
category: assertion          # 闭集 assertion / pattern / school_view / concept_mention
lane: a                      # 闭集 a / b / c；首切片拒收 c
channel: fixture_gold        # 闭集 fixture_gold / task_pipeline_manual / model_adapter / legacy_workbench；首切片只收前两个
technique_id: qizheng
producer: {kind: fixture, name: mini_ed01, model_id: null, prompt_sha256: null, response_sha256: null}   # kind 闭集 fixture / human / external_agent / model
source_task: null            # 或 {task_id, instruction_version}
skipped: []                  # 可选：工位 5 的 skipped_segments 原样保留
adapter_notes: []            # 可选：Adapter 丢弃字段的说明
items: [...]
```

各类 item 键（未列出的键 → SCH_002「类别混合」；缺必填 → SCH_001）：

| category | 必填 | 可选 |
|---|---|---|
| assertion | proposition, relation, evidence | conditions, exceptions, concept_refs, school_ids, layer, status |
| pattern | name, assertion_propositions, evidence | interpretation, status |
| school_view | school_id, subject, claim_propositions, changes_current_judgment, evidence | conflict_key, status |
| concept_mention | surface, evidence | concept_ref, status |

- evidence 条目：必填 `source_span_id`、`support_type ∈ {direct, interpreted}`；可选 `span_char_start` 与 `span_char_end`（必须成对，相对 Span 文本）、`quote`。
- `relation ∈ {supports, qualifies, opposes, corresponds, equivalent}`（SCHEMA.md §4）。
- **`layer ∈ {general, case, editorial}`，缺省 `general`**（§13.1 G4「通则 / 命例 / 注文·异文·校勘」；与 INTERFACES §3.2 一致。**修正点 F3**：原草稿写作 `{main, commentary, editorial, case}` 且缺省 `main`，其中 `main/commentary` 是 M3 语料分段层字段（`HANDBOOK.md:137`）而非 M4 主张层，已按 §13.1 G4 改正）。
- `status ∈ {null, machine_extracted}`，其他值整件拒收（与 AST_002 同口径）。
- `subject = {kind: assertion|pattern, key: <proposition 或 pattern name>}`。

### 6.3 CandidatePackage 结构草案（三层）

坐标语义：`candidate_set` 的证据 `start_offset/end_offset` 为**相对页块的绝对偏移**（与 `corpus_spans` 的 `start_offset/end_offset` 同一坐标系：`start_offset = span.start_offset + 局部起点`）；`quote` 与 `quote_sha256` 使 M5/M8 可独立复算。与 INTERFACES §3.1 `evidenceLink` 的 `char_start/char_end`（span 相对）命名与语义差异见 §10 待裁决 N3。

**(1) `candidate_set`**：纯内容、canonical JSON、不含任何修订号；无 SchoolView 时字节确定。

```yaml
schema_version: 0.1.0-draft
technique_id: qizheng
source_id: src_sanche_ed01
edition_part_artifact_id: art_…e1
evidence_level: glyphbox_level          # 继承 corpus_spans
span_layer: structural                  # D-03
source_channels: {assertion: {a: fixture_gold, b: fixture_gold}, concept_mention: {a: fixture_gold}}
assertions:
- assertion_id: as_qizheng_000001        # id_range 顺序分配（D-09）
  proposition_id: pr_qizheng_000001
  proposition: 宋錢如璧撰
  relation: supports
  evidence:                              # 按 (Span 序, start_offset, end_offset) 排序
  - {source_span_id: ss_sanche_ed01_p0001_s02, support_type: direct, start_offset: 8, end_offset: 12, quote: 錢如璧撰, quote_sha256: <hex>}
  - {source_span_id: ss_sanche_ed01_p0001_s04, support_type: direct, start_offset: 27, end_offset: 32, quote: 宋錢如璧撰, quote_sha256: <hex>}
  conditions: []
  exceptions: []
  concept_refs: []
  school_ids: []
  layer: editorial
  content_status: machine_extracted      # M4 上限：machine_extracted / disputed / needs_expert
  origin: {lane: a, item_index: 1}
patterns:                                # 键：pattern_id, name, assertion_ids, evidence, interpretation, interpretation_status(not_captured|captured), recognition_rule_status(not_captured), content_status, origin
school_views:                            # 键（§12.2:570）：school_view_id(sv_), school_id(sch_), subject_entity_id, claim_refs, conflict_group_id(cg_|null), changes_current_judgment, source_refs[{source_id, source_span_id}], evidence, content_status, origin
concept_mentions:                        # 已绑定：surface, concept_ref, evidence, content_status, origin
new_concept_candidates:                  # 未绑定（§12.1:557，不占 concept_id）：surface, technique_id, evidence, content_status, origin
rejected:                                # [{category, lane, item_index, disposition: refused|ruled_out, reason_code: 九码之一|null, detail}]
disputes:                                # [{dispute_id: m4_d001, category, key: [[span_id, start_offset, end_offset], ...], choice: a|b|both|neither}]
counts: {assertions, patterns, school_views, concept_mentions, new_concept_candidates, rejected, disputes, human_decisions}
```

**(2) `candidate_package`**：索引与血缘，含修订号。

```yaml
schema_version: 0.1.0-draft
candidate_set_revision_id: rev_…
candidate_set_sha256: <hex>
lane_set_revision_ids: {assertion/a: rev_…, assertion/b: rev_…, concept_mention/a: rev_…}
submission_revision_ids: {assertion/a: rev_…, …}
dispute_queue_revision_id: rev_…
human_event_revision_ids: [rev_…]
corpus_stage_package_revision_id: rev_…
spans_revision_id: rev_…
technique_profile_revision_id: rev_…
gate_profile: thin_no_model
span_layer: structural
cross_model: not_evaluated
term_layering: verify_only
```

**(3) m4 StagePackage**（过 `stage_package.schema.json`）

- `stage: m4`；`stage_package_id = ids.new_id("stage_package_id", stage="m4")`。
- `payload`：`candidate_set_revision_id, corpus_stage_package_revision_id, spans_revision_id, technique_profile_revision_id, gate_profile, span_layer, cross_model, term_layering, content_status_counts`。
- `manifest.input_artifacts`：M3 包用 `artifact_kind: stage_package`（携带 `stage_package_id`，§8.1:298），其余冻结输入用 `artifact_kind: artifact`；`output_artifacts: [candidate_package]`；`counts` 同 `candidate_set.counts`；`content_sha256 = sha256(candidate_set 字节)`。
- `validation: {passed: true, report_artifacts: [validation_report]}`；`lineage.upstream_artifacts: [M3 包, corpus_spans, technique_profile]`；`lineage.transformations: [extract_candidates]`；`logs: [step_log]`；`failures: []`。

### 6.4 人工事件形态

**(a) 类别裁决 `category_ruling`（§5 第 3 队列；本包 ACT 05 实现）**

```yaml
schema_version: 0.1.0-draft
event_kind: category_ruling
stage: m4
processing_run_id: prun_…
step_run_id: srun_…
dispute_id: m4_d001
choice: a                 # a / b / both / neither
rationale: B 路 relation=qualifies 与题记直述不符
actor_ref: local_owner
seen: {dispute_queue_revision_id: rev_…}
```

Ledger 路径：`put_artifact(step, "human_event", …)` → `seal_revision` → `record_human_event(step, token, rev, decision_type=None)`（D-14）→ 立即 `write_checkpoint`（§17.1:843）。全部裁决完成后 `resume_m4` 消费 token。

**(b) 专家审核决定 `review_decision`（形态由本包 ACT 06 冻结；StepRun 归属 M6，D-07；本包不建签发运行、不伪造签发，P7）**

```yaml
schema_version: 0.1.0-draft
event_kind: review_decision
stage: m6
decision_type: review_source_fidelity     # §8.2 八类之一；一事件一类
verdict: accept                           # accept / modify / reject / request_evidence / school_dispute（D-08）
target:
  entity_kind: assertion                  # assertion / pattern / school_view
  entity_id: as_qizheng_000001            # §8.1:265 主锚
  artifact_revision_id: rev_…             # 作决定时所见 candidate_set 修订
processing_run_id: prun_…
step_run_id: srun_…
actor_ref: local_owner
rationale: 逐字核对 page_001 题记与字框
evidence_refs: [ss_sanche_ed01_p0001_s02]
consumption_level: INTERNAL_DEMO
```

内容成熟度由 `derive_content_status` 按 D-08 推导，推导结果写进签发产物的新修订，不回写 `candidate_set`（已封存不可变）。真实签发需要用户撰写决定表（§9）。

### 6.5 Checkpoint 任务划分（§17.1:843）

- submit StepRun：task `submit_<category>_<lane>`，1 个。
- assemble StepRun：每路 `lane_<category>_<lane>`（按 category、lane 排序）→ `reconcile` → 每条裁决 1 个（task_id = dispute_id，`human_decisions` 累积全部已登记裁决事件）→ `assemble`。`pending_queue` 列出其后全部 task 与未裁决的 dispute_id，`next_pointer` 为首个待办或 None。
- 金标路径（附录 A）：submit 3 个；assemble 6 个（`lane_assertion_a`、`lane_assertion_b`、`lane_concept_mention_a`、`reconcile`、`m4_d001`、`assemble`）。

### 6.6 对下游的输出契约

**M5（impl-03，已验收；扩展只写接口需求，不改 impl-03）**

- 现状：M5 `scope: corpus_only`（G7-RULINGS §9 第 2 条），`resolve_m5_inputs` 只解析 m3 包及其血缘 17 个修订，不读 m4。
- 扩展需求（下一波由 M5 负责方实现）：新增解析 m4 StagePackage（`stage == "m4"`，`payload.candidate_set_revision_id`、`payload.spans_revision_id`）；对 `candidate_set` 逐条复核 G3（`source_span_id` 存在于 `spans_revision_id` 所指 spans、`start_offset/end_offset` 落在该 Span 区间、`quote` 复算一致、`quote_sha256` 复算一致、`support_type` 取值合法），并核对 `content_status ≤ needs_expert`、`span_layer == "structural"`、`cross_model == "not_evaluated"`、`rejected` 逐条可数。M5 不得修改 `candidate_set`（§13:580），只能产出 `ValidationPackage` 引用它。
- 消费约束（G7-RULINGS §9 第 21 条）：消费 m4/m5 包须同时满足所属 StepRun `succeeded`。

**M6（D-07）**

- 读 `candidate_set` + `ValidationPackage` + `CorpusPackage`；审核事件按 §6.4(b)；`derive_content_status` 可 import `pipeline.knowledge_extraction.review_events`，或由 M6 按同一契约重写。

**M8（impl-04，已验收；知识链前三段与 GraphProjectionPack 只写接口需求，不改 impl-04）**

- 首切片 M8 只闭合尾链四段（SourceSpan→SourceAnchor→OcrPage→SourceAsset），前三段标 `not_compiled`（impl-04 README §4 D1）。M4 落地后，M8 编译前三段需要的 M4 字段：
  - KnowledgeEntry：`subject_entity_id`（`co_*` / `pat_*`）、`title`（取自 `proposition` / `surface`）、`assertion_ids[]`、`school_view_ids[]`、`content_status`。
  - Assertion：`assertion_id`、`proposition`、`subject_entity_id`、`evidence[]`、`school_ids[]`、`content_status`。
  - EvidenceLink：`assertion_id`、`source_span_id`、`start_offset`、`end_offset`、`quote_sha256`（坐标语义见 §6.3 与 §10 N3）。
  - GraphProjectionPack：节点/边身份取自 M4 的 `as_` / `pr_` / `co_*` / `sv_` / `cg_` / `pat_` 与 `evidence` 关系；首切片 mini_ed01 上 M4 **没有** Pattern / SchoolView / ApplicabilityRule，也无 `expert_verified` 条目，故 GraphProjectionPack 仍不可编译（§20.9 维持 BLOCKED，§22.2:980 的 QizhengFactSet 匹配不可达）。
- `fixture_gold` 探针只能进入 `INTERNAL_DEMO`。

**M7**：首切片不消费。

**§20.6 / §20.7 与本包的关系**

- §20.6（Pattern 名称/规则/解释/出处可逐项补全、`not_captured` 不误判为不存在）：M4 产出 `patterns[].interpretation_status` / `recognition_rule_status = not_captured` 与 `content_status`，但 20.6 的判定要求 M8 编译出 KnowledgeEntry（`run_all.sh:257-262` 现为 `BLOCKED M8 Dataset Compilation`），故**本包不使 20.6 转判**；本包只保证不把 `not_captured` 误判为不存在（gate 检查 8、acceptance 的 `golden_match`）。
- §20.7（legacy 准入阈值）：与本包无直接关系（数据源是工作台 `ge_ju_database.sqlite`，非 M3 语料）。M4 薄接入**不得也不应**改变 20.7 的 FAIL（当前 496/0，`run_all.sh:242-270`）。可选 ACT 08 只以纯函数固化准入规则。
- 本包用于转判的是 §20.1/§20.4/§20.8/§20.9 的前置之一（G7-RULINGS §9.3 第 43 条：M4 最薄接入接入后由判据自动转判，需 M6/GraphProjectionPack 一并到位）。

### 6.7 配置修订内容

```yaml
# submit
{stage: m4, task: submit, category: assertion, lane: a, channel: fixture_gold, tool: pipeline.knowledge_extraction, tool_version: 0.1.0}
# assemble
{stage: m4, task: assemble, tool: pipeline.knowledge_extraction, tool_version: 0.1.0, gate_profile: thin_no_model,
 id_range: {assertion: [1, 99], proposition: [1, 99], pattern: [1, 99]},
 required_lanes: {assertion: [a, b], pattern: [a, b], school_view: [a, b], concept_mention: [a]},
 term_layering: verify_only}
```

`required_lanes` 只对出现了提交件的类别生效。

## 7. 执行分组与依赖

| 组 | ACT | 前置 |
|---|---|---|
| K1 | 00 提交件与任务管线 Adapter、01 纯函数装配、02 独立候选 Gate | 规格与 fixture `spans.yaml`（只读）；不依赖 impl-02 验收 |
| K2 | 03 Registry Adapter + 输入解析 + submit StepRun、04 assemble StepRun + CLI | K1 `ACCEPTED`；impl-02 `ACCEPTED`；D-04/05/09/10/13/15 |
| K3 | 05 类别裁决与恢复、06 审核决定事件契约 | K2 `ACCEPTED`；D-07/08/14 |
| K4 | 07 验收脚本 | K3 `ACCEPTED`；**fixture m4 金标独占 ACT 已落地**（D-02/P4）；D-11 |
| K5（可选） | 08 legacy 准入纯函数 | D-12 选 A 且主 Agent 决定要做 |

## 8. 目录（落地后）

```text
pipeline/knowledge_extraction/
  __init__.py            M4_TOOL / M4_TOOL_VERSION / CANDIDATE_SCHEMA_VERSION / 各闭集常量
  errors.py              ExtractionRefused
  serialize.py           canonical_json / sha256_hex
  submission.py          validate_submission（纯函数）
  assemble.py            page_blocks / span_index / locate_evidence / normalize_lane / reconcile_lanes / assemble_candidates（纯函数）
  gate.py                evaluate_candidates（纯函数，不依赖 assemble / submission）
  inputs.py              resolve_m3_outputs / resolve_m4_inputs（只读）
  submit.py              run_m4_submit（m4 submit StepRun）
  step.py                run_m4 / record_category_ruling / resume_m4（m4 assemble StepRun）
  review_events.py       build_review_decision / validate_review_decision / required_decision_types / derive_content_status（纯函数）
  acceptance.py          m4-stage-gate 十六项判定
  __main__.py            python -m pipeline.knowledge_extraction {profile|submit|assemble|rule|resume}
  adapters/
    __init__.py
    task_pipeline.py     normalize_task_output / export_task_inputs
    registry.py          build_technique_profile / register_technique_profile
    legacy_workbench.py  read_rules_readonly / admit_legacy_rules（ACT 08，可选）
  tests/
    data/appendix_a/     附录 A 四个 YAML 的逐字副本（测试数据）
    test_submission.py test_task_pipeline_adapter.py test_assemble.py test_gate.py
    test_registry.py test_submit.py test_step.py test_ruling.py test_review_events.py
    test_acceptance.py test_legacy_workbench.py
openspec/acceptance/m4-stage-gate.sh
```

## 9. 用户待办

1. **真实专家签发决定表（P7 / D-07 / D-08）**：本包只冻结 `review_decision` 形态与 `derive_content_status` 纯函数，不产生任何真实签发。任何需要真实 `expert_verified` 的条目，其决定表必须由用户本人撰写；在用户提供之前，依赖它的判定一律 **BLOCKED**，不得以测试替身或合成事件充数、不得写 `expert_verified`。
2. **fixture m4 金标独占 ACT（P4 / D-02）**：由主 Agent 落地 `pipeline/corpus/_fixture/mini_ed01/m4/` 四个金标、`expected/m4.stage_package.yaml`，并同步扩展 fixture `verify.sh` V5/V6 到 m4。该项属共享面独占 ACT，与 impl-05 实现分离；K4 以它落地为强制前置（见 §10 N2）。

## 10. 待主 Agent 裁决

以下问题无法由现有裁决与原则唯一推出，保留待裁。每条给选项、推荐与证据（文件:行号）。

### N1｜M4 artifact_type 登记与 INTERFACES §2.4 / §3.2 旧结构的对账

- 背景与证据：`INTERFACES.md` §4 M4 行仍列旧命名 `candidate_batch` / `model_run` / `candidate_diff_report` / `candidate_set` / `candidate_package`（状态「纵切后（D-11）」）；§2.4 M4 卡片的冻结输入/任务/输出/payload 与 §3.2 `candidate_set.schema.json`（含 `concepts[]`、`term_layers`、`extraction_mode`、`model_run_revision_ids[]`）均为 G7 薄接入**之前**的旧设计。本包实际使用 `candidate_submission` / `candidate_lane_set` / `dispute_queue` / `candidate_set` / `candidate_package`（**只提名**，P2）。`check_interfaces.py:REQUIRED_TYPES` 也未枚举任何 M4 类型。
- 选项：
  - A（推荐）：由该波登记 ACT（impl-00 侧）一次性把 §4 M4 行改写为本包提名清单、删除旧命名，并把 §2.4/§3.2 重写为 §6.3 的薄结构；同时把 M4 类型加入 `check_interfaces.py` 的 `REQUIRED_TYPES`，作为 impl-05 的开工前提（复刻 impl-04 的 `I00-IF SUMMARY` 前置）。
  - B：impl-05 改用 §4 旧命名（`candidate_batch` 等），不提名新名（与 D-04「每路一个 submit StepRun、输出 `candidate_submission`」的裁决冲突，不推荐）。
  - C：旧命名与新提名并存，先在 §4 增行、不删旧行（闭集出现两套同义名，违反 P2「单一闭集、同一时刻只有一路写」）。
- 推荐：A。

### N2｜K4 是否以 fixture m4 金标独占 ACT 为强制前置

- 背景与证据：`pipeline/corpus/_fixture/mini_ed01/` 目前无 `m4/`、`expected/m4.stage_package.yaml`；`verify.sh:333-400` 的 V5/V6 只覆盖 m1–m3。Q02 裁决为 A 且「金标进 fixture 须作为独占 ACT（P4）」。
- 选项：
  - A（推荐）：K4（ACT 07）以 fixture m4 金标 + `verify.sh` 扩展到 m4 的独占 ACT 先落地为强制前置；缺失即停手上报，执行者不得自建金标或改 fixture。
  - B：允许 ACT 07 以 `--gold-dir pipeline/knowledge_extraction/tests/data/appendix_a` 退避判定（削弱 §20:935「统一验收宿主」口径，不推荐）。
  - C：本批不建 `m4-stage-gate.sh`，只以单测验收（放弃 §19.0:908 判据，不推荐）。
- 推荐：A。

### N3｜候选证据的坐标键名与语义（与 INTERFACES §3.1 evidenceLink / §6 I-11 不一致）

- 背景与证据：本包 `candidate_set` 证据用 `start_offset` / `end_offset`，语义为**相对页块的绝对偏移**（`corpus_spans` 坐标系；附录 A 期望 `s02 [8,12]`、`s04 [27,32]` 皆页块绝对）。`INTERFACES.md` §3.1 `evidenceLink` 与 §6 I-11 定义为 `char_start` / `char_end`，语义为**相对所引 span `text`**；§3.10 `evidence_map_pack` 的 `evidence_link` 亦用 `char_start` / `char_end`，而 impl-04 已验收的 `evidence_map_pack` entry 又用 `start_offset` / `end_offset`（相对页块）。命名与语义在两处已互相矛盾。
- 选项：
  - A（推荐）：以 M3 `corpus_spans` 的页块绝对坐标为准，M4 统一用 `start_offset` / `end_offset`；由登记/契约 ACT 同步修改 INTERFACES §3.1、§6 I-11、§3.10，明确 `char_start/char_end` 为「相对 span 文本」的别名或删除之，并要求 M8 `evidence_link` 一并改写。
  - B：M4 改用 span 相对 `char_start` / `char_end`（与 INTERFACES 现状一致），页块绝对偏移由 M5/M8 以 `span.start_offset + char_start` 复算；需 M8 `evidence_map_pack` 与 impl-04 验收口径同步调整。
  - C：两个坐标系同时携带（`char_start/char_end` 相对 + `start_offset/end_offset` 绝对），冗余但无歧义；代价是候选体积与一致性检查翻倍。
- 推荐：A（单一坐标源，M8 尾链与社区锚点都用页块坐标；`quote`/`quote_sha256` 已足以独立复核）。

### N4｜`candidate_set` 的 `gate`/`validation` 结果是否落盘

- 背景与证据：G7-RULINGS §9.5 第 46 条修订第 34 条：**Stage Gate 报告**首纵切不落盘，由 `evaluate_stage_gate` 返回并打印。本包 ACT 04 把候选 Gate 结果写成**本 StepRun 内**的 `validation_report` 修订（复用已登记类型），可由公开读接口取回，与编排层 Stage Gate 报告不是同一对象。
- 选项：
  - A（推荐）：保留落盘为同 StepRun 的 `validation_report`（属于模块自检，非编排 Stage Gate 报告；可经公开读接口取回，不违反第 46 条）。
  - B：M4 候选 Gate 报告也不落盘，只由 `run_m4` 返回并打印（与 impl-04 的 `validation_report` 子包先例不一致，且 M5 无法从 Ledger 复核）。
- 推荐：A。

## 附录 A：fixture 金标提案（D-02 选 A 时由主 Agent 落地；测试数据副本放 `tests/data/appendix_a/`）

offset 已按 `spans.yaml` 实测核对：`ss_sanche_ed01_p0001_s02` 为 [5,12]「（宋）錢如璧撰」；`ss_sanche_ed01_p0001_s04` 为 [20,37]「三辰通載三十卷宋錢如璧撰據静嘉堂藏」；`ss_sanche_ed01_p0003_s12` 为 [67,72]「論身宮主星」；`ss_sanche_ed01_p0003_s19` 为 [118,122]「論官祿宮」。

`m4/submission_assertion_a.yaml`

```yaml
schema_version: 0.1.0-draft
category: assertion
lane: a
channel: fixture_gold
technique_id: qizheng
producer: {kind: fixture, name: mini_ed01, model_id: null, prompt_sha256: null, response_sha256: null}
source_task: null
items:
- proposition: 三辰通載三十卷
  relation: supports
  evidence:
  - {source_span_id: ss_sanche_ed01_p0001_s04, support_type: direct, span_char_start: 0, span_char_end: 7}
  layer: editorial
- proposition: 宋錢如璧撰
  relation: supports
  evidence:
  - {source_span_id: ss_sanche_ed01_p0001_s04, support_type: direct, span_char_start: 7, span_char_end: 12}
  - {source_span_id: ss_sanche_ed01_p0001_s02, support_type: direct, quote: 錢如璧撰}
  layer: editorial
```

`m4/submission_assertion_b.yaml`：`lane: b`；item 0 与 A 路 item 0 逐字相同；item 1 与 A 路 item 1 相同但 `relation: qualifies`；item 2 为 `{proposition: 錢如璧撰述, relation: supports, evidence: [{source_span_id: ss_sanche_ed01_p0001_s02, support_type: direct, quote: 錢如璧撰述}], layer: editorial}`（quote 在 Span 中不存在 → TXT_001）。

`m4/submission_concept_mention_a.yaml`：`category: concept_mention`、`lane: a`；items：`{surface: 身宮, evidence: [{source_span_id: ss_sanche_ed01_p0003_s12, support_type: direct, span_char_start: 1, span_char_end: 3}]}`、`{surface: 官祿宮, evidence: [{source_span_id: ss_sanche_ed01_p0003_s19, support_type: direct, span_char_start: 1, span_char_end: 4}]}`。

`m4/ruling_m4_d001.yaml`：`{schema_version: 0.1.0-draft, dispute_id: m4_d001, choice: a, rationale: B 路 relation=qualifies 与题记直述不符}`。

期望结果（`expected/m4.stage_package.yaml` 的 counts 与 payload 依此计算）：

- `assertions`：`as_qizheng_000001`「宋錢如璧撰」（证据 s02 [8,12]「錢如璧撰」、s04 [27,32]「宋錢如璧撰」）；`as_qizheng_000002`「三辰通載三十卷」（证据 s04 [20,27]）。排序键为 (首条证据 Span 序, 首条证据 start_offset, proposition, relation)，s02 在 s04 之前，故「宋錢如璧撰」取 000001。
- `new_concept_candidates`：「身宮」s12 [68,70]；「官祿宮」s19 [119,122]。
- `rejected`：1 条（assertion / b / item_index 2 / refused / TXT_001）。
- `disputes`：1 条 `m4_d001`（key `[[ss_sanche_ed01_p0001_s02,8,12],[ss_sanche_ed01_p0001_s04,27,32]]`，choice a）。
- `counts`：`{assertions: 2, patterns: 0, school_views: 0, concept_mentions: 0, new_concept_candidates: 2, rejected: 1, disputes: 1, human_decisions: 1}`。
- 声明：以上是结构探针，只证明「提交 → 证据定位 → 双路差异 → 人工裁决 → 候选封存」链路可校验，不是七政技法知识。
