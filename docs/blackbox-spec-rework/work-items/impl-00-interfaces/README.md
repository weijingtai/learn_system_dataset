# impl-00：跨模块接口总表与金标 fixture 规划（M1–M8 对账基准）

状态：`READY_FOR_REVIEW`（W2-C1 定稿 2026-09-12；按 `G7-RULINGS.md` §9「impl-00 的首纵切裁剪」重写；未经实现）

首纵切裁剪结论（`G7-RULINGS.md` §1 P1/P3/P9、§9）：

- **保留 1 个 ACT**：`impl-00/10`「INTERFACES §4 临时闭集登记与首纵切裁决对齐」，见 `act/10.yaml`。
- **不保留金标 ACT**：已逐文件核查 impl-03（`pipeline/validation/**`）与 impl-04（`pipeline/dataset_compiler/**`）的 verify/tests，**均未引用** `pipeline/corpus/_fixture/mini_ed01/expected/` 下 m5/m8 期望产物（证据见 `ACCEPTANCE.md` §1），故按 §9 不保留生成 ACT。
- **原 `act/00–09.yaml` 全部标 `DEFERRED`**：m4/m6/m7 金标、`stage_payload_m4..m8` Schema、`fixture_ingest.py` 灌入 m1–m8（原 act/09）等一律移入 §5「纵切后待办」，文件内容不删除、不入 `executor_groups`。

## 1. 目标

为并行实现 M1–M8 冻结一份**可机器验证**的跨模块契约。首纵切内只做两件事：

1. **接口总表登记**（`INTERFACES.md`）：把 M5/M8 首纵切要用的新 `artifact_type` 一次性写入 §4 临时闭集（P2），并把 §2 各阶段卡片、§1 通用约定同步到 G7 裁决口径（M8 尾链、M5 `corpus_only`、§9 第 13/16/21 条等）。
2. **对账基准**：`INTERFACES.md` §2 逐阶段列出冻结输入、输出 `artifact_type`、StagePackage `payload`/`counts`/`content_sha256` 规则、Checkpoint 粒度、Gate 与 G1–G7 归属、人工队列、下游实际消费键；m1–m3 以现有代码与 fixture 的**实际形状**为准，m4–m8 为草案并标明规格未定义处。首纵切外的阶段标「纵切后」。

**纵切后**（§5）才做：新增 JSON Schema（P3 改为代码内草案契约，不向 `openspec/schemas/` 新增文件）、`mini_ed01/expected/` 的 m4–m8 金标、`verify.sh` 扩项与篡改矩阵、`fixture_ingest` 灌入 m1–m8。

