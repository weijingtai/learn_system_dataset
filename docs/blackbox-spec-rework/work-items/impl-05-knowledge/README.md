# impl-05：M4 Knowledge Extraction（§12）最薄接入

状态：`DRAFT`（起草 Agent 产出；§4 共 16 项待主 Agent 裁决，裁决后方可改 `READY`；本目录不含 PROMPT 与 ACCEPTANCE）

## 1. 目标

在 `pipeline/knowledge_extraction/` 落地规格 §12 的 M4 **最薄接入**（§22.3 阶段 1：M4 属「首纵切后、薄用」）：

1. **不调用任何模型**。候选来自「现有任务管线形态」的产出——人或外部 Agent 按工位 5 格式写出的草稿（`run_task.py --model manual` 的上游），以及 fixture 金标；二者经 Adapter 规范化为「提交件」，每路（类别 × 路别）一个 m4 submit StepRun 登记为 Ledger 已封存修订。
2. M4 assemble StepRun 只读 Ledger 冻结修订：M3 StagePackage、`corpus_spans`、`technique_profile`（Contract Registry 快照）与全部提交件；确定性完成证据定位（页块 offset + quote + quote 哈希）、状态上限、类别分离、双路差异检出、人工闭集 ID 分配，输出 `candidate_set` 与 m4 StagePackage。
3. 双路不一致时进入 §5 的「M4 类别分歧」队列：`awaiting_human` → 类别裁决人工事件（每条即时 Checkpoint）→ `resume`。
4. 以独立实现的候选 Gate 判定输出契约；以独立实现的 `acceptance.py` 重算 13 项判定。
5. 冻结「专家审核决定」人工事件形态与内容成熟度推导纯函数（`review_events.py`），供 M6 签发复用；签发 StepRun 本身的归属待 D-07。

本批不做（报 BLOCKED 或推迟）：生产模型 A/B 与复核模型 C（§12.2:572）；SemanticSpan 输入（§12.2:561）；L1/L2/L3 自动扫描判层（§12.1）；`omen_carrying` / `condition_affordance` 等 Tag 字段（§16.3.2:801-815）；ApplicabilityRule 与条件 AST（§13 G6）；legacy 工作台候选导入进 run_all（§20.7，见 §5.3）；专家签发 StepRun（D-07）。

完成判据（本批唯一的「做完」定义；数字以 §4 全部采纳「推荐」为前提）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/knowledge_extraction/tests -t . 2>&1 | tail -1   # OK（用例 ≥ 118）
bash openspec/acceptance/m4-stage-gate.sh; echo exit=$?
# 期望：13 行 PASS + 3 行 BLOCKED（cross_model_extraction / semantic_span_input / term_layering_scan）
#       末行 SUMMARY pass=13 fail=0 blocked=3；exit=2
bash openspec/acceptance/run_all.sh | tail -1            # 与开工基线逐字相同（本批不改 run_all.sh；20.7 仍 FAIL）
bash openspec/acceptance/m3-coverage.sh; echo exit=$?    # 与开工基线相同（本批不得改变 M3 结果）
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
- §13:580（M5 不修改 Candidate）、§13:590-592（G3、G4）
- §14:618-627（M6 签发；M4 模式输出类别 ReviewDecision；Model Adapter 属 M4）
- §16.1:674-678（消费级别准入）、§16.3.2:801-815
- §17:836（事务序列）、§17.1:840-846（每 task 一个 Checkpoint；人工决定即时落盘）
- §19:878（M4 差距行）、§19:880（M6 行：496 rules、original_text 非空 0）、§19.0:908（`m4-stage-gate.sh`）、§19.1:929-931（units 与工作台库冻结）
- §20:935（BLOCKED 行名取 §19 第一列）、§20:937（20.1）、§20:943（20.7 准入阈值）
- §22.1:966-969、§22.2:977-980（M4 候选沿用现有任务管线，少量人工签发；QizhengFactSet 匹配）、§22.3:991、§22.4:999

其他：

