# impl-03：M5 Automatic Validation（§13）首切片——G1–G3 与 glyphbox_level 证据门禁

状态：`DRAFT`（起草 Agent 产出；§4 待主 Agent 裁决，各 ACT 暂按「推荐」项撰写）

前置：impl-02 `ACCEPTED`（含 J3 返工 act/05：冻结输入字节校验、页登记与终态严格比对、begin 后异常封存）。当前工作树 `pipeline/corpus_compiler/step.py` 仍是返工前版本（第 441–445 行 `pass`、第 432 行 `files_hash`），本包不得在其之前派发。

## 1. 目标

在 `pipeline/validation/` 落地规格 §13 / §13.1 的 M5 首切片：从 Artifact Ledger 冻结读取已 `succeeded` 的 M3 结构层产出（m3 StagePackage、`corpus_package`、`corpus_spans`、`coverage_report`、批次与 M3 自身冻结的 M1/M2 输入），以**确定性、不改输入、fail-closed** 的 14 个已注册 Validator 执行 G1（来源与可重放性）、G2（全书覆盖）、G3（身份、引用与证据锚点，含 `glyphbox_level` 证据门禁），每个 Validator 一个 task、一个 StageCheckpoint，产出 `gate_results`（内容）+ `validation_package`（阶段输出索引）+ m5 StagePackage；并新建 §19.0 已登记的判据脚本 `openspec/acceptance/m5-evidence-gate.sh`。

M4 未实现，本切片 `scope: corpus_only`：依赖 Candidate 的 G3 子项（evidence 位于所声明 span 内、direct proposition 忠实性）与 G4/G5/G6 记为 `not_evaluated`，验收脚本报 BLOCKED；G7 按 §13.1 延至 M8。

