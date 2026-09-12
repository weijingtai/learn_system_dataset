# impl-00：跨模块接口总表与金标 fixture 规划（M1–M8 对账基准）

状态：`DRAFT`（起草 Agent 产出；§4 共 17 条待主 Agent 裁决；裁决前不得派发任何 ACT；ACT 按各条「推荐」项撰写，主 Agent 取其他选项时须先改 ACT）

## 1. 目标

为并行实现 M1–M8 冻结一份**可机器验证**的跨模块契约，分三层：

1. **接口总表**（`INTERFACES.md`）：逐阶段列出冻结输入、输出 `artifact_type`、StagePackage `payload`/`counts`/`content_sha256` 规则、Checkpoint 粒度、Gate 与 G1–G7 归属、人工队列、下游实际消费键；m1–m3 以现有代码与 fixture 的**实际形状**为准，m4–m8 为草案并标明规格未定义处。
2. **新增 JSON Schema**（`openspec/schemas/` 下 12 份内容 Schema + 5 份阶段 payload Schema，字段草案见 `INTERFACES.md` §3）。
3. **金标 fixture**（`FIXTURE-PLAN.md`）：由 fixture 生成器确定性产出 `mini_ed01/expected/` 的 m4–m8 期望产物，扩展 `verify.sh` 判定项，以 `expected/SHA256SUMS` 冻结金标；给出 §19.0 判据脚本判定项草案与并行派发批次。