- `openspec/id-prefix-registry.md` §3.1–§3.4（:54 七政首批流派「正式登记随 M4 首次抽取时冻结」）
- `openspec/legacy-storage-transition.md:26,28,52,54`（units 冻结、新 M4 从 CorpusPackage 生成；工作台库只能经独立 legacy_candidate 导入）
- `openspec/acceptance/run_all.sh:45-46,242-270`（20.7 判定逻辑）
- `openspec/schemas/stage_package.schema.json`、`artifact_ref.schema.json`（`artifact_kind: stage_package` 分支）、`step_request.schema.json`、`step_result.schema.json`
- `pipeline/ledger/service.py:66`（RUN_ARTIFACT_TYPES 只含 configuration / technique_profile）、`:253-262`（running / awaiting_human 可写）、`:442-463`（put_artifact）、`:528`（put_run_artifact）、`:718`（register_stage_package）、`:777-790`（record_transformation 含 `model_ref`）、`:885`（await_human）、`:922-963`（record_human_event，decision_type 只收八类或 None）、`:965`（resume）、`:1364`（write_checkpoint）
- `pipeline/ledger/states.py:57-66`（REVIEW_DECISION_TYPES）、`pipeline/ledger/ids.py:13-33`（19 个前缀家族；`new_id` 支持 school_view_id / conflict_group_id）
- `pipeline/ledger/fixture_ingest.py:40-47`（灌入 m3 时不写 corpus_spans）
- `pipeline/corpus_compiler/step.py:236-251,272-330,335`（run_m3 的 corpus_package、StagePackage payload.spans_revision_id、finish 输出）
- 任务管线（只读调研，见 §5）：`pipeline/HANDBOOK.md:41-54,89-96,249-261,263-304`、`pipeline/schemas/core/SCHEMA.md:44-76`、`pipeline/runner/run_task.py:89-135,143-178`、`pipeline/runner/config.yaml`、`pipeline/validators/compare_drafts.py:65-160`、`pipeline/validators/validate_assertion_task.py:40-90`、`pipeline/tools/gen_assertion_task.py`、`pipeline/tools/merge_assertions.py`、`pipeline/TASKGEN_HANDOFF.md:147-157`、`pipeline/task-templates/stage5_assertions*/INSTRUCTIONS.md`、`pipeline/schemas/shared/canon/*.yaml`、`pipeline/registry/schools/`
- `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二–§三；`knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §3.2–§3.3
- fixture `pipeline/corpus/_fixture/mini_ed01/`：`spans.yaml`（sha256 `ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef`）、`source/transcript_v1.md`（仅书名页与目录）、`README.md` §1（内容不作知识来源）
- `pattern_knowledge_workbench/assets/ge_ju_database.sqlite`（sqlite 实测 `ge_ju_rules` 496 行、`original_text` 非空 0；`ge_ju_schools` 中 `guo_lao` 类型为 book）

## 3. 范围

写：`pipeline/knowledge_extraction/**`（新建）、`openspec/acceptance/m4-stage-gate.sh`（ACT 07 新建，待 D-11）。

主 Agent 写（执行者不写）：附录 A 的 fixture 金标与 `expected/m4.stage_package.yaml`（待 D-02）。

禁止：

