# impl-03：M5 Automatic Validation（§13）首切片——G1–G3 与 glyphbox_level 证据门禁

状态：`READY_FOR_REVIEW`（按 `G7-RULINGS.md` 定稿；§4「主 Agent 决定」执行者不重议）

前置：impl-02 `ACCEPTED`（含 J3 返工 act/05：冻结输入字节校验、页登记与终态严格比对、begin 后异常封存）。当前工作树 `pipeline/corpus_compiler/step.py` 已含 J3 返工（无裸 `pass`、无 `files_hash`），开工基线见 `TDD.md` §0。

## 1. 目标

在 `pipeline/validation/` 落地规格 §13 / §13.1 的 M5 首切片：从 Artifact Ledger 冻结读取已 `succeeded` 的 M3 结构层产出（m3 StagePackage、`corpus_package`、`corpus_spans`、`coverage_report`、批次与 M3 自身冻结的 M1/M2 输入），以**确定性、不改输入、fail-closed** 的 14 个已注册 Validator 执行 G1（来源与可重放性）、G2（全书覆盖）、G3（身份、引用与证据锚点，含 `glyphbox_level` 证据门禁），每个 Validator 一个 task、一个 StageCheckpoint，产出 `gate_results`（内容）+ `validation_package`（阶段输出索引）+ m5 StagePackage；并新建 §19.0 已登记的判据脚本 `openspec/acceptance/m5-evidence-gate.sh`。

**首纵切范围**（`G7-RULINGS.md` §1 P1、§9 第 2 与第 22 条）：

- 输入边界 `scope: corpus_only`：只冻结 M3 StagePackage 及其血缘输入，共 17 个修订（见 §5.1）；M4 未实现。
- 门禁：G1、G2、G3 由 M5 执行，含 `glyphbox_level` 证据门禁（§11.1）。
- G4（内容分层）、G5（概念与检索）、G6（盘面确定性匹配前半）记 `not_evaluated`，验收脚本判 `BLOCKED`；G7 按 §13.1 延至 M8。
- **零模型调用**（P6）：本包不调用任何模型 API，正常路径与对抗路径都不依赖模型输出。
- 依赖 M4 的 G3 子项（evidence 位于所声明 span 内、direct proposition 忠实性）同记 `not_evaluated`。