完成判据（全部 ACT 落地后；本包唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
W=docs/blackbox-spec-rework/work-items/impl-00-interfaces
.venv/bin/python $W/check_i00.py --upto 09; echo exit=$?
# 期望：C00–C09 每行 PASS，末行 `I00 SUMMARY pass=10 fail=0 skip=0`，exit=0
bash openspec/schemas/verify.sh >/dev/null; echo $?                   # 0
bash pipeline/corpus/_fixture/mini_ed01/verify.sh | tail -1           # FIXTURE OK（检查项由 8 增至 12，本机有页图）
bash $W/fixture_mutations.sh | tail -1                                # MUTATIONS 20/20
bash openspec/acceptance/run_all.sh | tail -1                         # 仍为 SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo exit=$?      # 仍为 exit=2
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/{manifest.yaml,spans.yaml,expected/m1.stage_package.yaml,expected/m2.stage_package.yaml,expected/m3.stage_package.yaml}
# 与 TDD.md §0 五个基线哈希逐字相同（m1–m3 金标一个字节都不许动）
```

本包**不会**让 `run_all.sh` 任何条目由 BLOCKED 变 PASS：金标是期望，不是实现；§20 各条仍须等对应模块落地。

## 2. 依据（只读来源，行号基于当前文件）

- 规格 `openspec/learn-system-blackbox-architecture.md`：§5 总体组织与五个专用队列 96–130；§6.1 EditionRun 包链 136–151；§6.2 ReleaseRun 153–175；§7 Module Interface 177–207、§7.1 209–226；§8 信封 228–251；§8.1 标识 253–329（新对象 290–306，3b 308–322）；§8.2 状态/审核类型/错误码 331–440；§9 M1 442–457；§10 M2 459–494；§11 M3 496–528；§12 M4 530–574；§13 M5 576–612（G1–G7 工位 584–604，ValidationPackage 606，fail-closed 608）；§14 M6 614–645；§15 M7 647–655；§16 M8 657–815（冻结输入 661–668，子包 680–699，EvidenceMapPack 703–715，SourceAssetPack 717–723，AnchorContractPack 727–734，16.3 Tag 字段 782–815）；§17 事务 836、§17.1 Checkpoint 838–846；§19.0 判据脚本 899–918；§20 933–947；§22 首纵切 958–1001（22.2 终点 971–984，22.3 分期 986–993）。
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §3 消费级别 38–46、§4 G1–G7 48–99、§6 行为场景 113–124。
- `pipeline/schemas/core/SCHEMA.md` §2 provenance 21–30、§4 assertions 44–66。
- `openspec/id-prefix-registry.md` §3.1–§3.4 20–63、§4 新增前缀流程 91–97。
- `openspec/schemas/`：`stage_package.schema.json`（payload 仅 `type: object` 22–24；counts 59–65）、`artifact_ref.schema.json`（artifact_type 仅正则 26–29）、`step_request/step_result.schema.json`、`verify.sh`。
- `pipeline/ledger/`：`fixture_ingest.py`（STAGES 40、STAGE_OUTPUT_TYPES 43–47、任务清单 167–214、Checkpoint 217–252、ingest 255–412）；`service.py`（RUN_ARTIFACT_TYPES 66、create_processing_run 319–345、register_stage_package 718、human_event 类型约束 824、record_human_event 922–930、write_checkpoint 1364–1377）；`store.py`（processing_runs 78–86、human_events 160–166、stage_checkpoints 168–180）；`ids.py` PATTERNS 14–34。
- `pipeline/corpus_compiler/step.py`（m3 实际 artifact_type：87/159/182/200/215/227/247/373）；`work-items/impl-02-corpus/act/01.yaml` R1–R8、`act/03.yaml` 17–65、`act/04.yaml` 19–20。
- `pipeline/corpus/_fixture/mini_ed01/`：`manifest.yaml`、`spans.yaml`、`expected/m1..m3`、`verify.sh`（ID_RULES 153–174、V5 334–352、V6 354–400）、`tools/build_fixture.py`（dump_yaml 117–125、build_expected 333–427、VERIFY_SH 模板 520 起）、`source/transcript_v1.md`。
- `ocr/data_work/data/page_001..010.json` 与 `ocr/data_work/logs/anomalies.jsonl`（page_010 `irregular_layout`）；`docs/blackbox-spec-rework/SUBAGENT_TODO.md` 599–600（impl-03 M5、impl-04 M8 为 BACKLOG）。

基线实测（2026-09-11，本机）：`verify.sh` 8 项 PASS、`FIXTURE OK`；生成器重放 `diff -r` 无输出；`m3-coverage.sh` `SUMMARY pass=8 fail=0 blocked=1`。

## 3. 范围

**本起草轮**只写本目录：`README.md`、`INTERFACES.md`、`FIXTURE-PLAN.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/00–09.yaml`。

**ACT 执行时写**（高风险：改 Schema 与 fixture；逐 ACT 的 `scope.write` 为准）：

- 本目录：`check_i00.py`、`tests/test_check_i00.py`、`fixture_mutations.sh`；
- `openspec/schemas/`：新增 `contract_common`、`candidate_set`、`gate_results`、`review_decision`、`reviewed_edition`、`rework_impact_report`、`canonical_snapshot`、`release_manifest`、`knowledge_data_pack`、`evidence_map_pack`、`source_asset_pack`、`anchor_contract_pack`、`query_contract_pack`、`stage_payload_m4..m8`（均为 `*.schema.json`）；`examples/` 新增样例；`verify.sh` **只追加**；
- `pipeline/corpus/_fixture/mini_ed01/`：`tools/build_fixture.py`、由它重新生成的 `verify.sh`、新增 `expected/` 文件与 `expected/SHA256SUMS`、人工维护的 `README.md`；
- `pipeline/ledger/fixture_ingest.py`、`pipeline/ledger/tests/test_ingest.py`（仅 ACT 09，视 D-13）。

**禁止**：改规格正文与 `id-prefix-registry.md`（新前缀须用户确认后另立工作包）；改四份 L0 Schema（`artifact_ref`/`stage_package`/`step_request`/`step_result`，除非 D-05 取 B）；改 `manifest.yaml`、`spans.yaml`、`anomalies.yaml`、`pages/`、`source/`、`expected/m1..m3` 的任何字节；改 `run_all.sh`、`m3-coverage.sh`、`pipeline/corpus_compiler/**`、`pipeline/ledger/` 中 ACT 09 以外的文件；新增依赖；调用模型 API；在 fixture 放任何图像；执行者写台账或 ACCEPTED。

## 4. 待主 Agent 裁决

每条给 2–3 个选项；「推荐」仅为起草意见，不是定案。

对账（与 impl-03 §4 去重，同一问题只需一次裁决，两边取同一选项）：D-02↔impl-03 D-01/D-07；D-08↔impl-03 D-11；D-09↔impl-03 D-04/D-05/D-08/D-12；D-10↔impl-03 D-09；D-12↔impl-03 D-02；D-13↔impl-03 D-13/D-14；D-17↔impl-03 D-10；I-13↔impl-03 D-15。

### D-01 fixture 内容无法承载知识抽取，§22.2 的 FactSet 匹配在前十页无宿主

事实：mini_ed01 只有 page_001（书名页 4 行）、page_002（无文字）、page_003（目录 39 行）。本机 OCR 与页图只到 page_010，其中 page_004–009 仍为目录（如 page_004 首行「卷第二 / 天福星 / 定十變星例」），page_010 为 `irregular_layout` 盘面页（anomalies.jsonl 第 2 条）。规格 §22.2 980 要求「QizhengFactSet 确定性匹配至少一条 Pattern 的全部适用主张」、§22.3 991 要求在 mini fixture 与真实前十页各跑通一次——两者均没有可抽规则的正文。

- A（推荐）：不扩页。m4 金标只取**目录型直接主张**（如「《三辰通載》目錄列有「論官祿宮」一目」，证据为 `ss_sanche_ed01_p0003_s19` 整行）与 2 个 L3 Concept 候选；M8 以 Concept 为 KnowledgeEntry 主体，打通 §16 705–713 七段证据链；G4/G6 与 FactSet 匹配在 mini_ed01 上标 BLOCKED。理由：零伪造、内容可逐字核对、足以验证链路与门禁。
- B：扩 fixture 到 page_010（多 7 页 OCR JSON，约 1.5MB），page_010 需新增终态。收益低：新页仍无规则内容，却改动 m1–m3 全部金标哈希。
- C：另立正文页 fixture（卷一正文，page_011 之后）。需先补页图与 OCR（属 M2），阻塞 m4–m8 金标。
- 附带需用户裁定：§22.2 980 / §22.3 991 的「真实前十页」页范围是否改为「首个含规则正文的 EditionPart」。

### D-02 M5 的冻结输入未定义

§13 576–612 未列输入；§6.1 142–145 暗示只接 CandidatePackage，但 G1/G2/G3（588–590）要核对页哈希、覆盖与字框，§7 207 又禁止读取未冻结的上游。G3 的 evidence_level 规则依赖「目标消费级别」（590），M5 却没有该入参。

- A：只冻结 m4 `candidate_package`，其余经 lineage 反查。违反 207。
- B（推荐）：冻结 m4 `candidate_package` + `candidate_set`、m3 `corpus_package` + `corpus_spans`、m2 `ocr_page_set`、m1 `source_manifest`；配置修订增加 `target_consumption_level`。
- C：只冻结 m4 与 m3，G1 页哈希链改由 M8 复验。与 588 的 M5 工位分配冲突。

### D-03 首纵切是否包含 M7，M8 读什么

§16 661–662 要求 M8 冻结 CanonicalKnowledgeSnapshot；§22.2 977–979 从 M5 直达 M8，§22.3 991 薄接入名单也没有 M7；§16 713/714 的 SourceAnchor 与页尺寸不在 Snapshot 的规定字段里。

- A（推荐）：M7 薄直通。一个 ReviewedEditionPackage 转成 Snapshot，提案全为空，不接人工；M8 另外冻结 m3 `corpus_spans` 与 m1 `source_manifest` 以打锚点与资产。理由：M8 接口一次定型，符合 §20.10 947「换 Adapter 不改相邻 Interface」。
- B：首纵切 M8 直接吃 ReviewedEditionPackage，纵切后再改接 Snapshot。接口二次变更。
- C：跳过 M6/M7，M8 直接吃 Candidate+Validation（仅 INTERNAL_DEMO）。与 §6.2、§14 链路不符。

### D-04 ReleaseRun（M7/M8）在 Ledger 中的运行归属

`create_processing_run(kind, edition_part_id, technique_id)` 要求单个 `art_` 形式的 `edition_part_id`（service.py 319–327，store.py 81 `NOT NULL`）；StageCheckpoint 链键为「EditionPart × Stage」（规格 842）。ReleaseRun 可汇入多个 ReviewedEditionPackage（155–159），两者对不上。

- A（推荐，最薄）：release_run 的 `edition_part_id` 填本次首个 ReviewedEditionPackage 所属 Part；全部 Part 登记在 m7 配置修订 `edition_part_ids`；m7/m8 Checkpoint 链沿用该 Part。首纵切只有一个 Part，无歧义。
- B：为 Release 引入独立作用域（改 Ledger 表，并需新身份，如以 `rel_` 充当作用域）。需改 impl-01 已验收代码。
- C：m7/m8 仍挂 EditionRun。违反 §6.2。

### D-05 阶段 payload 是否入 Schema；m1–m3 金标与生产形状已分叉

`stage_package.schema.json` 22–24 对 payload 不设约束。实际已分叉：expected/m3 payload 为 `{spans_path, coverage, excluded_pages}`，生产 `run_m3` 为 `{spans_revision_id, coverage, excluded_pages, gate_profile}`（impl-02 act/03 54）；expected 包 `input_artifacts` 只列 1 条，生产冻结 6 条。

- A（推荐）：不改 L0。新增 `stage_payload_m4..m8.schema.json`，只约束 m4–m8，禁止 `*_path` 键、只用 `*_revision_id`；m1–m3 保持现状，并在 INTERFACES 中声明下游不得依赖 `*_path`。`content_sha256` 统一为「sha256(本阶段主内容 Artifact 字节)」，与 m3 同规则。
- B：在 `stage_package.schema.json` 的 allOf 中按 stage 绑定 payload，同步重做 m1–m3 金标与 `run_m3`。改 L0，波及已验收的 impl-01/02。
- C：payload 不约束，只约束内容 Artifact。下游对 payload 键无契约可依。

### D-06 金标比对粒度与投影实现归属

生产用 UUIDv4 发号，包与内容中的 `rev_/art_/prun_/srun_/pkg_/rel_/ent_` 每次运行不同，无法逐字节比对。

- A（推荐）：「身份归一化投影」。按遍历顺序把 UUID 家族 ID 一致重命名为 `<rev#1>` 等占位后比对；人工闭集 ID（`ss_/as_/pr_/co_/pat_/sch_`）与内容保持原样；再排除 `validators[].version`、`*_path`。投影函数写在 Contract Registry 包，各模块验收直接调用；fixture 的 `verify.sh` 独立实现一份用于自证。
- B：全包字节相等，生产代码注入 IdProvider，测试一律用常量 ID。实现侵入大。
- C：只比 counts 与 content_sha256。内容错误可漏检。

### D-07 UUID 家族在金标中的确定性

`ent_`、`rel_` 规定为 uuid4（288、318）。

- A（推荐）：生产用 uuid4；金标与 ingest 用常量 ID（沿用 fixture_ingest 显式 ID 先例，形如 `rev_` + 左补 0 的后缀）；比对走 D-06 投影。
- B：uuid5 派生。违反 288 冻结。
- C：首个 Release 后持久化 entry 映射表，由后续 Release 复用（该机制仍需要，但不解决首个 Release 的金标问题）。

### D-08 规格要求有身份、但没有登记前缀的对象

§8.1 265 要求 EvidenceLink 同时记录 `entity_id` 与 `artifact_revision_id`；ApplicabilityRule、Case、Interpretation、Alias、Merge/Alias/Conflict/EvidenceRelation Proposal、CorrectionRequest、ReworkImpactReport 都没有前缀（registry §3 20–63）。

- A：按 registry §4 91–97 流程新登记（如 `el_<32hex>`、`rule_<technique>_<6位>`），需用户确认。
- B（推荐，首纵切）：EvidenceLink 内嵌在 Assertion 中，身份取复合键 `(assertion_id, source_span_id, char_start)`；Proposal/CorrectionRequest/ReworkImpactReport 只以 `art_`+`rev_` 为身份；m4 Schema v1.0.0 中 `applicability_rules`、`cases`、`editorial_notes` 用 `maxItems: 0` 锁死，待前缀登记后升版。ReviewDecision 用 `human_event` 修订号（service.py 824/922 已实现）。
- C：全部用 `art_`。EvidenceLink 数量大，逻辑身份过重。

### D-09 G4「school_ids 不留空」与无流派内容冲突；BLOCKED 门禁能否放行 M5 Gate

G4（601）要求 `school_ids` 不留空，而目录型主张没有流派；registry §3.3 54 规定首批 `sch_qizheng_` 随 M4 首次抽取冻结。§13.1 606 的放行条件只写「严重错误、失败任务、待修任务为零」，608 又写「任一断言缺失 fail-closed」。

- A（推荐）：G4、G6 在 mini_ed01 上报 `blocked` 并写明原因；M5 Gate 放行规则为：目标 INTERNAL_DEMO 时 `failed=0` 即放行，blocked 必须在 gate_results 与 ReleaseManifest `known_defects` 逐条披露；目标 DEV_SEARCH/PUBLIC_RELEASE 时 blocked 视同 failed。
- B：新增枚举 `school_scope: not_applicable`。需扩字段语义。
- C：blocked 一律视同 failed。首纵切在 M5 即断链。

### D-10 artifact_type 命名，以及 `validation_report` 同名异构

`artifact_type` 只有正则约束（artifact_ref 26–29），无闭集。`validation_report` 已有两种内容：fixture_ingest 写的是 expected 包的 validation 段（341–348），run_m3 写的是 gate 摘要。§16 695 的子包也叫 ValidationReport。

- A（推荐）：`validation_report` 保留为「每个 StepRun 的通用自检报告」；M5 业务产物命名 `gate_results`（内容）+ `validation_package`（阶段输出索引）；M8 子包命名 `release_validation_report`。各阶段统一「主内容 Artifact + 阶段输出索引 Artifact」双修订模式（与 m3 的 `corpus_spans` + `corpus_package` 一致）。闭集暂由 INTERFACES §4 充当，后续移交 Contract Registry。
- B：按阶段加前缀（`m5_validation_report`）。
- C：先实现 Contract Registry 的 artifact_type 登记册，再定名。阻塞并行。

### D-11 M4 的模型调用与冻结字典缺失

§12.2 572–574 规定 A/B/C 三个模型独立工作且完整留痕；执行纪律禁止调用模型 API。§12.1 540/547 的 `schemas/shared/canon`、`schemas/shared/homographs` 与 L3 `schemas/techniques/qizheng/glossary_v0.yaml` 在仓库中**均不存在**。

- A（推荐）：M4 首纵切实现「录制回放」适配器。模型 Prompt/Response 作为 `model_run` 冻结输入 Artifact，测试与金标只用录制；L1/L2 冻结表缺失时 `term_layers` 只产出 L3 候选，并在 Gate 中报 blocked。
- B：沿用现有任务管线离线产出候选，以 legacy candidate 导入（§22.4 999）。
- C：实调模型 API。需用户批准，并登记成本与密钥边界。

### D-12 M3 语义层与 M4 的先后；quote hash 由谁计算

M4 按 §12.2 561 读取 SemanticSpan，而 M3 目前只有结构层（`gate_profile: structural_only`）。§11.1 527 与 G3（67）要求 quote hash，`spans.yaml` 却没有该字段。

- A（推荐）：M4 首纵切以 StructuralSpan 为输入，candidate_set 记 `span_layer: structural`，可并行；quote hash 规则固定为 `sha256(quote 的 UTF-8 字节)`，由 M4 写进 evidence、M5 复算，不改 `spans.yaml`（sha `ec6d77b9…` 不动）。
- B：先完成语义层，再冻结 m4 金标（串行）。
- C：让 M3 在 spans 中增加 `quote_sha256`。改动已冻结金标及 impl-02 验收。

### D-13 共享热点文件的写权

`fixture_ingest.py`（各模块验收都要灌入金标上游）、`openspec/schemas/verify.sh`、fixture 生成器与 `verify.sh`、`run_all.sh`、生产代码加载新 Schema 的入口（service.py `_load_validator` 只注册 artifact_ref）。

- A（推荐）：`fixture_ingest` 扩到 m8 金标归 impl-00 ACT 09；生成器与 fixture `verify.sh` 只归 impl-00；`run_all.sh` 只在端到端批次改；Schema 加载入口由 Contract Registry 包先交最小版 `load_schema(name)`，其他包不得各自扩 Ledger。
- B：各模块包自行扩展。并行写冲突。
- C：全部归 Local Orchestrator 包。它排在首纵切之后（§22.4 1000），会阻塞批次 1。

### D-14 ReviewDecision 的 verdict 枚举与内容成熟度迁移

§14 618 列出「接受、修改、驳回、补证、流派分歧、专家签发」，§8.2 351–364 只定义 8 个 `decision_type`，并要求与 content_status 正交（433–440）；何种决定触发 `content_status` 迁移未定义。

- A（推荐）：`verdict` 闭集 `accept / modify / reject / request_evidence / school_dispute`，「专家签发」不是 verdict，而是 `content_status_after: expert_verified` 且须有对应 decision_type；首纵切 INTERNAL_DEMO 不改 content_status（保持 `machine_extracted`）。
- B：把 verdict 并入 decision_type。违反 353 的正交要求。
- C：verdict 用自由文本。不可机器判定。

### D-15 首纵切 PublicationPackage 子包范围与 ReleaseManifest 未定义字段

§16 680–695 列 11 项；§22.2 979 只列 4 项，983 又要求 AnchorContractPack；ReleaseManifest（697）必备；§20.9 945 需要 GraphProjectionPack。`min_app_version` 来源、`source_release` 取值闭集（697 只出现 `dev`）均未定义。

- A（推荐）：首纵切为 6 个子包（KnowledgeData、EvidenceMap、SourceAsset、QueryContract、AnchorContract、release_validation_report）+ ReleaseManifest；`source_release` 取 `internal / dev / release`；`min_app_version` 首纵切固定 `"0.0.0"`；RuleIndex/SearchIndex/GraphProjection/TechniqueProfile 四包留纵切后（20.9 继续 BLOCKED）。
- B：11 项全出，未实现的用空包占位。空包会冒充完成。
- C：严格只出 §22.2 的 4 项。与 983、697 冲突。

### D-16 SourceAssetPack 的字节与权利字段

fixture 禁止图像（verify V8；README §2），`derived_page_images_only` 却要携带派生页图（722）；manifest 的 `rights_status` 为自由文本「public_domain_text（…unconfirmed）」，与 SCHEMA.md §1 的枚举 `public_domain/licensed/unknown` 不一致。

- A（推荐）：金标只登记引用、sha256、宽高与 `bytes_included: false`；验收时从本地 Object Store 解析字节，缺素材报 BLOCKED；`rights_status` 暂按原文透传，另立工作包收敛为闭集。
- B：fixture 金标改用 `reference_and_hash_only`。与 manifest 的 `release_policy` 不一致。
- C：派生页图放进 fixture。违反 V8 与版权约束。

### D-17 错误码闭集不足以覆盖 M5/M8 的新失败类别

§8.2 368 规定表外错误码无效（9 个），但「证据越界、零命中、glyphbox 不足、证据链断裂、锚点不可迁移」都没有专门错误码。

- A（推荐）：映射到现有 9 码（越界/引文不符 → `TXT_001`，悬空/断链 → `REF_001`，缺证据 → `SEM_001`，重复 → `ID_002`，级别不足/非法枚举 → `SCH_002`），并以 snake_case 检查名细分；不扩枚举。
- B：扩展错误码表，需改规格 §8.2 与 SCHEMA.md。
- C：新类别不填错误码（`error_code: null`）。不可统计。

## 5. 起草假设（裁决前 ACT 按此撰写）

各 ACT 按 §4 全部「推荐」项撰写，并在 `ACT.yaml` 的 `decisions_required` 中注明依赖哪几条；主 Agent 若取其他选项，先改对应 ACT 再派发。常量 ID 统一构造为 `前缀 + 后缀.rjust(32, "0")`（后缀表见 `FIXTURE-PLAN.md` §2.3）。

## 6. 目录规划

```text
docs/blackbox-spec-rework/work-items/impl-00-interfaces/
  README.md  INTERFACES.md  FIXTURE-PLAN.md  BDD.md  TDD.md  ACT.yaml
  act/00.yaml … act/09.yaml
  check_i00.py            （ACT 00 新建：C00–C09 契约检查器）
  tests/test_check_i00.py （ACT 00 新建）
  fixture_mutations.sh    （ACT 08 新建：20 例篡改矩阵）

openspec/schemas/                      （ACT 01–04 新增，verify.sh 只追加）
  contract_common.schema.json  candidate_set.schema.json  gate_results.schema.json
  review_decision.schema.json  reviewed_edition.schema.json  rework_impact_report.schema.json
  canonical_snapshot.schema.json  release_manifest.schema.json  knowledge_data_pack.schema.json
  evidence_map_pack.schema.json  source_asset_pack.schema.json  anchor_contract_pack.schema.json
  query_contract_pack.schema.json  stage_payload_m4.schema.json … stage_payload_m8.schema.json
  examples/<schema>.valid.yaml  examples/<schema>.invalid_*.yaml

pipeline/corpus/_fixture/mini_ed01/expected/   （ACT 05–07 由生成器产出）
  m4.candidate_set.yaml  m4.stage_package.yaml
  m5.gate_results.yaml   m5.stage_package.yaml
  m6.review_decision_01..05.yaml  m6.reviewed_edition.yaml  m6.stage_package.yaml
  m7.canonical_snapshot.yaml  m7.stage_package.yaml
  m8/knowledge_data_pack.yaml  m8/evidence_map_pack.yaml  m8/source_asset_pack.yaml
  m8/query_contract_pack.yaml  m8/anchor_contract_pack.yaml  m8/release_validation_report.yaml
  m8/release_manifest.yaml  m8.stage_package.yaml
  SHA256SUMS
```

## 7. 与其他并行草案的接口假设（摘要；逐项见 INTERFACES.md §6）

1. 各模块验收以 `ingest(fixture, service, stages=前缀)` 灌入金标上游，再比对本阶段金标投影（D-06/D-13）。
2. 各阶段产出「主内容 Artifact + 阶段输出索引 Artifact」两个修订，StagePackage 的 `output_artifacts[0]` 指向索引（D-10）。
3. m4–m8 的 payload 只含 `*_revision_id(s)` 与标量，不含 `*_path`（D-05）。
4. M5 冻结 m1–m4 共 6 个修订并接收 `target_consumption_level`（D-02）；M8 冻结 m7 Snapshot + m3 corpus_spans + m1 source_manifest（D-03）。
5. m7/m8 属 release_run，`edition_part_id` 取首个 Part（D-04）。
6. ReviewDecision 即 `human_event` 修订，内容符合 `review_decision.schema.json`，并带 `decision_type`（D-14）。
7. G 代号只用 G1–G7；阶段 Gate 称「M<n> Gate」，检查名 snake_case；错误码只用 9 个（D-17）。
8. 生产代码经 Contract Registry 的 `load_schema` 加载新 Schema，不改 Ledger 的 `_load_validator`（D-13）。