- 改 `openspec/acceptance/run_all.sh`、`m3-coverage.sh`、规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`；
- 改 `pipeline/TASKS/`、`task-templates/`、`runner/`、`tools/`、`validators/`、`units/`、`registry/`、`schemas/`、`pattern_knowledge_workbench/`；创建 `pipeline/tools/import_legacy_candidates.py`（D-12）；
- 改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、其他 work-items 目录；
- 新增依赖、新增 ID 前缀；调用模型 API，或 import `requests`/`openai`/`anthropic`/`httpx`；
- 生产代码读 fixture 路径或工作目录「最新文件」（例外只有 Adapter 入口：`adapters/registry.py` 读 canon 目录、`adapters/task_pipeline.py` 读调用方传入的草稿与模板、`adapters/legacy_workbench.py` 以只读方式打开工作台库；它们的产物必须先登记进 Ledger，M4 核心只读 Ledger）；
- 生产代码 import `pipeline/validators`、`pipeline/tools`、`pipeline/runner` 下的脚本（只作规则参照，按本包契约重写）；
- M4 产出任何对象的 `content_status` 高于 `needs_expert`（不得出现 `cross_model_reviewed`、`expert_verified`）；
- 执行者写台账、写 `ACCEPTED`。

## 4. 待主 Agent 裁决

每条给出选项、推荐与理由；「推荐」不是定案。ACT 契约按全部采纳推荐起草，任一条改选会影响的 ACT 在 `ACT.yaml` 的 `pending_decisions` 中列出。

### D-01 模型调用是否在首切片内

- 依据：§12.2:572-574；§22.4:999（M4 不入首纵切，10 页候选由现有任务管线产出）；§2:40；§14:627（模型调用属于 M4 Model Adapter）；`pipeline/runner/config.yaml`（production/reviewer 走外网 API，需密钥）。
- 选项：
  - A：首切片不调用模型。候选只经提交件 Adapter 登记，渠道闭集中只收 `fixture_gold`、`task_pipeline_manual`（后者承接人或外部 Agent 按工位 5 格式写出的草稿，记录 producer 名）；`model_adapter` 渠道拒收；验收 `cross_model_extraction` 恒 BLOCKED。
  - B：接入 Model Adapter，调 `config.yaml` 端点（结果不可重放、需密钥，违背本批「不调模型」纪律）。
  - C：以 `run_task.py --model mock` 形态登记「mock 模型」渠道并写 `model_ref`（形式上有模型留痕，实为金标，容易被误读为已接模型）。
- 推荐：A。确定性替代 = fixture 金标提交件注入（附录 A）。Ledger `record_transformation` 已有 `model_ref` 参数（service.py:787），日后接入 Model Adapter 只新增渠道，不改 M4 Interface（§20:946 第 10 条）。

### D-02 fixture 候选金标的来源与内容

- 依据：mini_ed01 只有书名页与目录（`source/transcript_v1.md`；fixture README §1 声明内容不作知识来源），**没有任何七政技法主张**；真实第 8 页才有赋文正文（`ocr/data_work/data/page_008.json` 84 行）；fixture 尚无 M4–M8 期望产物；§22.1:969。
- 选项：
  - A：主 Agent 在 fixture 增 `m4/` 目录（assertion 两路、concept_mention 一路、类别裁决一份）与 `expected/m4.stage_package.yaml`，由 `build_fixture.py` 可重放；内容为附录 A 的「书目题记探针」——从 page_001 题记逐字截取「三辰通載三十卷」「宋錢如璧撰」，`layer: editorial`，渠道 `fixture_gold`。注意 fixture `verify.sh` V5/V6 目前只覆盖 m1–m3，需同步扩展。
  - B：金标只放 `pipeline/knowledge_extraction/tests/data/`，验收脚本 `--gold-dir` 指向它（不进统一验收宿主，削弱 §20:935 的「统一宿主」口径）。
  - C：新建含 page_008 的第二 fixture，产出真实七政主张（改动大，且需先有 M3 对 page_008 的结构金标；若改 mini_ed01 本身会改变 impl-02 的 spans 金标）。
- 推荐：首切片 A，C 列入纵切后。理由：A 不动 M3 金标、字节可重放、探针渠道可被 M5/M8 识别。**如实声明**：mini_ed01 无法支撑 Pattern、SchoolView、ApplicabilityRule 与 QizhengFactSet 匹配（§22.2:980），这些链路只能在 C 或真实前十页上验证。

### D-03 M4 输入的 Span 层

- 依据：§12.2:561「M4 将 SemanticSpan 分别提取为候选」；§11:513-521；impl-02 README §4 第 1 条（M3 只做结构层，`gate_profile: structural_only`、`semantic: not_evaluated`）。
- 选项：
  - A：薄接入消费 StructuralSpan；candidate_set 与 m4 包写 `span_layer: structural`；验收 `semantic_span_input` 恒 BLOCKED（行名「M3 Corpus Compilation」）。
  - B：M4 整体等 M3 语义层落地后再做。
  - C：M4 自行做语义合段（侵占 M3 职责，§11:519）。
- 推荐：A。

### D-04 候选提交件如何登记为 Ledger 冻结修订（Adapter 形态）

- 依据：§7:207；§7.1:211（一阶段可有多个任务，每个任务一个 StepRun）；§12.2:572（A/B 初次不可见彼此）；`put_run_artifact` 只收 configuration / technique_profile（service.py:66）；`put_artifact` 必须挂在 running / awaiting_human 的 StepRun 上（service.py:253-262）。
- 选项：
  - A：每路（category × lane）一个 m4 submit StepRun：配置 `task: submit`，冻结输入仅 M3 包与 `corpus_spans`，输出 `candidate_submission`；assemble StepRun 再把全部提交件修订列为冻结输入。路间隔离由 Ledger 冻结输入集合证明。
  - B：单个 assemble StepRun 以字节参数接收提交件并在内部封存（提交件成了本步输出而非冻结输入）。
  - C：Ledger 新增运行级类型 `candidate_submission`（改 pipeline/ledger，出本批范围）。
- 推荐：A。

### D-05 Contract Registry 冻结输入（canon / homographs / 流派闭集）如何进入 Ledger

- 依据：§5:128、§12.1:540,547；`pipeline/schemas/shared/canon/` 现有 6 个闭集文件；`schemas/shared/homographs/` 与 `schemas/techniques/qizheng/glossary_v0.yaml` **均不存在**（techniques 下只有 bazi、qimen；`pipeline/registry/schools/` 也只有 bazi、qimen）；`id-prefix-registry.md:54`；service.py:66。
- 选项：
  - A：Registry Adapter 读 canon 目录，生成运行级 `technique_profile` 修订（含 canon 快照及文件哈希、`homographs: []`、`glossary: []`、`schools: []`），列为 assemble 冻结输入；流派闭集本批不冻结，任何 `school_id` 一律 REF_001 拒收。
  - B：同 A，但本批冻结 `sch_qizheng_001` 琴堂派、`sch_qizheng_002` 天官派（须用户确认登记）。
  - C：主 Agent 在 Ledger 新增运行级类型 `contract_registry_snapshot`（改 L1）。
- 推荐：A。不改 Ledger、不越权冻结流派；SchoolView 路径用单测合成 profile 覆盖。

### D-06 「L1 确定性字典匹配 100% 准确」与七政文本实测冲突

- 依据：§12.1:543；本起草实测：以 canon 全部字面对 mini_ed01 43 条 Span 做子串匹配，命中 6 次，**6 次全是误命中**——5 次是「三辰通載」的「辰」→`co_shared_branch_05`（三辰指日、月、星），1 次是「定胎元宮」的「胎」→`co_shared_changsheng_11`（胎元是七政宫位名，不是十二长生的「胎」）。
- 选项：
  - A：首切片「只校验不扫描」：提交件自带的 `co_shared_*` 引用必须存在于冻结 canon，字面 ∈ {surface, aliases}，且等于证据 quote；自动扫描报 BLOCKED `term_layering_scan`。
  - B：自动扫描，但命中只记 `needs_context`、不直接绑定（与 §12.1:543「直接命中并绑定」冲突）。
  - C：自动扫描 + 七政复合词停用表（需新登记冻结输入与维护流程）。
- 推荐：A；并建议主 Agent 把上述实测登记为 §12.1 的规格问题（单字闭集在复合词里并不零歧义）。

### D-07 「人工签发 expert_verified」归属 M4 还是 M6

- 依据：§22.3:991（M4 行：「候选由现有任务管线产出并人工签发少量 expert_verified 条目」；M6 行：「工作台只做只读对照与签发」）、§22.2:977；§14:618-624（M6 做专家签发，M4 模式只出类别 ReviewDecision）；§5:122-123（M4 类别分歧与 M6 待签发是两个队列）；§5:103-110、§6.1:141-146（M4→M5→M6）；§2:40。
- 选项：
  - A：签发 StepRun 归属 M6 薄接入工作包（在 M5 之后）；本包只冻结 `review_decision` 事件形态与 `derive_content_status` 纯函数（ACT 06）。
  - B：在 M4 assemble StepRun 内追加签发队列（签发早于 M5 校验，违背 §2:40 与阶段顺序）。
  - C：在本包宿主内临时写一个 stage=m6 的签发 StepRun（宿主与阶段错位，M6 落地时迁出）。
- 推荐：A；若本轮没有 M6 草案，退而取 C。

### D-08 expert_verified 需要哪些审核决定齐备，verdict 闭集是什么

- 依据：§8.2:337-364（禁止单一 expert_verified 覆盖全部含义，但没有定义「哪些决定齐备才能置 expert_verified」）；§14:618（接受、修改、驳回、补证、流派分歧、专家签发）；§16.1:678；§8.1:265。
- 选项：
  - A：首切片最小集：`review_source_fidelity` 必需；候选 `school_ids` 非空或对象是 SchoolView 时 `review_school_attribution` 也必需；verdict 闭集 `accept / modify / reject / request_evidence / school_dispute`；推导优先级：必需类型中有 `reject` → `deprecated`；有 `school_dispute` → `disputed`；有 `modify` 或 `request_evidence` → `needs_expert`；必需类型全部 `accept` → `expert_verified`；否则保持原状态。所见修订与当前候选修订不同的决定不计入（与 §14.1:640 内容变化需复核同口径）。
  - B：八类全部 `accept` 或显式 `not_applicable` 才可 `expert_verified`。
  - C：按消费级别设不同必需集合（INTERNAL_DEMO / DEV_SEARCH / PUBLIC_RELEASE）。
- 推荐：A（仅适用首切片 INTERNAL_DEMO；PUBLIC_RELEASE 前须由用户重定）。

### D-09 人工闭集 ID（as_ / pr_ / pat_）分配与重跑保号

- 依据：§8.1:257,267；§8.1:277-279,317；HANDBOOK:89-96（派发者写 id_range，禁止自挑号）；id-prefix-registry §3.4（pat_ 由 Contract Registry 登记）；Ledger 没有号段登记。
- 选项：
  - A：assemble 配置修订写 `id_range`（首切片 as / pr / pat 均为 1–99），同一 candidate_set 内查重（ID_002）；本批拒绝 M4 重跑（与 M3 相同），重跑保号推迟到重跑工作包。
  - B：Pattern 候选不分配 pat_（`pattern_id: null`，M7 聚合时分配），as_/pr_ 同 A。
  - C：新建号段登记冻结输入（新 artifact_type 与登记流程）。
- 推荐：A（首切片金标没有 Pattern，影响面小）。跨 Ledger 历史查重留给主 Agent 决定何时做。

### D-10 新 artifact_type 与 CandidatePackage 机器 Schema

- 依据：§8:232-251、§8.1:324-329；Ledger 只校验 artifact_type 形如 `^[a-z][a-z0-9_]*$`（service.py:458-463），没有登记表；`openspec/schemas/` 没有候选相关 Schema。
- 本包拟新增 artifact_type：`candidate_submission`、`candidate_lane_set`、`dispute_queue`、`candidate_set`、`candidate_package`；复用 `configuration`、`technique_profile`、`human_event`、`validation_report`、`step_log`、`failure_report`。
- 选项：
  - A：首切片用内部结构版本 `schema_version: "0.1.0-draft"`，由 `gate.py` 与 `acceptance.py` 各自独立校验；与 M5/M6 草案对账后，再由主 Agent 登记 `openspec/schemas/candidate_set.schema.json`。
  - B：本批先由主 Agent 新增 L0 Schema 并纳入 `openspec/schemas/verify.sh`。
  - C：不设独立制品，全部塞进 StagePackage payload（payload 过大，M5 需逐条引用）。
- 推荐：A；artifact_type 清单请主 Agent 与 M5/M6/M8 草案对账后冻结。

### D-11 是否在本批新建 §19.0 判据脚本

- 依据：§19.0:908；impl-02 先例（`m3-coverage.sh` 返回 2）。
- 选项：A 新建 `openspec/acceptance/m4-stage-gate.sh`（13 PASS + 3 BLOCKED，exit 2）；B 不建脚本，只以单测验收；C 建脚本但把三项 BLOCKED 折成一行。
- 推荐：A。BLOCKED 行名逐字取 §19 第一列：「M4 Knowledge Extraction」「M3 Corpus Compilation」「Contract Registry」。

### D-12 §20.7 legacy 候选与 M4 的关系

- 依据：§20:943；`run_all.sh:242-270`（先查 `original_text` 非空条数，为 0 即 FAIL；非 0 时只检查 `pipeline/tools/import_legacy_candidates.py` **是否存在**即 PASS）；sqlite 实测 496/0；`legacy-storage-transition.md:28,54`。
- 选项：
  - A：首切片不接 run_all，不在 `pipeline/tools/` 建该文件；可选 ACT 08 在本包宿主内写 fail-closed 纯函数 `admit_legacy_rules`（实库 496 条全部以 SCH_001 拒收），只作准入规则的可执行说明。
  - B：本批在 `pipeline/tools/import_legacy_candidates.py` 实现导入（数据不变时 20.7 仍 FAIL；一旦数据出现非空 original_text，存在性判据会让一个未经验证的工具直接 PASS）。
  - C：主 Agent 先把 20.7 判据改为「执行导入工具并核对准入/拒收计数」，再派 B。
- 推荐：A，并建议主 Agent 评估 C（当前存在性判据偏弱）。M4 薄接入**不能也不应**改变 20.7 的 FAIL。

### D-13 被拒候选是否阻断 M4 Gate

- 依据：§6.1:149（失败为零）；§12.2:572（只明确未解决语义分歧不能过 Gate）；HANDBOOK:60-66（一级容错由生产者自修）。
- 选项：A 被拒条目逐条写入 `rejected`（原因码取 §8.2:368-380 九码），不阻断 Gate，计数进 m4 包、由 M5 报告；B 任一条被拒即 StepRun failed；C 由配置设阈值。
- 推荐：A（拒收是准入结果不是加工失败，与 §20.7「fail-closed 拒绝」同口径）。提交件整体形状错误仍在 begin 之前拒绝。

### D-14 M4 类别裁决人工事件的 decision_type

- 依据：`record_human_event(..., decision_type=None)` 只收 §8.2 八类或 None（service.py:922-930，states.py:57-66）；§14:623（M4 模式输出「类别 ReviewDecision」），八类中没有「类别」。
- 选项：A `decision_type=None`，事件内容写 `event_kind: category_ruling`；B 映射成 `review_source_fidelity`（语义不符）；C 主 Agent 在 §8.2 增类型（L0 变更，需用户确认）。
- 推荐：A。

### D-15 M4 如何定位 M3 产出（与 impl-02 的接口）

- 依据：`fixture_ingest.py:40-47`（灌入 m3 时只写 corpus_package / corpus_batch，没有 corpus_spans）；`corpus_compiler/step.py:236-251,272-330,335`。
- 选项：
  - A：只认「succeeded 且 Transformation `compile_corpus` 的输出恰含 1 个 `corpus_package`、1 个 `corpus_spans`」的 m3 StepRun；0 个或多于 1 个即拒绝；测试脚手架 = `ingest(stages=("m1","m2"))` → `run_m3` → M4。
  - B：扩展 fixture_ingest 让 m3 也写 corpus_spans（改 pipeline/ledger，出范围）。
  - C：允许读 fixture `spans.yaml`（违背只读冻结修订）。
- 推荐：A；K2 起依赖 impl-02 `ACCEPTED`（含返工 ACT 05）。

### D-16 七政任务包模板与术语表

- 依据：`TASKGEN_HANDOFF.md:147-157`（stage4/5「通用版」实为奇门早期分叉）；`gen_assertion_task.py`（instruction_version 写死 `assertions_bazi_v0.1`，id_range 写死 `as_bazi`）；没有 qizheng glossary。
- 选项：A 本包 `export_task_inputs` 只导出输入（segments/spans 取自 Ledger `corpus_spans`），INSTRUCTIONS 由调用方指定模板路径（默认通用 `stage5_assertions`），task.yaml 记录 `instruction_version` 与 `id_range`；B 主 Agent 先写 `stage5_assertions_qizheng` 模板再派；C 首切片不做导出，只做导入。
- 推荐：A（导出只是便利，不进验收判据）。

## 5. 调研结论：现有任务管线能给 M4 薄接入什么

### 5.1 逐目录结论

| 路径 | 现状 | 在 M4 薄接入中的用法 | 结论 |
|---|---|---|---|
| `pipeline/TASKS/` | bazi/qimen 工位 3–6 任务包；`output/` 下有 `draft_*`、`authoritative`、`merged_final`、`merge_review`、`review_compare` | 只作格式与流程参照。其 `source_span_id` 指向旧 corpus，不是 Ledger 中 M3 编译的 Span，直接登记会全部 REF_001 拒收 | 不作首切片数据源 |
| `pipeline/task-templates/stage5_assertions(_bazi)` | 工位 5 INSTRUCTIONS | `export_task_inputs` 复制模板（D-16） | 可复用 |
| `pipeline/runner/run_task.py` | 组 prompt；`production`/`reviewer` 走 API，`mock`、`manual` 归档；`output/<by>_<ts>/{response,prompt,run}.yaml` | `manual` 模式是渠道 `task_pipeline_manual` 的上游；`run.yaml` 的 model、model_id、prompt_sha256、response_sha256 映射到提交件 `producer` 与 Transformation `model_ref`；API 模式不入首切片 | 形态复用，不 import |
| `pipeline/units/` | 139 单元、1331 条主张，冻结为历史快照（transition:26） | transition:52 明确「新 M4 从 CorpusPackage 生成」 | 排除 |
| `pipeline/validators/` | `compare_drafts.py` 按证据 span 集合对齐双路；`validate_assertion_task.py` AST_002 状态越权；`validate.py` TXT_001/SEM_001/REF_001 | 规则参照，在 `assemble.py`/`gate.py` 中按本包契约重写 | 规则复用 |
| `pipeline/tools/` | `gen_assertion_task.py` + `lib/taskgen.py` 生成任务包；`merge_assertions.py`「A 主干、B 查漏」 | 导出参照；合并策略不采用——M4 以人工类别裁决代替自动并入（§12.2:572「按证据比较，不采用多数票」） | 参照 |
| `pipeline/registry/` | techniques / works / schools 登记 | schools 无七政；首切片不读（D-05） | 暂不用 |
| `pipeline/HANDBOOK.md` | 工位 4/5 输出格式、三级容错、id_range | 提交件 item 字段沿用 SCHEMA.md §4（`concept_ids` 更名为 `concept_refs`；`assertion_id`/`proposition_id` 由 M4 重新分配） | 格式复用 |
| `pipeline/TASKGEN_HANDOFF.md` | taskgen 平台化交接 | 七政模板缺失（D-16） | 参照 |

### 5.2 Adapter 链路

```text
人 / 外部 Agent（未来：Model Adapter）
  └ 按工位 5 格式写草稿（可经 run_task.py --model manual 归档）
      └ adapters/task_pipeline.normalize_task_output → 提交件（单一类别）
          └ submit.run_m4_submit → m4 submit StepRun（冻结 M3 包 + corpus_spans）→ candidate_submission（sealed）