`impl-00/10` 完成判据（本包首纵切唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
W=docs/blackbox-spec-rework/work-items/impl-00-interfaces
python3 $W/check_interfaces.py; echo exit=$?                                    # exit=0，末行 I00-IF SUMMARY pass=N fail=0
python3 -m unittest discover -s $W/tests -t $W 2>&1 | tail -3                    # OK
git status --short | grep -vE "^(\?\?| M) docs/blackbox-spec-rework/work-items/impl-00-interfaces/"   # 空（只写本目录）
git diff --check                                                                 # 无输出
```

`INTERFACES.md` §4 登记完成后，impl-04 前置「INTERFACES §4 已含 D4 六个新类型」与 impl-03 §4 D-09 的 `gate_results`/`validation_package` 提名即满足。

## 2. 依据（只读来源，行号基于当前文件）

- 裁决 `docs/blackbox-spec-rework/G7-RULINGS.md`：§1 原则 P1–P9；§2 impl-04 裁决表（D1–D6，含 D4 新类型）；§9 impl-00/impl-03 的 23 条（本 README §4 取其中与 impl-00 相关的 1–17 条）。
- `G7-PLAN.md`：W2-C 写范围（schemas + fixture，独占）已按 §9 裁剪为仅 `INTERFACES.md` 闭集登记。
- 规格 `openspec/learn-system-blackbox-architecture.md`（共 1001 行）：§5 队列 96–130；§6.1 EditionRun 136–151；§6.2 ReleaseRun 153–175；§7/§7.1 接口 177–226；§8 信封 228–251；§8.1 标识 253–329；§8.2 状态/审核类型/错误码 331–440；§9–§16 各模块 442–815；§17/§17.1 事务与 Checkpoint 836–846；§19.0 判据 899–918；§20 933–947；§22 首纵切 958–1001。
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §3 消费级别 38–46、§4 G1–G7 48–99、§6 行为场景 113–124。
- `pipeline/schemas/core/SCHEMA.md` §2 provenance 21–30、§4 assertions 44–66；`openspec/id-prefix-registry.md` §3.1–§3.4 20–63、§4 90–97。
- `openspec/schemas/`：`stage_package.schema.json`（payload 22–24；counts 59–65）、`artifact_ref.schema.json`（26–29）、`step_request/step_result.schema.json`、`verify.sh`。
- `pipeline/ledger/`：`fixture_ingest.py`（STAGES 40、STAGE_OUTPUT_TYPES 43–47、任务 167–214、Checkpoint 217–252、ingest 255–412）；`service.py`（RUN_ARTIFACT_TYPES 66、create_processing_run 319–345、register_stage_package 718、human_event 824/922–930、write_checkpoint 1364–1377）；`store.py`；`ids.py` PATTERNS 14–34。
- `pipeline/corpus_compiler/step.py`（m3 实际 artifact_type 87/159/182/200/215/227/247/373）；`work-items/impl-02-corpus/act/01.yaml` R1–R8、`act/03.yaml` 17–65。
- fixture `pipeline/corpus/_fixture/mini_ed01/`：`manifest.yaml`、`spans.yaml`、`expected/m1..m3`、`verify.sh`、`tools/build_fixture.py`、`source/transcript_v1.md`。
- 定稿输入：`work-items/impl-04-dataset/`（提交 `2e4f9a7`：README §4/§6/§7、ACT.yaml、act/*.yaml 的 artifact_type 与消费键）；`work-items/impl-03-validation/ACT.yaml` 与 `act/*.yaml`（只读，取 `gate_results`/`validation_package` 与输入边界；`validator_report` 已按 §9.1 第 24 条废弃，复用 `validation_report`）。
- 模板 `work-items/impl-02-corpus/`（README、BDD、TDD、ACT.yaml、PROMPT-J3.md、ACCEPTANCE.md）。

**起草时实测（2026-09-11/12，本机）**：`run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`；`m3-coverage.sh` exit 2；fixture `verify.sh` 8 项 PASS + `FIXTURE OK`；生成器重放 `diff -r` 无输出。

## 3. 范围

**本定稿轮（W2-C1）**只写本目录：`README.md`、`INTERFACES.md`、`FIXTURE-PLAN.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/00–10.yaml`、`PROMPT-C1.md`、`ACCEPTANCE.md`。

**首纵切 ACT（`impl-00/10`）执行时写**（`scope.write` 精确边界）：

- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`（§4 闭集登记 + 各章节裁决对齐）；
- 本目录：`check_interfaces.py`、`tests/__init__.py`、`tests/test_check_interfaces.py`。

**禁止**：改规格正文与 `id-prefix-registry.md`；改 `openspec/schemas/**`（四份 L0 Schema 与 `verify.sh` 一字不动）；改 `pipeline/corpus/_fixture/**`、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`openspec/acceptance/**`；改 `HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、`G7-PLAN.md`、`G7-RULINGS.md`、其他 work-items；新增依赖；新增 ID 前缀（P8）；调用模型 API（P6）；执行者写台账或 `ACCEPTED`。

## 4. 主 Agent 决定（执行者不重议）

本节取代原 §4 的 17 条待裁决清单；全部由主 Agent 裁决（`G7-RULINGS.md` §9 第 1–17 条），理由随条列出。未单列的细节默认采纳草稿推荐。

| # | 原条目 | 决定 | 说明 |
|---|---|---|---|
| 1 | D-01 前十页无规则正文，FactSet 匹配无宿主 | **首纵切不做 FactSet 匹配** | §22.2 该项判 BLOCKED；扩页宿主纵切后再议（P1）。m4 金标只取目录型直接主张的设想一并推迟。 |
| 2 | D-02 ↔ impl-03 D-01 M5 冻结输入边界 | **采纳 impl-03 `corpus_only`** | M5 冻结 M3 包及其血缘输入（含 M3 自身冻结的 M1/M2），impl-03 为 17 个修订；impl-00 对齐，放弃原「6 个修订」推荐（P1）。 |
| 3 | D-03 首纵切是否含 M7、M8 读什么 | **不采纳推荐** | M7 不进首纵切；M8 按 §2 D1-A 尾链只读 M3 包与页图（SourceSpan→SourceAnchor→OcrPage→SourceAsset 四段），知识链前三段 `not_compiled`。 |
| 4 | D-04 ReleaseRun 归属 | **采纳推荐** | 首纵切单 Part，`edition_part_id` 取该 Part；跨 Part Release 纵切后改 Ledger 再议。 |
| 5 | D-05 阶段 payload 入 Schema | **不采纳** | P3：首纵切不新增 `openspec/schemas/` 文件；payload 结构以代码内草案契约（`schema_version: "0.1.0-draft"`）表达。 |
| 6 | D-06 ↔ impl-03 D-13 金标投影与对抗输入 | **采纳推荐** | 身份归一化投影（UUID 家族一致重命名后比对）；对抗输入用 mock compiler 构造 sealed 错误包。 |
| 7 | D-07 UUID 金标确定性 | **采纳推荐** | 生产 `uuid4`；金标比对前身份归一化，不在生产代码写常量 ID（纵切后落实到金标时）。 |
| 8 | D-08 ↔ impl-03 D-11 无前缀对象与返工任务身份 | **采纳推荐** | 不新增前缀（P8）；EvidenceLink 内嵌复合键，Proposal/CorrectionRequest/ReworkImpactReport 以 `art_`+`rev_` 为身份；返工任务以 `(rework_stage, validator_id, check)` 聚合。 |
| 9 | D-09 ↔ impl-03 D-04/05/08/12 blocked 放行等 | **采纳推荐** | `INTERNAL_DEMO` 下 `failed=0` 放行、blocked 逐项披露；`DEV_SEARCH`/`PUBLIC_RELEASE` 下 blocked 视同 failed。 |
| 10 | D-10 ↔ impl-03 D-09 M5 类型与 ValidationPackage 结构 | **采纳** | `gate_results`、`validation_package` **提名入 §4 闭集**（P2）；结构为代码草案（P3），不新增 Schema 文件。 |
| 11 | D-11 M4 模型调用 | **推迟** | M4 不在首纵切（P6）；录制回放/真实调用开关归属留到对应波次。 |
| 12 | D-12 ↔ impl-03 D-02 quote hash 归属 | **采纳** | M5 按 `sha256(quote)` 复算，不改 M3 `spans.yaml`（P9）；M4 写入 evidence 的 `quote_sha256` 待 M4 落地。 |
| 13 | D-13 ↔ impl-03 D-13/14 热点文件写权与只读查询 | **采纳** | `fixture_ingest.py` 首纵切不改（P9）；Ledger 读优先用 `LedgerReader` 公开方法，缺口处允许 `reader.store.conn` 只读 SELECT，并在本 README §5.2 登记缺口清单，供 impl-08 补读接口。 |
| 14 | D-14 ReviewDecision verdict | **推迟至 W4** | M6 不在首纵切；verdict 闭集与 content_status 迁移届时单独裁。 |
| 15 | D-15 首纵切子包范围 | **以 impl-04 定稿为准** | 对齐 `2e4f9a7`：首切片 = `SourceAssetPack` + `EvidenceMapPack`（尾链四段）+ `ReleaseManifest` + `ValidationReport` + `PublicationPackage`；`QueryContractPack`/`SearchIndexPack`/`KnowledgeDataPack` 纵切后。 |
| 16 | D-16 SourceAssetPack 字节 | **不采纳** | 按 impl-04 D2 与规格 §16:723，页图字节登记进 Ledger（薄 M1 `source_asset_page`，`rights_scope=internal`）；fixture 内不出现图像。 |
| 17 | D-17 ↔ impl-03 D-10 错误码闭集 | **采纳推荐** | 映射现有 9 码，找不到合理映射的填 `code: null` 并以 snake_case 检查名区分；缺口清单见 §5.2。 |

**与 impl-03 的其余对账项**（`G7-RULINGS.md` §9 第 18–23 条，属 impl-03 定稿范围，本包只登记接口影响）：D-03 四点坐标 vs `box`（采纳推荐）；D-06 G1 重放（只有 `replay.py` 可 import M3 compiler）；D-07 目标消费级别（配置带 `target`，报告三级都算）；D-08 Gate 未通过时 M5 StepRun 终态（跑完即 `succeeded` 并封存报告）；D-12 G4/G5/G6（`not_evaluated`，验收判 BLOCKED）；D-15 上游终态过滤（P5）。

## 5. 纵切后待办（DEFERRED）

首纵切（§1）不执行下列工作。原 `act/00–09.yaml` 文件保留，`ACT.yaml` 中逐条标 `status: DEFERRED` 并移出 `executor_groups`，内容不得删除。

| ACT | 标题 | 推迟到 | 理由 |
|---|---|---|---|
| `impl-00/00` | 契约检查器 `check_i00.py`（C00 基线 + C01–C09 逐 ACT 终态） | 与 Schema/金标同批（W3 后） | 检查器判定 C01–C09 依赖 act/01–09 的产物 |
| `impl-00/01` | `contract_common` + `candidate_set` Schema + 样例 | impl-08 Contract Registry（W4-I） | P3：首纵切不新增 `openspec/schemas/` 文件 |
| `impl-00/02` | `gate_results`/`review_decision`/`reviewed_edition`/`rework_impact_report` Schema | 同上 | P3；§9 第 5 条不采纳 |
| `impl-00/03` | `canonical_snapshot`/`release_manifest`/`knowledge_data_pack`/`evidence_map_pack` Schema | 同上 | P3 |
| `impl-00/04` | `source_asset_pack`/`anchor_contract_pack`/`query_contract_pack` + `stage_payload_m4..m8` Schema | 同上 | P3；§9 第 5 条明确「首纵切不新增 `openspec/schemas/` 文件」 |
| `impl-00/05` | m4（candidate_set+包）/ m5（gate_results+包）金标 | 纵切后（M4/M5 实现同期或其后） | §9「impl-00 的首纵切裁剪」；impl-03/impl-04 verify 未引用 `expected/` 金标 |
| `impl-00/06` | m6（5 决定+reviewed_edition+包）/ m7（canonical_snapshot+包）金标 | 纵切后 | M6/M7 不在首纵切 |
| `impl-00/07` | m8 七子包 + release_manifest + m8 包 + `expected/SHA256SUMS` | 纵切后 | impl-04 不消费 `expected/` 金标 |
| `impl-00/08` | `verify.sh` 由 8 扩到 12 项 + 20 例篡改矩阵 + fixture README | 纵切后（金标落地后） | 依赖 act/05–07 金标 |
| `impl-00/09` | `fixture_ingest` 灌入 m1–m8（8 StepRun / 2 ProcessingRun / 30 Checkpoint） | 纵切后 | §9 第 13 条：`fixture_ingest.py` 首纵切不改（P9） |

细则随附：

- **m4/m6/m7 金标、`stage_payload_m4..m8` Schema、`fixture_ingest` 灌入 m1–m8（原 act/09）一律推迟**（`G7-RULINGS.md` §9 明列）。
- **FIXTURE-PLAN.md、TDD.md、BDD.md** 中被推迟的部分移入各自的「纵切后」小节，不删除；首纵切相关小节保留并与 `impl-00/10` 对齐。
- **`openspec/schemas/` 与 fixture 在首纵切内一字不动**：M5/M8 新类型只登记到 `INTERFACES.md` §4，内容结构以代码草案表达（P3）。

### 5.1 §4 闭集首纵切新增项（`impl-00/10` 登记内容）

- **M8**（`G7-RULINGS.md` §2 D4，impl-04 README §4 D4）：`source_asset_page`、`source_asset_register`、`source_asset_pack`、`evidence_map_pack`、`release_manifest`、`publication_package`。
- **M5**（§9 第 10 条）：`gate_results`、`validation_package`。
- 复用（不新增，但首纵切内首次以闭集形式确认）：`configuration`、`validation_report`、`step_log`、`failure_report`、`stage_package`、`source_manifest`、`ocr_page`、`ocr_page_set`、`human_event`、`corpus_batch`、`corpus_spans`、`coverage_report`、`corpus_package`。

### 5.2 缺口与已裁项（G7-RULINGS §9.1 第 24/25/26 条）

1. **已裁（§9.1 第 24 条）**：`validator_report` **不入** §4 闭集；impl-03 定稿（`1a189ae`）已改为复用通用 `validation_report`；首纵切 M5 新类型只有 `gate_results`、`validation_package`；§4 表残留的 `gate_report` 由 `impl-00/10` 删除。
2. **已裁（§9.1 第 25 条，按第 13 条）**——Ledger 只读查询缺口清单（本清单为唯一登记处，供 impl-08 补读接口）：impl-03 `act/04.yaml:16` 需 `frozen_inputs`、`artifacts.artifact_type`、`stage_packages` 三类元数据；impl-04 `act/04.yaml:14` 需按 `step_run_id` 取 sealed StagePackage。`LedgerReadMixin`（service.py 111–164）无对应公开方法，首纵切允许只读 SELECT；impl-08 以公开读方法补齐后回改调用方。
3. **已裁（§9.1 第 26 条，按第 17 条）**——错误码缺口：impl-03 的 `count_mismatch`、`unproofread_glyphs`、`replay_tool_mismatch` 在现有 9 码中无对应，填 `code: null`，缺口并入本清单；错误码闭集扩充随 impl-08 Contract Registry。

## 6. 与其他并行草案的接口假设（摘要；逐项见 `INTERFACES.md` §6）

1. 首纵切内各实现包**不再**以 `ingest(fixture, stages=前缀)` 灌入 m4–m8 金标（金标推迟）：impl-03 用 `ingest(stages=("m1","m2")) → run_m3 → run_m5` 真实链路；impl-04 用 `run_m3` 真实产出 + 薄 M1 页图登记。
2. 各阶段产出「主内容 Artifact + 阶段输出索引 Artifact」两个修订，StagePackage 的 `output_artifacts[0]` 指向索引（纵切后正式化）。
3. m4–m8 的 payload 只含 `*_revision_id(s)` 与标量，不含 `*_path`；m1–m3 保持现状，下游不得依赖 `*_path`。
4. M5 冻结 M3 包及其血缘输入（17 个修订，`corpus_only`），接收 `target_consumption_level`；M8 冻结 m7 Snapshot 由 M3 包替代（D1-A 尾链）+ m3 `corpus_spans` + m1 `source_manifest` + 薄 M1 页图。
5. m7/m8 属 `release_run`，`edition_part_id` 取首个 Part（D-04；M7 纵切后）。
6. ReviewDecision 即 `human_event` 修订，内容符合代码草案契约，并带 `decision_type`（D-14 推迟）。
7. G 代号只用 G1–G7；阶段 Gate 称「M<n> Gate」，检查名 snake_case；错误码只用 9 个（§5.2 列缺口）。
8. 生产代码经 Contract Registry `load_schema(name)` 加载新 Schema（纵切后，P3/§9 第 13 条）；不改 Ledger 私有 loader。
9. **上游只认 `succeeded`**（P5）：M5/M8 解析上游 StagePackage 时只接受所属 StepRun `succeeded` 的包；M5 特例（§9 第 21 条）另须 `validation.passed == true` 才能被下游消费。

## 7. 目录规划

```text
docs/blackbox-spec-rework/work-items/impl-00-interfaces/
  README.md  INTERFACES.md  FIXTURE-PLAN.md  BDD.md  TDD.md  ACT.yaml
  PROMPT-C1.md            （W2-C1 新建：执行 impl-00/10 的派发提示词）
  ACCEPTANCE.md           （W2-C1 新建：§0–§4 清单；§5 验收记录由主 Agent 填写）
  act/00.yaml … act/09.yaml    （保留原文件，ACT.yaml 标 DEFERRED）
  act/10.yaml                  （首纵切保留 ACT）
  check_interfaces.py          （impl-00/10 新建：§4 闭集登记检查器）
  tests/test_check_interfaces.py（impl-00/10 新建）

纵切后（§5）才落地，首纵切内不存在：
  openspec/schemas/*.schema.json + examples/     （act/01–04）
  pipeline/corpus/_fixture/mini_ed01/expected/m4..m8 + SHA256SUMS（act/05–07）
  pipeline/corpus/_fixture/mini_ed01/verify.sh（12 项）+ fixture_mutations.sh（act/08）
  pipeline/ledger/fixture_ingest.py（GOLDEN_STAGES）+ test_ingest.py（act/09）
```