完成判据（本批唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/validation/tests -t . 2>&1 | tail -1   # OK；ACT 06 后累计用例数 ≥ 83（逐 ACT 阈值见 TDD.md §1）
bash openspec/acceptance/m5-evidence-gate.sh; echo exit=$?
# 期望：9 行 PASS（inputs_frozen、validator_checkpoints、g1_source_replay、g2_coverage、g3_anchor_offset、
#       gate_and_levels、package_lineage、fail_closed_tamper、adversarial_bypass）
#       + 5 行 BLOCKED（candidate_evidence、g4_content_layering、g5_concept_search、g6_rule_executability、quote_hash_stored）
#       + SUMMARY pass=9 fail=0 blocked=5；exit=2
bash openspec/acceptance/m3-coverage.sh | tail -1   # 仍为 SUMMARY pass=8 fail=0 blocked=1（本批不改 M3）
bash openspec/acceptance/run_all.sh | tail -1       # 仍为 SUMMARY pass=2 fail=1 blocked=8（本批不改 run_all.sh）
```

`m5-evidence-gate.sh` 返回 **2** 而非 0：无 FAIL，但 Candidate 相关校验与 G4–G6 缺 M4 输入、span 未存储 quote hash（§11.1）。返回 0 须等 M4 首切片落地且 §4 D-02 选定的 quote hash 归属实现。§19.0「M5 全书与证据校验不足」差距仍标记为未关闭。

fixture 上的期望判定（目标消费级别 `INTERNAL_DEMO`，§22.1 第 968 行），均已由起草 Agent 用 fixture 实测：

| Validator / 检查 | 发现数 | 分级严重度（INTERNAL_DEMO / DEV_SEARCH / PUBLIC_RELEASE） | 实测依据 |
|---|---|---|---|
| `g1_unresolved_chars` / `unresolved_glyph` | 2（`ss_sanche_ed01_p0001_s03` 含 `page_001c0038/c0040/c0041`；`…_s04` 含 `page_001c0036/c0037`） | warning / error / error | `pages/page_001.json` 5 个字框 `status: unrecognized`、`char: ""`、`source: manual` |
| `g1_unresolved_chars` / `unproofread_glyphs` | 2（page_001 32 个、page_003 193 个 `status: pending`） | info / warning / error | 230 个字框中 225 个 `pending` |
| `g3_strict_offset_quote` / `quote_hash_not_stored` | 1（整份 `corpus_spans`） | warning / error / error | 代码、fixture、schemas 内 `git grep -n quote_hash` 0 处 |
| `g3_glyphbox_anchor` / `glyph_text_misaligned` | 2（s03：文本 `影宋刊本影印`、字框拼接 `宋刊本影印`；s04：文本末字 `藏` 无字框） | warning / error / error | 43 条 Span 中 2 条字框拼接 ≠ 文本 |
| 其余 11 个 Validator | 0 | — | M3 结构 Gate 已独立判过；M5 重算（14 个注册 Validator 中 3 个有发现） |

合计 findings **7**（G1 4 + G3 3；目标级别 `INTERNAL_DEMO` 下 warnings 5、info 2、failures 0），与 `BDD.md` 2.1/4.1 一致，`counts.findings == 7`。

由此：`gate = {passed: true, severe_error_count: 0, failed_task_count: 0, pending_rework_count: 0}`；`level_verdicts = {INTERNAL_DEMO: passed, DEV_SEARCH: failed, PUBLIC_RELEASE: failed}`。

## 2. 依据（只读来源，文件:行号）

- 规格 `openspec/learn-system-blackbox-architecture.md`
  - §6.1 EditionRun 包链 `CorpusPackage → CandidatePackage → ValidationPackage`：141–147；阶段放行「失败为零、输出 Contract 通过、StageManifest 封存」：149
  - §7 只读冻结输入：207；§8 StagePackage 六段：232–246；§8.1 `pkg_<stage>` 闭集含 `m5`：298
  - §8.2 第 3 表 9 个校验错误码「M5 Validator 等的标准输出集合，表外代码无效」：366–380
  - §11 M3 Gate：521；§11.1 `offset_level` / `glyphbox_level`（quote hash、四点坐标、PUBLIC_RELEASE 必须 glyphbox）：525–528
  - §13 确定性、不用模型、不改 Candidate：580；通用 Validator 清单：582；§13.1 G1–G7 工位：588–604；ValidationPackage 六要素与 Gate 放行：606；全链哈希、重放、fail-closed：608；G6 在 M5 只做可执行性：610
  - §14 M6 读 CandidatePackage、ValidationPackage、CorpusPackage：618、624
  - §16 消费级别显式输入与 fail-closed：666–668；三级准入：676–678；字框坐标与页图像素同源可换算：714
  - §17 事务序列（失败与部分输出也封存）：836；§17.1 非人工任务每 task 一个 Checkpoint：843；失败任务进 Checkpoint：846
  - §19 M5 行（`pipeline/validators`，首纵切内）：879；M3/M4 行名：877–878；§19.0 `m5-evidence-gate.sh`：909
  - §20 十一条判据：935–947；§22.1 `glyphbox_level`、`INTERNAL_DEMO`：968；§22.2「M5 Validator：G1–G3 与 glyphbox_level 证据门禁」：978；§22.3 阶段 1：991
- 裁决 `docs/blackbox-spec-rework/G7-RULINGS.md`：§1 原则 P1–P9；§9 表中与 impl-03 相关的第 2、6、8、9、10、12、13、17、18、19、20、21、22、23 条（逐条落地见 §4）。
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md`：§3 三级消费：40–46；G1：50–55；G2：57–62；G3：64–70
- `openspec/id-prefix-registry.md`：只引用已登记前缀：93（本包不新增前缀）
- `pipeline/ledger/`（impl-01 已验收，只调用、不改）：`service.py` `LedgerReadMixin` 111–164、`_configuration_stage` 295、`begin_step_run` 405、`put_artifact` 442、`put_run_artifact` 528、`register_stage_package` 718、`record_transformation` 777、`finish_step_run` 1132、`fail_step_run` 1187、Checkpoint stage 必须等于 StepRun stage 1257、`write_checkpoint` 1364、`read_object` 1606；`store.py` `stage_packages` 71–75、`step_runs` 88–103、`frozen_inputs` 119–124；`errors.py` `ERROR_CODES` 11–23
- `pipeline/corpus_compiler/`（impl-02）：`step.py` run_m3 产出布局（以 J3 返工后为准，act/03 contract 第 30–65 行）；`compiler.py` `compile_structural`（仅供 G1 重放调用）；`__init__.py` `M3_TOOL`/`M3_TOOL_VERSION`
- `pipeline/corpus/_fixture/mini_ed01/`：`manifest.yaml`（`source_assets` 宽高 1203×1654）、`pages/*.json`、`anomalies.yaml`、`spans.yaml`（sha256 `ec6d77b9…44ef`）、`verify.sh`
- 模板：`docs/blackbox-spec-rework/work-items/impl-02-corpus/`（README、BDD、TDD、ACT.yaml、act/01、03、04、PROMPT-J3.md、ACCEPTANCE.md）
- 并行草案（对账用，未定稿）：`impl-00-interfaces/README.md` D-02、D-06、D-08、D-09、D-10、D-12、D-13、D-17 与 §5.1、§5.2；`impl-06-review/README.md` §5.1