fixture 金标（D-02）───────────────────────────────┘
canon 目录 → adapters/registry.register_technique_profile → technique_profile（运行级 sealed）

step.run_m4（m4 assemble StepRun；冻结 M3 包、corpus_package、corpus_spans、technique_profile、全部提交件）
  → 每路 candidate_lane_set（Checkpoint）→ dispute_queue（Checkpoint）
  → [有分歧] await_human → record_category_ruling（每条一个 Checkpoint）→ resume_m4
  → candidate_set（Checkpoint）→ gate.evaluate_candidates → candidate_package → m4 StagePackage → finish
```

### 5.3 §20.7 与 M4 的关系

- 20.7 考的是「当前七政格局数据能否作为官方 Candidate 输入」，数据源是工作台 `ge_ju_database.sqlite`，不是 M3 语料。`run_all.sh:242-270` 先数 `original_text` 非空条数：现为 0/496，直接 FAIL，根本走不到工具存在性检查。
- 因此 M4 薄接入无论做到什么程度，20.7 都保持 FAIL；这是规格明确要求的「不得因可作为输入的字面而判通过」（§20:943）。
- 20.7 的准入规则（`original_text` 非空且来源引用可解析，否则 fail-closed）与本包对提交件的证据规则同口径：legacy 条目可以作为渠道 `legacy_workbench` 的提交件来源，但首切片拒收该渠道，只在可选 ACT 08 用纯函数固化准入规则。
- 风险提示（D-12）：20.7 在数据非空后只查文件是否存在，判据偏弱。

## 6. 契约

### 6.1 上游输入契约

**M3（impl-02）**

- m3 StepRun `status == "succeeded"`；其 Transformation `operation == "compile_corpus"` 的输出恰含 1 个 `corpus_package`、1 个 `corpus_spans`（D-15）。
- m3 StagePackage（`stage_packages` 表只读 SELECT 定位，列名以 `pipeline/ledger/store.py` 建表语句为准）内容 JSON：`payload.spans_revision_id` 等于上面的 corpus_spans 修订；`payload.gate_profile == "structural_only"`；`manifest.content_sha256 == sha256(corpus_spans 字节)`。
- `corpus_spans` 字节为 YAML。顶层键：`work, source_id, edition_part_artifact_id, evidence_level, content_status, span_count, batch_count, spans`。Span 键：`span_id, batch_id, page, line_index, start_offset, end_offset, text, source_anchor`。offset 相对页块（同页 Span 文本以 `"\n"` 连接），`block[start:end] == text`。
- M4 继承 `evidence_level`（mini_ed01 为 `glyphbox_level`），不得提升。

**Contract Registry（D-05，运行级 `technique_profile`，canonical JSON）**

```yaml
schema_version: 0.1.0-draft
technique_id: qizheng
canon:
  files: [{name: bagua.yaml, sha256: <hex>}, ...]          # 按文件名排序
  concepts: [{concept_id: co_shared_stem_01, surface: 甲, aliases: [], domain: stem, rev: 1}, ...]   # 按 concept_id 排序