完成判据（本批唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
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
| `g3_strict_offset_quote` / `quote_hash_not_stored` | 1（整份 `corpus_spans`） | warning / error / error | `git grep -n quote_hash` 全仓 0 处 |
| `g3_glyphbox_anchor` / `glyph_text_misaligned` | 2（s03：文本 `影宋刊本影印`、字框拼接 `宋刊本影印`；s04：文本末字 `藏` 无字框） | warning / error / error | 43 条 Span 中 2 条字框拼接 ≠ 文本 |
| 其余 11 个 Validator | 0 | — | M3 结构 Gate 已独立判过；M5 重算（14 个注册 Validator 中 3 个有发现） |

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
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md`：§3 三级消费：40–46；G1：50–55；G2：57–62；G3：64–70
- `openspec/id-prefix-registry.md`：只引用已登记前缀：93（本包不新增前缀）
- `pipeline/ledger/`（impl-01 已验收，只调用、不改）：`service.py` `LedgerReadMixin` 111–164、`_configuration_stage` 295、`begin_step_run` 405、`put_artifact` 442、`put_run_artifact` 528、`register_stage_package` 718、`record_transformation` 777、`finish_step_run` 1132、`fail_step_run` 1187、Checkpoint stage 必须等于 StepRun stage 1257、`write_checkpoint` 1364、`read_object` 1606；`store.py` `stage_packages` 71–75、`step_runs` 88–103、`frozen_inputs` 119–124；`errors.py` `ERROR_CODES` 11–23
- `pipeline/corpus_compiler/`（impl-02）：`step.py` run_m3 产出布局（以 J3 返工后为准，act/03 contract 第 30–65 行）；`compiler.py` `compile_structural`（仅供 G1 重放调用）；`__init__.py` `M3_TOOL`/`M3_TOOL_VERSION`
- `pipeline/corpus/_fixture/mini_ed01/`：`manifest.yaml`（`source_assets` 宽高 1203×1654）、`pages/*.json`、`anomalies.yaml`、`spans.yaml`（sha256 `ec6d77b9…44ef`）、`verify.sh`
- 模板：`docs/blackbox-spec-rework/work-items/impl-02-corpus/`（README、BDD、TDD、ACT.yaml、act/01、03、04）
- 并行草案（对账用，未定稿）：`impl-00-interfaces/README.md` D-02、D-09、D-10、D-12、D-17；`impl-06-review/README.md` §5.1

## 3. 范围

写（全部新建）：`pipeline/validation/**`、`openspec/acceptance/m5-evidence-gate.sh`。

禁止：改规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`openspec/acceptance/run_all.sh` 与 `m3-coverage.sh`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、任何台账或 ACCEPTANCE 文件；新增依赖（只用标准库 + PyYAML + jsonschema）；新增 ID 前缀（`validator_id`、`task_id` 是任务标签，不是登记册 ID）；调用任何模型 API；生产代码读 fixture 路径或工作目录文件（只读 Ledger 冻结修订，元数据查询允许经 `reader.store.conn` 只读 SELECT，沿用 impl-02 inputs.py 先例）。

独立性纪律：
1. Validator 只读取冻结修订，不修改、不重写、不「修正」任何输入（§13:580）；
2. `g2_coverage.py`、`g3_evidence.py` 不得 import `pipeline.corpus_compiler` 的任何模块（防止与 M3 同错同过）；唯一允许 import `pipeline.corpus_compiler.compiler` 的是 `replay.py`（G1 重放按定义需执行生产工具）；
3. `acceptance.py` 不得 import `pipeline.validation` 的 `g1_source`、`g2_coverage`、`g3_evidence`、`replay`，判定一律自行重算；
4. fail-closed：`g1_frozen_bytes` 出现任何 error 发现，其余 13 个 Validator 记 `skipped_fail_closed`；Validator 自身抛异常记 `errored`；两者均计入 `failed_task_count`，任何级别都不得判 `passed`（§13:608）。

本批不改 `run_all.sh`：§20 没有任何一条会因 M5 首切片单独落地而由 BLOCKED 变 PASS——20.1 仍缺 Local Orchestrator 与 M4/M6 Gate，20.4/20.8 仍缺 M8。M5 的 `gate_results` 是 20.4（候选与校验可追溯）、20.8（EvidenceMapPack 证据完整性）的前置输入。

## 4. 待主 Agent 裁决

每条给 2–3 个选项；「推荐」仅为起草意见，不是定案。各 ACT 按推荐项撰写，`ACT.yaml` 的 `decisions_required` 注明依赖。

对账（与 impl-00 §4 去重，同一问题只需一次裁决，两边取同一选项）：D-01↔impl-00 D-02；D-02↔impl-00 D-12；D-04/D-05/D-08/D-12↔impl-00 D-09；D-07↔impl-00 D-02；D-09↔impl-00 D-10；D-10↔impl-00 D-17；D-11↔impl-00 D-08；D-13↔impl-00 D-13；D-14↔impl-00 D-13；D-15↔impl-00 I-13（INTERFACES §1.1 通用规则）。本节 D-03、D-06 为 impl-03 独有。

### D-01 M4 缺席时 M5 的输入边界

§13（576–612）未列 M5 输入；§6.1（141–147）把 ValidationPackage 排在 CandidatePackage 之后，§14（618）说明 M6 同时读 Candidate/Validation/Corpus；G1–G3（588–590）又要核对页哈希、覆盖与字框。M4 目前没有实现，也没有期望产物。

- A（推荐）：首切片 `scope: corpus_only`。冻结 m3 包与 M3 全部输出，外加 M3 自身冻结的 M1/M2 修订，共 17 个。依赖 Candidate 的检查记 `not_evaluated`，验收报 BLOCKED。M4 落地后升级为 `corpus_and_candidates`：追加冻结 `candidate_package` 和逐对象 `knowledge_candidate`，已有 14 个 Validator 不变。理由：G1–G3 的主体（全链哈希、覆盖、锚点）现在就能在真实数据上判定，且不伪造知识内容。
- B：在 mini_ed01 增补 `expected/m4` 金标候选，经 `fixture_ingest` 注入 m4（要改 fixture、`verify.sh`、`fixture_ingest.STAGES`，归 impl-00 D-13），M5 首切片同时实现证据范围检查。
- C：等 M4 首切片完成后再做 M5。与 §22.3（991）首纵切顺序冲突。
- 对账：impl-00 D-02 推荐冻结 m4 两个修订加 m3、m2、m1 各 1 个（共 6 个），本包比它多冻结页修订、批次、配置与 m3 包，原因是 G2 重算覆盖、G1 重放、G3 引用闭合需要这些对象的**内容**（§7:207 禁止经血缘反查读取未冻结修订）。建议 impl-00 采纳本包的冻结集合，作为 M5 的 M3 侧子集。

### D-02 quote hash 的归属

§11.1（527–528）规定两档证据级别都要求 span 带 quote hash，G3（600、标准 67）要求「quote hash 锚点对账」。但 `spans.yaml` 与 run_m3 都没有该字段（`git grep quote_hash` 为 0）。

- A：M3 在 Span 中新增 `quote_sha256`。需要重建 fixture 金标（`spans.yaml` 的 sha256、`expected/m3` 的 `content_sha256`、`verify.sh`），并返工已验收的 impl-02。
- B（推荐）：首切片由 M5 按 `sha256(block[start:end] 的 UTF-8 字节)` 派生对账；若 Span 自带 `quote_sha256` 则逐条比对，不符判 TXT_001。未存储记一条 `quote_hash_not_stored`（SCH_001），严重度 `{INTERNAL_DEMO: warning, DEV_SEARCH: error, PUBLIC_RELEASE: error}`，验收脚本报 `BLOCKED quote_hash_stored`。与 impl-00 D-12 A 一致（quote hash 由 M4 写入 evidence、M5 复算）。
- C：未存储即判 error（三级都是）。首纵切会在 M5 断链。

### D-03 「四点坐标」与现有 `box{x,y,w,h}`

§11.1（528）写「OCR 字框范围（四点坐标）」；fixture 全部字框与行框都是轴对齐的 `{x,y,w,h}`，`angle` 全为 `0.0`。§16（714）要求坐标与页图像素同源、可以换算。

- A（推荐）：`angle == 0` 时轴对齐框与四点坐标等价，`g3_glyphbox_anchor` 检查 `w>0`、`h>0`、`x≥0`、`y≥0`、`x+w≤width`、`y+h≤height`（宽高取 manifest `source_assets`）。`angle != 0` 且无四点字段时判 `anchor_field_missing`。实测 fixture 越界为 0。
- B：强制四点字段，现有数据全部 FAIL，需要 M2/M3 改输出。
- C：修订规格措辞为「矩形框或四点坐标」（规格变更工作包）。

### D-04 「未决字符」的定义与分级严重度

G1（598、标准 55）要求 PUA、乱码占位与未决字符为 0，但 §8.2 没有定义 OCR 字框的状态枚举。fixture 实测：5 个 `status: unrecognized`、`char: ""` 的字框落在 s03/s04；225 个 `status: pending`（未人工校对）；7 个 `is_rare`。标准 §3（42）规定 INTERNAL_DEMO「已知缺陷必须披露」。

- A：`pending` 和 `unrecognized` 在三级都判 error。fixture 在 M5 全部 FAIL，首纵切断链。
- B：只有 `unrecognized`、空字符、PUA、U+FFFD、`□`、`〓` 算未决，三级都判 error。fixture 仍然 FAIL（5 字）。
- C（推荐）：按级别分：PUA/U+FFFD/控制符/占位符在文本中出现，三级 error；`unrecognized` 或空字符字框为 `{warning, error, error}`；`pending` 为 `{info, warning, error}`；配置 `approved_uncertain_chars`（首切片为空）登记经批准的不确定字。理由：M5 同时给出三级结论，INTERNAL_DEMO 如实披露、不阻断，DEV_SEARCH/PUBLIC_RELEASE 按 fail-closed 拒绝。与 impl-00 D-09 A 的分级放行一致。

### D-05 字框序列与 Span 文本不对齐

实测 43 条中 2 条：s03 文本 `影宋刊本影印`，非空字框拼接为 `宋刊本影印`，另有 3 个空字框；s04 文本末字 `藏` 无字框，另有 2 个空字框。M3 Gate `glyphbox_anchors` 只比较锚点与页 JSON 是否一致，不比较锚点与文本是否对齐，所以放行了。

- A：三级 error。fixture 在 M5 FAIL，需返工 M2 后重建金标。
- B（推荐）：`glyph_text_misaligned`（TXT_001）严重度 `{warning, error, error}`，逐条列出主体 Span 与差异。它与 D-04 合在一起，决定 PUBLIC_RELEASE 能否达到真实 `glyphbox_level`。
- C：不检查。§16（705–713）的高亮链会静默错位。

### D-06 G1「重放一致性」的实现方式

标准 G1（53）要求相同输入与工具版本重放后哈希一致，但 Validator 不应与 M3 共享代码（防止同错同过）。

- A（推荐）：只有 `replay.py` 可以 import `pipeline.corpus_compiler.compiler.compile_structural`。先比较 m3 配置里的 `tool`/`tool_version` 与已安装的 `M3_TOOL`/`M3_TOOL_VERSION`，不同即 `replay_tool_mismatch`（三级 error），相同再重放并比较字节。G2/G3 独立重算，禁止 import M3。
- B：子进程在临时 Ledger 上重跑 `python -m pipeline.corpus_compiler`。更慢，还要复制冻结输入。
- C：首切片不重放，报 BLOCKED。违反 608 的 fail-closed。

### D-07 目标消费级别从哪里来、判几级

§13.1（590）用「目标消费级别」判定 evidence_level，§16（666）只规定它是 M8 的显式输入。

- A：M5 配置只带 `target_consumption_level`，只判这一级。
- B（推荐）：配置带 `target_consumption_level`（默认 `INTERNAL_DEMO`，§22.1:968），决定 `gate.passed`；同时对三级都计算 `level_verdicts`，写进 `gate_results` 与 m5 StagePackage payload。理由：M8 可以不重跑 M5，直接拒绝 `level_verdicts[目标] != passed` 的输入，符合 §16（668）的 fail-closed。
- C：M5 不接收级别，由 M8 自行判定 evidence_level。与 590 的 M5 工位冲突。

### D-08 Gate 未通过时 M5 StepRun 的终态

M3 选择的是「Gate 失败 → StepRun failed、不产出 StagePackage」（impl-02 act/03 第 10 步）。但 M5 的失败项和返工任务本身就是 M6 要读的业务产物（§14:618「返工项」）。

- A（推荐）：14 个 Validator 全部执行完即 StepRun `succeeded`，并照常封存 `gate_results` / `validation_package` / m5 StagePackage，`validation.passed` 与 `gate.passed` 取目标级别的结论。只有输入契约或内部异常才 `failed`。下游（M6/M8）必须检查 `gate.passed`，impl-06 §5.1 已按此假设。
- B：`gate.passed=false` 时 StepRun `failed`，`gate_results` 作为失败报告封存，不产出 m5 StagePackage。M6 读不到返工任务。
- C：StepRun `succeeded`，但 `gate.passed=false` 时不注册 StagePackage。§6.1（149）「StageManifest 封存」语义含糊。

### D-09 ValidationPackage 结构、artifact_type、是否入 Schema

§13（606）只列六要素，没有 Schema；`artifact_type` 只有正则约束，没有闭集。`validation_report` 已有两种内容（fixture_ingest 与 run_m3），见 impl-00 D-10。

- A（推荐）：不新增 Schema，结构由 act/05 contract 冻结并用测试逐键断言。类型采用 impl-00 D-10 A 命名：`gate_results`（主内容）、`validation_package`（阶段输出索引，键名兼容 impl-06 §5.1 的 `gate{passed,severe_error_count,failed_task_count,pending_rework_count}` 与 `candidate_package_revision_id`，首切片为 `null`）、每 task 一个 `validator_report`；`validation_report` 只作通用自检摘要。
- B：新增 `openspec/schemas/gate_results.schema.json` 与 `validation_package` 的 payload Schema（归 impl-00 ACT 01–04）。本包等待。
- C：全部内容直接放进 m5 StagePackage `payload`。payload 过大，也不能单独封存和引用。

### D-10 错误码闭集不足

§8.2（368）规定表外码无效。本包的检查项中，`count_mismatch`、`unproofread_glyphs`、`replay_tool_mismatch` 在 9 码里找不到对应。

- A（推荐）：按 impl-00 D-17 A 映射（引文、offset、锚点不符 → TXT_001；悬空、断链、缺失 → REF_001；重复 → ID_002；格式 → ID_001；级别不足、非法枚举 → SCH_002；缺必填字段 → SCH_001；哈希 → SRC_003；对象缺失 → SRC_001；缺证据 → SEM_001）。上面三项找不到合理映射，填 `code: null`，靠 snake_case 检查名区分；act/00 登记完整的「检查名 → 码」表，测试逐项断言。
- B：三项也强行映射（`count_mismatch → REF_001`、`unproofread_glyphs → TXT_001`、`replay_tool_mismatch → SRC_003`）。统计口径失真。
- C：扩展 §8.2 码表（规格变更，需用户确认）。

### D-11 返工任务的身份与指向阶段

§13（606）要求「返工任务」，但没有登记前缀（id-prefix-registry:93 禁止发明前缀）。

- A（推荐）：不设标识。按 `(rework_stage, validator_id, check)` 聚合并排序，`subjects` 列出主体（`entity_id` 可为 `span_id`，外加 `artifact_revision_id`、`page`）。`rework_stage` 取 `m2`（字符、页登记、终态）或 `m3`（其余）。只把目标级别为 error 的发现转成返工任务。
- B：用任务标签 `m5rw_<3位>`（与批号同样视为标签）。易被误当 ID。
- C：登记新前缀（需用户确认）。

### D-12 G4/G5/G6 与 Candidate 子项的披露；G6 的 M5/M8 分工

§13.1（603）把 G6 拆成「M5：规则可执行性、FactSet AST 条件完整性」和「M8：索引产出后复验」，但边界没有写清。

- A（推荐）：首切片在 `gate_results.not_evaluated` 中逐条写明 `{gate, check, reason}`，验收脚本报 BLOCKED（行名 `M4 Knowledge Extraction`）。分工建议：M5 负责每条 ApplicabilityRule 的 AST 合法性、operator 闭集、条件引用的 FactSet 字段存在性与可求解性；M8 负责 RuleIndexPack/SearchIndexPack 与 KnowledgeDataPack 的一致性、「全部且仅返回适用规则」的正负例查询。写入 M4/M8 草案对账。
- B：从脚本中省略这些行。exit 0 会冒充门禁完成（假绿）。
- C：报 FAIL。首切片永远 exit 1，无法区分真缺陷。

### D-13 验收脚本如何构造「M3 同错同过」的对抗输入

M5 的价值在于抓出 M3 Gate 放过的错误，但 M3 在真实链路上会拒绝错误输入。

- A（推荐）：`acceptance.py` 在每个对抗场景的独立临时 Ledger 上，用 `unittest.mock.patch` 同时替换 `pipeline.corpus_compiler.step.compile_structural`（返回篡改后的结果，字节经 `corpus_compiler.serialize.dump_yaml` 重算）与 `pipeline.corpus_compiler.step.evaluate_structural`（返回 `structural: passed`）。这样得到布局完全真实的 sealed 错误 m3 包，再断言 M5 命中。
- B：`acceptance.py` 用 Ledger 公开写接口手工伪造一个 M3 StepRun。要复刻 run_m3 的约 100 行布局，容易漂移。
- C：对抗只放在单元测试里，验收脚本只跑正例。§19.0 判据证明不了「能阻断」。

### D-14 Ledger 元数据查询没有公开读方法

M5 需要 `frozen_inputs`、`artifacts.artifact_type`、`stage_packages` 三类元数据；`LedgerReadMixin`（111–164）没有对应方法。

- A（推荐）：沿用 impl-02 `inputs.py`（101–108）先例，经 `reader.store.conn` 执行只读 SELECT，集中写在 `inputs.py` 的三个私有函数中。
- B：先给 `LedgerReadMixin` 加 `list_frozen_inputs` / `artifact_type_of` / `get_stage_package`（改 impl-01 已验收代码，另立工作包）。
- C：从 StepRun `request_json` / `result_json` 解析修订号，类型靠内容推断。不可靠。

### D-15 上游 StagePackage 的 StepRun 终态过滤（必须只接受 succeeded）

依据：impl-02 ACCEPTANCE §5.3 登记的下游约束；规格 §17 事务序列（836）。
背景：在重跑或异常注入场景下，上游 StepRun 可能在封存 StagePackage 之后因后续步骤抛异常而标记为 `failed`。当重跑成功后，Ledger 中可能存在多个同一 stage 的 StagePackage，其中属于未完成或失败 StepRun 的包依然存在。

- A（推荐）：M5 解析上游 StagePackage 时，必须显式校验其所属 `step_run_id` 的状态必须为 `succeeded`，只接受 `status == "succeeded"` 的包；若属于非 `succeeded` StepRun（如 `failed`、`running` 等），一律拒绝解析并抛出 `ValidationRefused`（输入契约拒绝），严禁消费失败运行遗留的包。
- B：只按 `stage_packages` 表中时间最新（或 revision_id 最新）取包，不反查 StepRun 状态。存在误读失败中间包的严重风险，违反 impl-02 验收结论。
- C：要求 Ledger 物理删除失败 StepRun 的 StagePackage。违反不可变账本设计与 §20 第 2 条「历史失败不被覆盖」。

## 5. 接口契约（供与 M3/M4/M6/M8 与 impl-00 草案对账）

### 5.1 上游输入契约（本包依赖）

> **核心约束（impl-02 ACCEPTANCE §5.3 登记）**：M5 解析上游 StagePackage 时**只接受 StepRun 状态 `succeeded` 的包**。若上游 StepRun 为 `failed` 或非 `succeeded`，一律拒绝解析并抛出 `ValidationRefused`。

| 来源 | 定位方式（只经 Ledger） | artifact_type / 对象 | 读取的字段 |
|---|---|---|---|
| M3 StepRun | `list_checkpoints(ep,"m3")` 最新项的 `step_run_id`；`get_step_run().status == "succeeded"`（必须为 succeeded） | `step_runs.request_json` / `result_json` | `configuration_artifact_id`、`input_artifact_ids`（顺序）、`technique_profile_id`、`output_artifact_ids`、`validation_report_ids` |
| M3 输出 | `result_json.output_artifact_ids` 按 artifact_type 各恰 1 个；对应 m3 StagePackage 归属的 StepRun 状态必须为 `succeeded` | `corpus_package`（JSON）、`corpus_spans`（YAML，impl-02 act/01 R7/R8 键序）、`coverage_report`（JSON）、m3 StagePackage（`stage_packages.stage == "m3"`） | `corpus_package.spans_revision_id`；spans 表头 `work, source_id, edition_part_artifact_id, evidence_level, content_status, span_count, batch_count`；Span 全部键；m3 包 `manifest.counts`、`content_sha256`、全部 ArtifactRef、`lineage` |
| M3 自检 | `result_json.validation_report_ids` 恰 1 个 | `validation_report` | 只冻结不解析 |
| M3 配置 | `request_json.configuration_artifact_id` | `configuration`（JSON） | `stage == "m3"`、`tool`、`tool_version`、`batch_size`、`gate_profile` |
| M3 批次 | 该 StepRun 的 m3 Checkpoint 链序 `completed_tasks` | `corpus_batch`（JSON 列表） | 批号与 Span 列表 |
| M1/M2（经 M3 冻结） | `frozen_inputs` 中 M3 StepRun 的行，按 `request_json.input_artifact_ids` 顺序 | `source_manifest`（YAML）、`ocr_page_set`（JSON）、`ocr_page` ×3、`human_event` ×1 | manifest `source_id, technique_id, edition_part.pages, source_assets[page,sha256,width,height]`；`ocr_page_set.ocr_pages[page,sha256]`、`terminal_states`；页 JSON `lines[id,box,text,angle]`、`chars[id,parent,char,box,status]`；人工事件 `page` |
| M2 Checkpoint | `list_checkpoints(ep,"m2")` 全链 | — | 页 → 修订、终态（与冻结 `ocr_page_set` 交叉核对） |

假设 M3 的 `ocr_page_set.ocr_pages` 为非空列表、每项含 `page` 与 `sha256`（impl-02 act/05 C2）。M3 语义层（impl-10）落地后，`gate_profile` 会升级，Span 可能分为结构层与语义层；本包按 `gate_profile == "structural_only"` 取结构层，遇到其他取值时判 `input_contract` 失败，不静默兼容。根据 impl-02 ACCEPTANCE §5.3，上游失败或重跑留下的未封存/归属失败运行的 StagePackage 坚决丢弃，只认 succeeded StepRun 的包。

### 5.2 本包内部对象

- **Finding**：`validator_id, gate, check, code(9 码或 null), severity{INTERNAL_DEMO,DEV_SEARCH,PUBLIC_RELEASE ∈ error|warning|info}, subject{entity_id, artifact_revision_id, page}, relation(null|artifact_ref|content_hash|anchor_image|batch_membership), rework_stage(m2|m3), detail`。
- **validator_report**（每 task 一个修订）：`validator_id, gate, version, task_status(succeeded|errored|skipped_fail_closed), checked{…计数}, findings[]`。
- **m5 StageCheckpoint**：`task_id = validator_id`；`completed_tasks[{task_id, artifact_revision_id: 该 validator_report, status: succeeded|failed, terminal_state: null}]`；`pending_queue` 为其后的 validator_id；`human_decisions: []`。

### 5.3 下游输出契约

- **`gate_results`（JSON，主内容）**：`schema_version:"1.0.0", scope:"corpus_only", target_consumption_level, validator_suite:"pipeline.validation", validator_version, validators[{validator_id,gate,version,task_status,report_revision_id}], gates{G1..G3: passed|passed_with_warnings|failed, G4..G6: not_evaluated, G7: deferred_to_m8}, passed_checks[validator_id], failures[Finding], warnings[Finding], broken_relations[{relation,subject,code,detail}], rework_tasks[{rework_stage,validator_id,check,code,subjects[]}], not_evaluated[{gate,check,reason}], level_verdicts{INTERNAL_DEMO,DEV_SEARCH,PUBLIC_RELEASE}, gate{passed,severe_error_count,failed_task_count,pending_rework_count}, counts{validators,findings,failures,warnings,broken_relations,rework_tasks,spans_checked,pages_checked}`。
- **`validation_package`（JSON，阶段输出索引）**：`schema_version, edition_part_id, technique_id, scope, target_consumption_level, validator_version, gate_results_revision_id, corpus_package_revision_id, corpus_spans_revision_id, m3_stage_package_id, m3_package_revision_id, candidate_package_revision_id(null), gate{…}, level_verdicts{…}`。
- **m5 StagePackage**：形状同 impl-02 act/03 第 13 步；`stage:"m5"`；`payload{validation_package_revision_id, gate_results_revision_id, scope, target_consumption_level, gate, level_verdicts}`；`manifest.input_artifacts` = 17 个冻结修订（m3 包用 `artifact_kind: stage_package`）；`output_artifacts=[validation_package]`；`counts{validators, findings, failures, warnings, rework_tasks}`；`content_sha256 = sha256(gate_results 字节)`；`validation{passed: gate.passed, report_artifacts:[validation_report]}`；`lineage.upstream_artifacts=[m3 包, corpus_package, corpus_spans]`；transformation `operation: validate_corpus`。
- **M6（impl-06）应读取**：`validation_package.gate.*`、`gate_results.failures/warnings/rework_tasks/broken_relations`。差异：impl-06 §5.1 假设的扁平 `entries[…result∈pass/warn/fail]` 在本包由 `failures`/`warnings` 表达（目标级别下），`info` 不下发；首切片 `candidate_package_revision_id` 为 `null`，M6 必须据此拒绝（没有候选包可审）。
- **M8（impl-04，尚无草案）应读取**：`level_verdicts[本次消费级别]` 必须为 `passed`，否则 fail-closed 拒绝；`validation_package.corpus_spans_revision_id` 必须等于 M8 冻结的 `corpus_spans`；`warnings` 进 ReleaseManifest `known_defects` 披露（与 impl-00 D-09 A 一致）。
- **M4（未起草）假设**：Candidate evidence 形如 `{source_span_id, start_offset, end_offset, quote_sha256}`，offset 相对 Span `text`（与 impl-06 §5.1 一致），M5 升级 `scope` 时新增 Validator，已有 14 个的 `validator_id` 不变。

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
  inputs.py          resolve_m5_inputs（Ledger 读）
  context.py         build_context（冻结字节 → raw/doc）
  package.py         assemble_gate_results / assemble_validation_package
  step.py            run_m5（§17 事务序列）
  __main__.py        python -m pipeline.validation
  acceptance.py      m5-evidence-gate 十四项判定
  tests/             helpers.py test_registry.py test_g1.py test_g2.py test_g3.py test_inputs.py test_step.py test_acceptance.py
openspec/acceptance/m5-evidence-gate.sh
```