**引用核对（2026-09-12，定稿时逐条比对实际代码）**：

- act/04、act/05 调用的 Ledger 方法 `list_checkpoints`、`get_step_run`、`get_revision`、`list_transformations`、`read_object`、`put_run_artifact`、`put_artifact`、`seal_revision`、`write_checkpoint`、`record_transformation`、`register_stage_package`、`finish_step_run`、`fail_step_run` 均在 `pipeline/ledger/service.py` 存在，参数名与契约一致。
- act 中引用的 M3 产出 artifact_type `corpus_batch`、`corpus_spans`、`coverage_report`、`validation_report`、`step_log`、`corpus_package`、`failure_report`、`configuration`、`stage_package` 与 `pipeline/corpus_compiler/step.py`（195/218/236/251/263/283/409 行与 `put_run_artifact`、`register_stage_package`）实际写入一致。
- 本包新 artifact_type 仅 `gate_results`、`validation_package`（见 §3）。

## 3. 范围

写（全部新建）：`pipeline/validation/**`、`openspec/acceptance/m5-evidence-gate.sh`。

**artifact_type 纪律**（P2）：本包只新增 `gate_results`、`validation_package` 两个类型，须与 `impl-00-interfaces/INTERFACES.md` §4 临时闭集**逐字一致**——**开工前实跑 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py`，末行 `I00-IF SUMMARY pass=18 fail=0` 且 exit 0 才可实现**；不满足不得开始实现。每 Validator 报告复用通用已登记类型 `validation_report`，**不引入** `validator_report`、`gate_report` 等新类型名。新内容结构以代码内草案契约表达，`schema_version: "0.1.0-draft"`（P3），不新增 `openspec/schemas/` 文件。

禁止：改规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`openspec/acceptance/run_all.sh` 与 `m3-coverage.sh`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、任何台账或 ACCEPTANCE 文件；新增依赖（只用标准库 + PyYAML + jsonschema）；新增 ID 前缀（`validator_id`、`task_id` 是任务标签，不是登记册 ID）；调用任何模型 API；生产代码读 fixture 路径或工作目录文件（只读 Ledger 冻结修订，元数据查询允许经 `reader.store.conn` 只读 SELECT，沿用 impl-02 inputs.py 先例，缺口清单见 §5.4）。

独立性纪律：
1. Validator 只读取冻结修订，不修改、不重写、不「修正」任何输入（§13:580）；
2. `g1_source.py`、`g2_coverage.py`、`g3_evidence.py` 不得 import `pipeline.corpus_compiler` 的任何模块（防止与 M3 同错同过）；唯一允许 import `pipeline.corpus_compiler.compiler` 的是 `replay.py`（G1 重放按定义需执行生产工具，§9 第 19 条）；
3. `acceptance.py` 不得 import `pipeline.validation` 的 `g1_source`、`g2_coverage`、`g3_evidence`、`replay`，判定一律自行重算；
4. fail-closed：`g1_frozen_bytes` 出现任何 error 发现，其余 13 个 Validator 记 `skipped_fail_closed`；Validator 自身抛异常记 `errored`；两者均计入 `failed_task_count`，任何级别都不得判 `passed`（§13:608）。

本批不改 `run_all.sh`（P4）：§20 没有任何一条会因 M5 首切片单独落地而由 BLOCKED 变 PASS——20.1 仍缺 Local Orchestrator 与 M4/M6 Gate，20.4/20.8 仍缺 M8。M5 的 `gate_results` 是 20.4（候选与校验可追溯）、20.8（EvidenceMapPack 证据完整性）的前置输入。

## 4. 主 Agent 决定（执行者不重议）

依据 `G7-RULINGS.md` §9（impl-00 与 impl-03 合并去重的 23 条）与 §1 原则。裁决表未单列者默认采纳 impl-03 原「推荐」项；执行者实现时按本表落地，不得重议、不得自行取舍。

| impl-03 | 问题 | 主 Agent 决定 | 理由 / 落地位置 |
|---|---|---|---|
| D-01 | M4 缺席时 M5 的输入边界 | §9 第 2 条：采纳 `corpus_only`——冻结 m3 包与 M3 全部血缘输入共 17 个；依赖 Candidate 的检查记 `not_evaluated`，验收报 BLOCKED；M4 落地后升级为 `corpus_and_candidates` | 采纳 impl-03 冻结集合（含页修订、批次、配置、m3 包），因 G1 重放、G2 重算覆盖、G3 引用闭合需这些对象的**内容**（§7:207 禁经血缘反查读未冻结修订）。落地：act/04、§5.1 |
| D-02 | quote hash 的归属 | §9 第 12 条：采纳推荐 B——M5 按 `sha256(quote)` 复算；Span 自带 `quote_sha256` 则逐条比对，不符判 TXT_001；整份未存储记恰 1 条 `quote_hash_not_stored`（SCH_001）。**不改 M3 `spans.yaml`** | P9 不改已验收模块；与 impl-00 D-12 一致。落地：act/03 |
| D-03 | 「四点坐标」与现有 `box{x,y,w,h}` | §9 第 18 条：采纳推荐 A——`angle == 0` 时轴对齐框与四点坐标等价；`angle != 0` 且无四点字段判 `anchor_field_missing` | fixture 全部字框/行框轴对齐。落地：act/03 |
| D-04 | 「未决字符」的定义与分级严重度 | §9 第 9 条：采纳推荐 C——PUA/U+FFFD/控制符/占位符在文本中出现三级 error；`unrecognized`/空字符字框 `{warning, error, error}`；`pending` `{info, warning, error}` | 与 impl-00 D-09 A 分级放行一致：INTERNAL_DEMO 如实披露不阻断，DEV_SEARCH/PUBLIC_RELEASE fail-closed。落地：act/01 |
| D-05 | 字框序列与 Span 文本不对齐 | §9 第 9 条：采纳推荐 B——`glyph_text_misaligned`（TXT_001）`{warning, error, error}`，逐条列出主体 Span 与差异 | 与 D-04 合并决定 PUBLIC_RELEASE 能否达真实 `glyphbox_level`。落地：act/03 |
| D-06 | G1「重放一致性」的实现方式 | §9 第 19 条：采纳推荐 A——**只有 `replay.py` 可 import `pipeline.corpus_compiler.compiler`**；先比对 m3 配置 `tool`/`tool_version` 与已安装版本，再重放并逐字节比对；G2/G3 独立重算，禁止 import M3 | 防同错同过。落地：act/01、`ACT.yaml` 全局规则 |
| D-07 | 目标消费级别来源与判几级 | §9 第 20 条：采纳推荐 B——配置带 `target_consumption_level`（默认 `INTERNAL_DEMO`），决定 `gate.passed`；同时对三级计算 `level_verdicts` 写进 `gate_results` 与 m5 StagePackage | M8 可不重跑 M5 直接拒绝 `level_verdicts[目标] != passed`（§16:668）。落地：act/05 |
| D-08 | Gate 未通过时 M5 StepRun 终态 | §9 第 21 条：采纳推荐 A（14 个 Validator 跑完即 `succeeded` 并照常封存，`validation.passed` 与 `gate.passed` 取目标级别结论；只有输入契约或内部异常才 `failed`）；**追加约束见 §5.3** | M5 失败项与返工任务是 M6 的业务产物（§14:618）。落地：act/05 |
| D-09 | ValidationPackage 结构、artifact_type、是否入 Schema | §9 第 10 条：采纳——`gate_results`、`validation_package` **提名入 INTERFACES §4 临时闭集**（P2），结构为代码草案 `0.1.0-draft`（P3），不新增 Schema 文件；每 Validator 报告复用通用 `validation_report`，不引入 `validator_report`/`gate_report` 等新类型 | P2「未入闭集的类型名不得使用」；`validator_report` 不在 §9 第 10 条提名，故不采用。落地：act/05、§5.2/§5.3 |
| D-10 | 错误码闭集不足 | §9 第 17 条：采纳推荐 A——按现有 9 码映射，缺项 `code: null`，缺口清单见 §5.5 | §8.2 表外码无效。落地：act/00 `CHECK_CODES` |
| D-11 | 返工任务的身份与指向阶段 | §9 第 8 条：采纳推荐 A——不新增前缀（P8，id-prefix-registry:93）；按 `(rework_stage, validator_id, check)` 聚合排序，`rework_stage ∈ {m2, m3}` | 无前缀对象按 impl-00 D-08 取身份。落地：act/05 |
| D-12 | G4/G5/G6 与 Candidate 子项披露；G6 的 M5/M8 分工 | §9 第 22 条：采纳推荐 A——`gate_results.not_evaluated` 逐条写 `{gate, check, reason}`，行名「M4 Knowledge Extraction」；验收脚本报 BLOCKED | 省略行会假绿；报 FAIL 无法区分真缺陷。落地：act/05、act/06 |
| D-13 | 验收脚本如何构造「M3 同错同过」的对抗输入 | §9 第 6 条：采纳推荐——用 `unittest.mock.patch` 替换 M3 编译与结构 Gate，构造布局真实、sealed 的错误 m3 包，再断言 M5 命中 | 手工伪造易漂移。落地：act/06 |
| D-14 | Ledger 元数据查询没有公开读方法 | §9 第 13 条：采纳推荐 A——经 `reader.store.conn` 只读 SELECT，集中写在 `inputs.py` 三个私有函数，清单见 §5.4 | Ledger 读优先 `LedgerReader` 公开方法，缺口处允许只读 SELECT 并登记，供 impl-08 补读接口。落地：act/04 |
| D-15 | 上游 StagePackage 的 StepRun 终态过滤 | §9 第 23 条：采纳（P5，impl-02 ACCEPTANCE §5.3）——只接受 `succeeded` StepRun 的包，非 `succeeded` 一律抛 `ValidationRefused` | 严禁消费失败运行遗留的包。落地：act/04 |

## 5. 接口契约（供与 M3/M4/M6/M8 与 impl-00 草案对账）

### 5.1 上游输入契约（本包依赖）

> **核心约束（impl-02 ACCEPTANCE §5.3 登记，§9 第 23 条）**：M5 解析上游 StagePackage 时**只接受 StepRun 状态 `succeeded` 的包**。若上游 StepRun 为 `failed` 或非 `succeeded`，一律拒绝解析并抛出 `ValidationRefused`。
>
> **M5 特例（§9 第 21 条追加约束）**：下游消费 m5 StagePackage 时，须**同时**满足「所属 StepRun 状态为 `succeeded`」**且**「StagePackage `validation.passed == true`」，二者缺一不得消费。

| 来源 | 定位方式（只经 Ledger） | artifact_type / 对象 | 读取的字段 |
|---|---|---|---|
| M3 StepRun | `list_checkpoints(ep,"m3")` 最新项的 `step_run_id`；`get_step_run().status == "succeeded"`（必须为 succeeded） | `step_runs.request_json` / `result_json` | `configuration_artifact_id`、`input_artifact_ids`（顺序）、`technique_profile_id`、`output_artifact_ids`、`validation_report_ids` |
| M3 输出 | `result_json.output_artifact_ids` 按 artifact_type 各恰 1 个；对应 m3 StagePackage 归属的 StepRun 状态必须为 `succeeded` | `corpus_package`（JSON）、`corpus_spans`（YAML，impl-02 act/01 R7/R8 键序）、`coverage_report`（JSON）、m3 StagePackage（`stage_packages.stage == "m3"`） | `corpus_package.spans_revision_id`；spans 表头 `work, source_id, edition_part_artifact_id, evidence_level, content_status, span_count, batch_count`；Span 全部键；m3 包 `manifest.counts`、`content_sha256`、全部 ArtifactRef、`lineage` |
| M3 自检 | `result_json.validation_report_ids` 恰 1 个 | `validation_report` | 只冻结不解析 |
| M3 配置 | `request_json.configuration_artifact_id` | `configuration`（JSON） | `stage == "m3"`、`tool`、`tool_version`、`batch_size`、`gate_profile` |
| M3 批次 | 该 StepRun 的 m3 Checkpoint 链序 `completed_tasks` | `corpus_batch`（JSON 列表） | 批号与 Span 列表 |
| M1/M2（经 M3 冻结） | `frozen_inputs` 中 M3 StepRun 的行，按 `request_json.input_artifact_ids` 顺序 | `source_manifest`（YAML）、`ocr_page_set`（JSON）、`ocr_page` ×3、`human_event` ×1 | manifest `source_id, technique_id, edition_part.pages, source_assets[page,sha256,width,height]`；`ocr_page_set.ocr_pages[page,sha256]`、`terminal_states`；页 JSON `lines[id,box,text,angle]`、`chars[id,parent,char,box,status]`；人工事件 `page` |
| M2 Checkpoint | `list_checkpoints(ep,"m2")` 全链 | — | 页 → 修订、终态（与冻结 `ocr_page_set` 交叉核对） |

冻结修订集合固定为 17 个：m3 包、`corpus_package`、`corpus_spans`、`coverage_report`、`validation_report`、`configuration`、5 个 `corpus_batch`、`source_manifest`、`ocr_page_set`、3 个 `ocr_page`、`human_event`。

假设 M3 的 `ocr_page_set.ocr_pages` 为非空列表、每项含 `page` 与 `sha256`（impl-02 act/05 C2）。M3 语义层（impl-10）落地后，`gate_profile` 会升级，Span 可能分为结构层与语义层；本包按 `gate_profile == "structural_only"` 取结构层，遇到其他取值时判 `input_contract` 失败，不静默兼容。根据 impl-02 ACCEPTANCE §5.3，上游失败或重跑留下的未封存/归属失败运行的 StagePackage 坚决丢弃，只认 succeeded StepRun 的包。

### 5.2 本包内部对象

- **Finding**：`validator_id, gate, check, code(9 码或 null), severity{INTERNAL_DEMO,DEV_SEARCH,PUBLIC_RELEASE ∈ error|warning|info}, subject{entity_id, artifact_revision_id, page}, relation(null|artifact_ref|content_hash|anchor_image|batch_membership), rework_stage(m2|m3), detail`。
- **Validator 报告**（每 task 一个修订，artifact_type 复用 `validation_report`；内容 `schema_version: "0.1.0-draft"`）：`validator_id, gate, version, task_status(succeeded|errored|skipped_fail_closed), checked{…计数}, findings[]`。
- **m5 StageCheckpoint**：`task_id = validator_id`；`completed_tasks[{task_id, artifact_revision_id: 该 Validator 报告修订, status: succeeded|failed, terminal_state: null}]`；`pending_queue` 为其后的 validator_id；`human_decisions: []`。

### 5.3 下游输出契约

- **`gate_results`（JSON，主内容；`schema_version: "0.1.0-draft"`）**：`scope:"corpus_only", target_consumption_level, validator_suite:"pipeline.validation", validator_version, validators[{validator_id,gate,version,task_status,report_revision_id}], gates{G1..G3: passed|passed_with_warnings|failed, G4..G6: not_evaluated, G7: deferred_to_m8}, passed_checks[validator_id], failures[Finding], warnings[Finding], broken_relations[{relation,subject,code,detail}], rework_tasks[{rework_stage,validator_id,check,code,subjects[]}], not_evaluated[{gate,check,reason}], level_verdicts{INTERNAL_DEMO,DEV_SEARCH,PUBLIC_RELEASE}, gate{passed,severe_error_count,failed_task_count,pending_rework_count}, counts{validators,findings,failures,warnings,broken_relations,rework_tasks,spans_checked,pages_checked}`。
- **`validation_package`（JSON，阶段输出索引；`schema_version: "0.1.0-draft"`）**：`edition_part_id, technique_id, scope, target_consumption_level, validator_version, gate_results_revision_id, corpus_package_revision_id, corpus_spans_revision_id, m3_stage_package_id, m3_package_revision_id, candidate_package_revision_id(null), gate{…}, level_verdicts{…}`。
- **m5 StagePackage**：形状同 impl-02 act/03 第 13 步（信封 `schema_version: "1.0.0"`，L0 Schema 不变）；`stage:"m5"`；`payload{validation_package_revision_id, gate_results_revision_id, scope, target_consumption_level, gate, level_verdicts}`；`manifest.input_artifacts` = 17 个冻结修订（m3 包用 `artifact_kind: stage_package`）；`output_artifacts=[validation_package]`；`counts{validators, findings, failures, warnings, rework_tasks}`；`content_sha256 = sha256(gate_results 字节)`；`validation{passed: gate.passed, report_artifacts:[14 个 Validator 报告修订]}`；`lineage.upstream_artifacts=[m3 包, corpus_package, corpus_spans]`；transformation `operation: validate_corpus`。

> **§9 第 21 条追加约束**：m5 StagePackage 的 `validation.passed` 必须**如实反映 Gate**（`== gate.passed`）。下游消费 M5 包须**同时**满足 `StepRun.status == "succeeded"` 与 `validation.passed == true`（P5 的 M5 特例）；`gate.passed == false` 时 StepRun 仍为 `succeeded`（D-08 A），故下游不得仅凭 `succeeded` 放行。

- **M6（impl-06）应读取**：`validation_package.gate.*`、`gate_results.failures/warnings/rework_tasks/broken_relations`。差异：impl-06 §5.1 假设的扁平 `entries[…result∈pass/warn/fail]` 在本包由 `failures`/`warnings` 表达（目标级别下），`info` 不下发；首切片 `candidate_package_revision_id` 为 `null`，M6 必须据此拒绝（没有候选包可审）。
- **M8（impl-04，尚无草案）应读取**：`level_verdicts[本次消费级别]` 必须为 `passed`，否则 fail-closed 拒绝；`validation_package.corpus_spans_revision_id` 必须等于 M8 冻结的 `corpus_spans`；消费 m5 包须同时满足 StepRun `succeeded` 与 `validation.passed == true`（§9 第 21 条）；`warnings` 进 ReleaseManifest `known_defects` 披露（与 impl-00 D-09 A 一致）。
- **M4（未起草）假设**：Candidate evidence 形如 `{source_span_id, start_offset, end_offset, quote_sha256}`，offset 相对 Span `text`（与 impl-06 §5.1 一致），M5 升级 `scope` 时新增 Validator，已有 14 个的 `validator_id` 不变。

### 5.4 只读 SELECT 清单（§9 第 13 条要求登记，供 impl-08 补读接口）

`LedgerReadMixin`（`service.py` 111–164）没有以下三类元数据的公开读方法，本包按 impl-02 `inputs.py`（101–108）先例经 `reader.store.conn` 执行**只读 SELECT**，集中写在 `pipeline/validation/inputs.py` 的三个私有函数中：

| 私有函数 | 读取的表 / 列 | 用途 |
|---|---|---|
| `_m3_step_run` | `frozen_inputs`（某 StepRun 的冻结输入行） | 解析 M3 自身冻结的 M1/M2 修订（§5.1） |
| `_artifact_types` | `artifacts.artifact_type`（经 `artifact_revisions` join） | 按 artifact_type 归类上游输出（`corpus_package` / `corpus_spans` / `coverage_report`） |
| `_stage_package_for_stage` | `stage_packages`（按 `stage='m3'` 取包及其归属 StepRun） | D-15 终态过滤：只接受 succeeded StepRun 的包 |

以上为**已知读接口缺口**，impl-08 Contract Registry / Ledger 补读接口落地后应改为公开方法；本包不修改 `pipeline/ledger/`（P9）。

### 5.5 错误码缺口清单（§9 第 17 条要求登记）

§8.2 第 3 表只有 9 个校验错误码（`errors.py` `ERROR_CODES`：SRC_001、SRC_003、TXT_001、ID_001、ID_002、REF_001、SCH_001、SCH_002、SEM_001），表外码无效。下列检查名在 9 码中**无无歧义映射**，`registry.CHECK_CODES` 取 `code: null`，靠 snake_case 检查名区分（与 impl-00 README §5.2 第 3 条一致）：

| 检查名 | 归属 Validator | 无映射原因 |
|---|---|---|
| `count_mismatch` | `g2_count_reconciliation` | 「计数对账不符」无语义吻合码 |
| `unproofread_glyphs` | `g1_unresolved_chars` | 「未人工校对」是披露项而非「未决字符」错误码 |
| `replay_tool_mismatch` | `g1_replay` | 「工具版本不符」不属 SRC_003（哈希）/REF_001（引用） |

其余检查名逐一映射到九码；`act/00` 的 `CHECK_CODES` 为权威表，`tests/test_registry.py` 逐项断言其值 ⊆ `ERROR_CODES ∪ {None}`。实现中若发现新的无映射检查名，同规则取 `null` 并在实现回报中登记。

## 6. 目录（落地后）

```text
pipeline/validation/
  __init__.py        M5_TOOL / M5_TOOL_VERSION / CONSUMPTION_LEVELS
  errors.py          ValidationRefused
  serialize.py       canonical_json
  findings.py        make_finding / make_report / level_verdicts / gate_summary
  registry.py        VALIDATORS（14 项，顺序固定）/ CHECK_CODES / resolve
  g1_source.py       g1_frozen_bytes / g1_page_registry / g1_content_hashes / g1_unresolved_chars
  replay.py          g1_replay（唯一 import corpus_compiler.compiler 的模块）
  g2_coverage.py     g2_page_accounting / g2_contiguous_coverage / g2_batch_partition / g2_count_reconciliation
  g3_evidence.py     g3_span_identity / g3_references / g3_strict_offset_quote / g3_glyphbox_anchor / g3_evidence_level
  inputs.py          resolve_m5_inputs（Ledger 读）+ 三个只读 SELECT 私有函数
  context.py         build_context（冻结字节 → raw/doc）
  package.py         assemble_gate_results / assemble_validation_package
  step.py            run_m5（§17 事务序列）
  __main__.py        python -m pipeline.validation
  acceptance.py      m5-evidence-gate 十四项判定
  tests/             helpers.py test_registry.py test_g1.py test_g2.py test_g3.py test_inputs.py test_step.py test_acceptance.py
openspec/acceptance/m5-evidence-gate.sh
```