homographs: []     # 首切片为空（目录不存在）
glossary: []       # 首切片为空（qizheng 术语表不存在）
schools: []        # 首切片为空（流派闭集未冻结）
```

**Ledger（impl-01，不改其行为）**：`put_run_artifact`、`begin_step_run`、`put_artifact`、`seal_revision`、`write_checkpoint`、`await_human`、`record_human_event`、`resume`、`record_transformation`、`register_stage_package`、`finish_step_run`、`fail_step_run`；读：`get_revision`、`get_step_run`、`list_step_run_events`、`list_transformations`、`list_checkpoints`、`read_object`；允许经 `reader.store.conn` 执行只读 SELECT（artifact_type、stage_packages、frozen_inputs、human_events、processing_runs）。

### 6.2 提交件 `candidate_submission`（canonical JSON；一件一类，§12.2:572）

```yaml
schema_version: 0.1.0-draft
category: assertion          # 闭集 assertion / pattern / school_view / concept_mention
lane: a                      # 闭集 a / b / c；首切片拒收 c（复核路预留）
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
- `relation ∈ {supports, qualifies, opposes, corresponds, equivalent}`（SCHEMA.md §4）；`layer ∈ {main, commentary, editorial, case}`，缺省 `main`；`status ∈ {null, machine_extracted}`，其他值整件拒收（与 AST_002 同口径）。
- `subject = {kind: assertion|pattern, key: <proposition 或 pattern name>}`。

### 6.3 CandidatePackage 结构草案（三层）

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
  evidence:                              # 按 (Span 序, start, end) 排序
  - {source_span_id: ss_sanche_ed01_p0001_s02, support_type: direct, start_offset: 8, end_offset: 12, quote: 錢如璧撰, quote_sha256: <hex>}
  - {source_span_id: ss_sanche_ed01_p0001_s04, support_type: direct, start_offset: 27, end_offset: 32, quote: 宋錢如璧撰, quote_sha256: <hex>}
  conditions: []
  exceptions: []
  concept_refs: []
  school_ids: []
  layer: editorial
  content_status: machine_extracted      # M4 上限：machine_extracted / disputed / needs_expert
  origin: {lane: a, item_index: 1}
patterns:                                # 字段：pattern_id, name, assertion_ids, evidence, interpretation, interpretation_status(not_captured|captured), recognition_rule_status(not_captured), content_status, origin
school_views:                            # 字段（§12.2:570）：school_view_id(sv_), school_id(sch_), subject_entity_id, claim_refs, conflict_group_id(cg_|null), changes_current_judgment, source_refs[{source_id, source_span_id}], evidence, content_status, origin
concept_mentions:                        # 已绑定：surface, concept_ref, evidence, content_status, origin
new_concept_candidates:                  # 未绑定（§12.1:557，不占 concept_id）：surface, technique_id, evidence, content_status, origin
rejected:                                # [{category, lane, item_index, disposition: refused|ruled_out, reason_code: 九码之一|null, detail}]
disputes:                                # [{dispute_id: m4_d001, category, key: [[span_id, start, end], ...], choice: a|b|both|neither}]
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
- `manifest.input_artifacts`：M3 包用 `artifact_kind: stage_package`（携带 `stage_package_id`，§8.1:298），其余冻结输入用 `artifact_kind: artifact`；`output_artifacts: [candidate_package]`；`counts` 同 candidate_set.counts；`content_sha256 = sha256(candidate_set 字节)`。
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

**(b) 专家审核决定 `review_decision`（形态由本包 ACT 06 冻结；StepRun 归属待 D-07）**

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

Ledger 路径（签发 StepRun 内）：`await_human(step, [签发队列修订])` → 每条 `put_artifact("human_event")` → `seal` → `record_human_event(..., decision_type=<同值>)` → `write_checkpoint` → 全部完成后 `resume`。内容成熟度由 `derive_content_status` 按 D-08 推导，推导结果写进签发产物的新修订，不回写 candidate_set（已封存不可变）。

### 6.5 Checkpoint 任务划分（§17.1:843）

- submit StepRun：task `submit_<category>_<lane>`，1 个。
- assemble StepRun：每路 `lane_<category>_<lane>`（按 category、lane 排序）→ `reconcile` → 每条裁决 1 个（task_id = dispute_id，`human_decisions` 累积全部已登记裁决事件）→ `assemble`。`pending_queue` 列出其后全部 task 与未裁决的 dispute_id，`next_pointer` 为首个待办或 None。
- 金标路径（附录 A）：submit 3 个；assemble 6 个（`lane_assertion_a`、`lane_assertion_b`、`lane_concept_mention_a`、`reconcile`、`m4_d001`、`assemble`）。

### 6.6 对下游的输出契约

**M5（impl-03）**

- 入口：m4 StagePackage（`stage == "m4"`，stage_packages 表定位）→ `payload.candidate_set_revision_id`、`payload.spans_revision_id`。
- 每个证据条目提供 `source_span_id, start_offset, end_offset, quote, quote_sha256, support_type`；M5 可对 `spans_revision_id` 独立复核 G3（引用、逐字、证据范围）。
- M4 保证：content_status ≤ `needs_expert`；`span_layer: structural`；`cross_model: not_evaluated`；`source_channels` 可识别 `fixture_gold` 探针；被拒条目在 `rejected` 中逐条可数。
- M5 不得修改 candidate_set（§13:580），只能产出 ValidationPackage 引用它。

**M6（D-07）**

- 读 candidate_set + ValidationPackage + CorpusPackage；审核事件按 6.4(b)；`derive_content_status` 可 import `pipeline.knowledge_extraction.review_events`，或由 M6 按同一契约重写。

**M8（impl-04）**

- 首切片 mini_ed01 上 M4 **没有** Pattern、SchoolView、ApplicabilityRule，也没有 `expert_verified` 条目（除非 M6 签发）；M8 草案不得假设从 M4 拿到可做 QizhengFactSet 匹配的规则（§22.2:980），PUBLIC_RELEASE 在首切片不可达（§16.1:678）。
- `fixture_gold` 探针只能进入 INTERNAL_DEMO。

**M7**：首切片不消费。

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
| K1 | 00 提交件与任务管线 Adapter、01 纯函数装配、02 独立候选 Gate | 规格与 fixture spans.yaml（只读）；不依赖 impl-02 验收 |
| K2 | 03 Registry Adapter + 输入解析 + submit StepRun、04 assemble StepRun + CLI | K1 ACCEPTED；impl-02 ACCEPTED；D-04/05/09/10/13/15 |
| K3 | 05 类别裁决与恢复、06 审核决定事件契约 | K2 ACCEPTED；D-07/08/14 |
| K4 | 07 验收脚本 | K3 ACCEPTED；D-02 金标已由主 Agent 落地；D-11 |
| K5（可选） | 08 legacy 准入纯函数 | D-12 选 A 且主 Agent 决定要做 |

## 8. 目录（落地后）

```text
pipeline/knowledge_extraction/
  __init__.py            M4_TOOL / M4_TOOL_VERSION / CANDIDATE_SCHEMA_VERSION / 各闭集常量
  errors.py              ExtractionRefused
  serialize.py           canonical_json / sha256_hex
  submission.py          validate_submission（纯函数）
  assemble.py            page_blocks / locate_evidence / normalize_lane / reconcile_lanes / assemble_candidates（纯函数）
  gate.py                evaluate_candidates（纯函数，不依赖 assemble / submission）
  inputs.py              resolve_m3_outputs / resolve_m4_inputs（只读）
  submit.py              run_m4_submit（m4 submit StepRun）
  step.py                run_m4 / record_category_ruling / resume_m4（m4 assemble StepRun）
  review_events.py       build_review_decision / validate_review_decision / derive_content_status（纯函数）
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

- `assertions`：`as_qizheng_000001`「宋錢如璧撰」（证据 s02 [8,12]「錢如璧撰」、s04 [27,32]「宋錢如璧撰」）；`as_qizheng_000002`「三辰通載三十卷」（证据 s04 [20,27]）。排序键为 (首条证据 Span 序, 首条证据 start, proposition, relation)，s02 在 s04 之前，故「宋錢如璧撰」取 000001。
- `new_concept_candidates`：「身宮」s12 [68,70]；「官祿宮」s19 [119,122]。
- `rejected`：1 条（assertion / b / item_index 2 / refused / TXT_001）。
- `disputes`：1 条 `m4_d001`（key `[[ss_sanche_ed01_p0001_s02,8,12],[ss_sanche_ed01_p0001_s04,27,32]]`，choice a）。
- `counts`：`{assertions: 2, patterns: 0, school_views: 0, concept_mentions: 0, new_concept_candidates: 2, rejected: 1, disputes: 1, human_decisions: 1}`。
- 声明：以上是结构探针，只证明「提交 → 证据定位 → 双路差异 → 人工裁决 → 候选封存」链路可校验，不是七政技法知识。
