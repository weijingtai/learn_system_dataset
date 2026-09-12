# impl-10：M3 Corpus Compilation（§11）语义层：SemanticSpan、双模型边界提议与分歧人工裁决

状态：`DRAFT`（起草 Agent 产出；§4 待主 Agent 裁决；**必须排在 impl-02 `ACCEPTED` 之后派发**）

## 1. 目标

在 `pipeline/corpus_compiler/semantic/`（新子包）落地规格 §11 第 2–5 条与 §11.1：在 impl-02 结构层（StructuralSpan + glyphbox 锚点）之上，产出 **SemanticSpan** 层：

1. 规则优先：结构行默认一行一个语义片段（§11 第 1 条）；规则无法判定的行进入「模型窗口」；
2. 双模型独立提议：A、B 两个 Proposer 各自只看窗口原文，只输出 `start_offset/end_offset/reason`，原文由程序截取（§11 第 2、3 条）；
3. 两份提议一致即采纳；不一致或任一提议非法即进入 **M3 边界分歧队列**，StepRun 进入 `awaiting_human`，人工裁决作为不可变 `human_event` 写回，每条裁决落盘一个 Checkpoint，之后 `resume`（§11 第 4 条、§7.1、§17.1）；
4. 每条 SemanticSpan 带页块 offset、`quote_sha256`、对结构 Span 的引用和逐字 glyph 锚点；`evidence_level` 逐条如实判定（§11.1）；
5. 独立语义 Gate 判定：同层全文覆盖 100%、无缺口、无重叠、拼接等于页块、未解决语义分歧为零（§11:521）；
6. m3 StagePackage 的 `gate_profile` 从 `structural_only` 升级为 `structural_and_semantic`。

模型调用完全隔离：Proposer 是 Adapter 接口；测试和验收只用**手写回放录制**（`ReplayProposer`），零网络；真实模型 Adapter 本包只留一个默认禁用的桩（D2）。

完成判据（本包唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
bash openspec/acceptance/m3-coverage.sh; echo exit=$?
# 期望：9 行 PASS（inputs_frozen … package_lineage、semantic_layer）+ SUMMARY pass=9 fail=0 blocked=0；exit=0
.venv/bin/python -m pipeline.corpus_compiler.semantic.acceptance \
  --fixture pipeline/corpus/_fixture/mini_ed01 \
  --semantic-fixture pipeline/corpus/_fixture/mini_ed01_semantic; echo exit=$?
# 期望：9 行语义子项 PASS + SUMMARY pass=9 fail=0 blocked=0；exit=0
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/semantic/tests -t . 2>&1 | grep -E '^(Ran|OK|FAILED)'   # OK，≥ 82
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | grep -E '^(Ran|OK|FAILED)'            # OK（impl-02 用例数不减）
bash openspec/acceptance/run_all.sh | tail -1     # 不变：SUMMARY pass=2 fail=1 blocked=8（本包不改 run_all.sh）
```

`m3-coverage.sh` 是 §19.0 登记的「M3 整书漏编/无双层锚点」差距判据（规格:907 附近，修复后 exit 0）。本包落地后该差距关闭。

回放验收只证明「双提议 → 比较 → 分歧 → 人工裁决 → 覆盖 Gate」这套机制可确定性重放，**不证明任何模型的切分质量**；录制文件显式标注 `synthetic: true`。

## 2. 依据（只读来源，文件:行号）

- 规格 `openspec/learn-system-blackbox-architecture.md`
  - §5:119–124 `PendingQueue` 第 2 队列「M3 边界分歧」；§5:128 Review Console 呈现 M3 边界分歧
  - §7:207 Module 只读冻结 Artifact；§7.1:211–221 一次 StepRun 覆盖任务及其整个人工队列、`await_human`/`record_human_event`/`resume` 语义、恢复只读冻结输入与写回事件
  - §8.1:265 ReviewDecision 必须同时记录目标 `entity_id` 与所见 `artifact_revision_id`；§8.1 第 3 节第 5 条（约 :300）非法格式判定
  - §8.2:349–364 ReviewDecision 八类；§8.2:406–430 StepRun 迁移（`running → awaiting_human → running`）
  - §10.1:482–494 异常页终态
  - §11:496–521（链路 :502–509；第 1–5 条 :515–519；Gate :521）；§11.1:523–528 `offset_level`/`glyphbox_level`
  - §12.2:572–574 A/B 独立、初次不可见彼此结果、不采用多数票、Prompt/Response/参数/版本/差异/人工决定全部作为 Artifact 保存
  - §13.1:590 G3（offset + quote hash、`evidence_level` 判定）
  - §14:622 M3 模式输出归属 M3 StepRun 的边界 ReviewDecision；§14:627「模型调用统一属于 M4 的 Model Adapter」
  - §17:835 事务序列；§17.1:838–846 单链 Checkpoint、人工决定被接受后即时落盘、恢复不重做
  - §19:876 M3 行「缺双层 Span」；§19 语义分层阻塞行（约 :894）；§19.0 M3 行（约 :907）
  - §20.3:938、§20.10:945；§22.1:964–969（`evidence_level=glyphbox_level`、`INTERNAL_DEMO`）
- `openspec/id-prefix-registry.md`:27（`ss_` = SourceSpan「页码 + 句序」）、:93–97（只引用已登记前缀、新增前缀流程）
- `docs/blackbox-spec-rework/work-items/impl-02-corpus/README.md`:34（决定 1：只做结构层、`structural_only`、`semantic: not_evaluated`、语义层落地时升级 gate_profile）、:37（输入解析）、:38（Gate 独立）、:40（退出码纪律）
- `pipeline/corpus_compiler/acceptance.py`:30–33、:86（`semantic_layer` 恒 BLOCKED）、:407–435（`batch_checkpoints` 统计该 EditionPart 全部 m3 Checkpoint）
- `openspec/acceptance/m3-coverage.sh`:23（永远调用规范 verify.sh）、:36
- `pipeline/ledger/service.py`：`put_artifact`:442、`register_stage_package`:718–746（同一 `stage_package_id` 不可重复登记）、`record_transformation`:777（`model_ref`）、`await_human`:885、`record_human_event`:922–929（`decision_type` 只接受 §8.2 八类或 None）、`resume`:965、`_live_step_run`:253（`running`/`awaiting_human` 可写）、`_write_checkpoint_locked`（`_stage_sealed_by_finished_run`：同 EditionPart×Stage 已有 succeeded StepRun 后，新 StepRun 除非经 supersedes 链否则不能写 Checkpoint）
- `pipeline/ledger/states.py`:57（`REVIEW_DECISION_TYPES`）
- fixture 实测（`pipeline/corpus/_fixture/mini_ed01/spans.yaml`）：
  - 文本长度 ≥ 12 的结构行恰 2 条：`ss_sanche_ed01_p0001_s04`（17 字「三辰通載三十卷宋錢如璧撰據静嘉堂藏」）、`ss_sanche_ed01_p0003_s13`（14 字「論星曜合照命宮論星曜對照命宮」，目录两条目 OCR 合行）
  - glyph 与文本**不对齐**的结构行恰 2 条：`p0001_s03`（非空字框 5 个「宋刊本影印」对文本 6 字）、`p0001_s04`（含 2 个空字框、缺「藏」）；其余 41 行非空字框字符序列 == 文本
  - 注意：结构锚点里的 `char_index` 是页内 `chars` 数组下标，不是文本位置，不能直接当 offset 用

## 3. 范围

写（全部为新增，除 ACT 06 列出的三处经 D9 批准的修改）：

- `pipeline/corpus/_fixture/mini_ed01_semantic/**`（ACT 00，新建兄弟目录，D7）
- `pipeline/corpus_compiler/semantic/**`（ACT 01–06，新建子包）
- ACT 06 修改（D9）：`pipeline/corpus_compiler/acceptance.py`（只改 `semantic_layer` 一项与参数）、`pipeline/corpus_compiler/tests/test_acceptance.py`（只改列明用例）、`openspec/acceptance/m3-coverage.sh`（加语义金标宿主校验与参数透传）

禁止：

- 改 `pipeline/corpus_compiler/` 结构层其他已有文件（`compiler.py gate.py inputs.py step.py serialize.py errors.py __init__.py __main__.py` 及其测试）的任何行为或文本
- 改 `pipeline/ledger/**`、`pipeline/corpus/_fixture/mini_ed01/**`、规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、`run_all.sh`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、其他 work-items
- 新增依赖（只用标准库 + PyYAML + jsonschema）；import 任何网络库（`socket` 仅测试可用于打补丁断言零网络）；调用任何模型 API
- 未经 D1 裁决使用新前缀；生产代码读工作目录文件代替 Ledger 冻结修订（例外见 D5：回放录制是 Adapter 后端，只经显式参数传入）
- 执行者写台账、`ACCEPTANCE.md` 或把任何项标为 `ACCEPTED`

## 4. 待主 Agent 裁决

每条给出选项、起草人推荐（标「推荐」）与理由。ACT 契约按推荐项书写；主 Agent 选别的选项时，须同步改写对应 ACT 中标注 `〔D#〕` 的段落。

### D1 SemanticSpan 标识前缀（阻断 ACT 00/02/03）

事实：`ss_` 登记含义是「页码 + **句序**」（registry:27，沿用旧 `SCHEMA.md` v0.2 §2），impl-02 已把它用于 **OCR 行**（StructuralSpan，金标 sha256 `ec6d77b9…` 已冻结）。语义片段没有登记前缀；registry:96 要求先登记再入 §8.1 再用。

- A（推荐）新登记 `sem_<work>_ed<NN>_p<NNNN>_s<NNN>`（人工闭集家族，页号取起始页，序号 3 位、页内从 001 顺序编号）。`git grep '\bsem_'` 当前 0 处。理由：不动已冻结金标与 impl-02；3 位序号给行内拆分留余量。代价：`ss_` 的「句序」字面与实际「行序」不符的历史歧义仍在，需在 registry 注明。
- B SemanticSpan 改用 `ss_`，StructuralSpan 另登记新前缀。语义上更贴近旧 SourceSpan（M4/M8/注解锚点历来认 `ss_`），但要重生成 `spans.yaml` 金标并返工 impl-02，涟漪大。
- C 不设领域 ID，用 `ss_…#<start>-<end>` 复合键。违反 §8.1:255–263 稳定 `entity_id` 语义，且与 §19 M8「映射键碰撞」同类风险，不推荐。

**下游影响**：M4 EvidenceLink、M5 G3、M8 AnchorContractPack 引用的「原文片段 ID」是 `sem_` 还是 `ss_`，由本条决定，须与 M4/M5/M8 草案对账。

### D2 真实模型调用开关与 Adapter 归属

§11:516 要求 M3 用两个模型；§14:627 却写「模型调用统一属于 M4 的 Model Adapter」。

- A（推荐）本包只定义 M3 `BoundaryProposer` 接口 + `ReplayProposer`；`LiveProposer` 为桩：未设环境变量 `LEARN_SYSTEM_ALLOW_MODEL_CALLS=1` 时构造即抛 `ModelCallDisabled`，设了也在 `propose` 抛 `ModelCallDisabled("未实现")`，本包不含任何网络代码。真实 Adapter 另立工作包，并与 M4 Model Adapter 统一接口（§20.10 换 Adapter 不改相邻接口）。
- B 本包直接实现某厂商 Adapter，由显式开关 + 密钥环境变量启用，测试一律回放。违反「不新增依赖/不调模型 API」纪律，且模型选型未裁决。
- C M3 不自带 Proposer 接口，等 M4 Model Adapter 落地后复用。会让本包无法完成。

还需裁定：§14:627 的措辞是否改为「模型调用统一经 Model Adapter 接口（M3 边界提议与 M4 抽取共用）」——属规格修改，本包不改。

### D3 `gate_profile` 新取值与 M4 消费约束

规格没有 `gate_profile` 枚举；`structural_only` 是 impl-02 自定（impl-02 README:34）。

- A（推荐）新增取值 `structural_and_semantic`；m3 StagePackage `payload` 增 `semantic: "passed"`、`semantic_spans_revision_id`、`disputes`、`evidence_level_counts`。旧 `run_m3` 保留原样（`structural_only`）。**下游契约**：M4 只能消费 `payload.gate_profile == "structural_and_semantic"`、`validation.passed == true`、`payload.disputes.unresolved == 0` 的 m3 包，遇 `structural_only` 包必须拒绝。
- B 取值 `full`。更短但语义不自明。
- C 删除 `structural_only` 路径，只保留完整 M3。要改 impl-02 已验收代码，不推荐。

### D4 StepRun 拓扑：语义层放在哪个 StepRun（阻断 ACT 04/05）

Ledger 事实：同一 EditionPart×m3 已有 succeeded StepRun 后，新 StepRun 除非经 `supersedes_step_run_id` 链，否则**不能再写 m3 Checkpoint**（`_write_checkpoint_locked`）；`register_stage_package` 不允许重复 `stage_package_id`。§7.1:211 另说「一个阶段可以包含多个此类任务」，与 Ledger 现行为有张力。

- A（推荐）新增 `run_m3_full`：**一个** M3 StepRun 依次完成结构层（复用 `compile_structural`/`evaluate_structural` 纯函数，写出与 `run_m3` 同类型、同字节的结构产物）→ 语义规则 → 双提议 → `await_human` → 裁决 → `resume` → 语义 Gate → 唯一的 m3 StagePackage。理由：符合 §7.1:211「一次 StepRun 覆盖任务及其整个人工队列」、§17.1 单链、§11:502–509 一条链产出一个 CorpusPackage；不改 Ledger、不改 `run_m3`。代价：结构层 Ledger 写序列在两处实现（由 ACT 04 字节等价测试兜底）。
- B 先 `run_m3`（结构包封存）再开语义 StepRun，以 `supersedes_step_run_id` 指向结构 StepRun。能写 Checkpoint，但把「后续任务」伪装成「重跑」，违背 §8.2:424–430 supersede 语义；且早先封存的 `structural_only` 包仍可被消费。
- C 改 Ledger，允许同阶段多个任务 StepRun 各自 succeeded 后再合取 Stage Gate。最贴合 §7.1:211，但要返工 impl-01 已验收代码，另立包。

### D5 回放录制的身份：Adapter 后端还是冻结输入

- A（推荐）录制文件是 `ReplayProposer` 的**后端**（相当于外部模型服务），不是 Module 输入：只经 `--replay <path>` / 构造参数传入；配置修订记录 `adapter: replay`、`model_id`、`model_version`、`recording_set_sha256`；每次请求与响应字节都作为 `model_request`/`model_response` Artifact 封存，血缘完整（§12.2:574、§20.3）。换成真实模型时 Module 接口不变（§20.10）。
- B 把录制内容嵌进 `configuration` 修订（`put_run_artifact` 只允许 `configuration`/`technique_profile`，service.py:66）。纯「只读 Ledger」，但把模型输出伪装成配置，真实模型时路径不同。
- C 新增 artifact_type 并扩展 `fixture_ingest` 灌入录制。要改 impl-01/02 已验收文件。

### D6 M3 边界裁决的 `decision_type`

`record_human_event` 只接受 §8.2:349–364 八类或 None；八类里没有「边界切分」。

- A（推荐）`review_source_fidelity`（「审核文本与原书/底本切片的一致性」最接近边界切分）。
- B 传 `None`，类型只写在事件内容里。可行但 Ledger 侧无法按类型查询。
- C 规格 §8.2 增第 9 类 `review_segmentation`。需用户确认改规格。

### D7 语义层金标放在哪（阻断 ACT 00）

- A（推荐）新建兄弟目录 `pipeline/corpus/_fixture/mini_ed01_semantic/`：`recordings.yaml`（手写，`synthetic: true`）、`human_decisions.yaml`、`semantic_spans.yaml`（由本目录独立生成器产出）、`expected/m3.stage_package.yaml`、`tools/build_semantic_fixture.py`、`verify.sh`、`README.md`、`manifest.yaml`。以 sha256 钉住 `mini_ed01/spans.yaml`。理由：`mini_ed01` 的 `manifest.yaml` `files[]`、expected/m1 `content_sha256`、生成器重放 `diff -r` 与 `run_all.sh` 全部不受影响。
- B 扩展 `mini_ed01/tools/build_fixture.py` 把语义金标生成进原目录。manifest 字节变 → M1 修订哈希、expected/m1、run_all 20.x 连锁变化。
- C 放进 `pipeline/corpus_compiler/semantic/tests/golden/`。验收脚本读测试目录，规范性弱。

### D8 复用结构层私有 Ledger 读写助手（影响 ACT 04）

`step.py` 里的 `_validate_input_contract`、`_read_manifest_content`、`_read_revision_json`、`_build_artifacts_map`、`_artifact_ref`、`_fail` 都是私有函数，而且 J3 返工仍在改。

- A（推荐，首切）只读 import `pipeline.corpus_compiler.step` 的这些私有函数，不改 `step.py`；另加一个契约测试钉住签名，签名一变立即红。
- B 先由主 Agent 批一个纯重构 ACT，把它们抽到公开模块 `pipeline/corpus_compiler/ledger_io.py`（改 `step.py`，行为不变）。更干净，但动已验收代码。
- C 在语义子包里重写一份。重复实现，输入契约可能漂移。

### D9 为达 exit 0 必须修改的三个结构层已有文件（阻断 ACT 06）

`semantic_layer` 由 `acceptance.py`:86 写死为 BLOCKED，`m3-coverage.sh` 只校验 `mini_ed01`，所以不改这些文件就无法 exit 0。申请的最小改动：

1. `acceptance.py`：增可选参数 `--semantic-fixture`；给了就调用 `pipeline.corpus_compiler.semantic.acceptance.check_semantic_layer(...)` 得到 PASS/FAIL；没给就 BLOCKED，说明改为「前置缺失: M3 Corpus Compilation；未提供 --semantic-fixture（语义层金标与录制响应）」。其余八项与退出码逻辑不动。
2. `tests/test_acceptance.py`：`test_semantic_layer_line_is_blocked_with_exact_text` 改期望文本；`test_shell_exit_2_on_fixture` 改名为 `test_shell_exit_0_on_fixture`，期望 `SUMMARY pass=9 fail=0 blocked=0`、exit 0；追加 2 个用例。
3. `m3-coverage.sh`：增 `SEMANTIC_FIXTURE_DIR`（默认规范路径，可被环境变量覆盖）；调用**仓库内规范** `mini_ed01_semantic/verify.sh` 做宿主校验；向 acceptance 透传 `--semantic-fixture`。

- A（推荐）批准以上三处。
- B 另建 `openspec/acceptance/m3-semantic.sh`，`m3-coverage.sh` 保持 exit 2。与 §19.0「M3 一条判据 exit 0」不符。

### D10 §11 第 5 条「条件/结论、正文/注文、通则/命例完整性检查」的范围

fixture 只有题名页和目录页，不含注文、命例、条件句，第 5 条在宿主上无法真实判定。

- A（推荐）本包的 `semantic_layer` 覆盖 §11 第 1–4 条与 :521 Gate，外加「明显切分问题」检查（语义片段不得跨结构行、不得为空、窗口外必须一行一片）；分层判定归 §19「语义分层阻塞」行（`pipeline-p0.sh`，首纵切后）与 M5 G4（§13.1）。README 与验收说明逐字写明，不把第 5 条算作已通过。
- B 最小实现片段类型（`heading/catalog/paratext/prose`）并检查类型不混，在 fixture 上只能验证目录类。价值有限，且类型枚举规格未定义。
- C 第 5 条单列一行 BLOCKED，`m3-coverage.sh` 维持 exit 2。

### D11 字框不对齐行的 `evidence_level`（影响 ACT 02/03 金标计数）

§22.1:968 要求首纵切达 `glyphbox_level`，但 `p0001_s03`、`p0001_s04` 的 OCR 字框缺字或含空字框（§2 实测）。

- A（推荐）逐片如实判定：该行非空字框字符序列 == 文本时为 `glyphbox_level`，锚点给出逐字 glyph；否则为 `offset_level`，保留行 bbox，`glyphs: []`。金标计数 glyphbox 42 / offset 4（`p0001_s03` 整行 1 条 + `p0001_s04` 拆出的 3 条）。`INTERNAL_DEMO` 允许 `offset_level`（§11.1:526）；`PUBLIC_RELEASE` 由 M5 G3 拦截（§13.1:590）。同时提示：impl-02 在文档级宣称 `glyphbox_level`，与这两行实情不符，属结构层遗留，另报。
- B 一律 `glyphbox_level`、只给行 bbox。会在证据链上假绿。
- C 字框不对齐的行拒绝编译（fail-closed）。fixture 无法通过，需先回 M2 修字框。

### D12 窗口选择规则（规则层占位）

- A（推荐，首切）确定性阈值规则：结构行文本长度 ≥ `model_min_chars`（默认 12，写进配置修订）即成为单行模型窗口，其余行一行一片。fixture 恰得 2 个窗口。只处理行内拆分，不产生跨行、跨页片段。
- B 规则由 TechniqueProfile 声明（标题/条目/表格识别器）。更贴合 §11:515，但 TechniqueProfile 的 Contract 未定义。
- C 多行窗口（连续需模型的行合并成窗口，允许跨行片段）。散文、注疏必需，但 offset 坐标、glyph 映射和跨页片段都要另定，建议下一包。

### D13 是否引入复核模型 C（§11:518「由独立复核或人工决定」）

- A（推荐）本包不引入：分歧直接进人工队列。
- B 引入 C 重读原文，只有 C 不能与 A 或 B 完全一致时才进人工。多一组录制，且 §12.2 的 C 规则是 M4 语境。

### D14 新 artifact_type 与内容格式登记

本包新增 artifact_type：`semantic_windows`、`model_request`、`model_response`、`boundary_proposal`、`boundary_comparison`、`boundary_review_queue`、`semantic_spans`、`semantic_gate_report`。复用已有类型：`human_event`（内容 `schema: m3_boundary_decision/1`）、`validation_report`、`corpus_package`、`step_log`、`failure_report`、`stage_package`。

- A（推荐）本包内以 ACT 契约冻结字段与键序，不新增 JSON Schema；Contract Registry 落地时再补 `semantic_spans.schema.json`。
- B 本包同时新增 `openspec/schemas/semantic_spans.schema.json` 并接入 `openspec/schemas/verify.sh`。需主 Agent 放开 schemas 写权限。

## 5. 接口契约

### 5.1 上游输入（本包依赖）

| 来源 | 内容 | 读取方式 |
|---|---|---|
| M1（impl-02 已解析） | `source_manifest` 修订（YAML：`source_id`、`work_title`、`technique_id`、`edition_part.pages`、`source_assets[].sha256`） | `resolve_m3_inputs`（只读 import）+ 冻结输入字节 sha256 复核 |
| M2 | `ocr_page_set`（`ocr_pages[{page, sha256}]`、`terminal_states`）、各页 `ocr_page` JSON（`lines[{id, text, box}]`、`chars[{id, char, box, parent}]`）、`human_event`（异常页证据，顶层 `page`） | 同上；M2 StepRun 必须 succeeded |
| M3 结构层（同一 StepRun 内产出） | `compile_structural` 返回的 `spans_doc`/`spans_bytes`/`batches`/`coverage`/`excluded_pages`；`evaluate_structural` 返回的 `structural`/`checks` | 纯函数只读 import，不改 |
| Proposer 后端（D5） | `recordings.yaml`：`template_id`、`models.{a,b}`、`entries[{slot, structural_span_id, window_text_sha256, response_text}]` | 显式参数传入，sha256 写入配置修订 |

### 5.2 对下游输出（M4/M5/M6/M8 与 Orchestrator 对账用）

- **m3 StagePackage**（`stage: m3`，过 `stage_package.schema.json`）：
  - `payload`：`spans_revision_id`、`semantic_spans_revision_id`、`coverage`、`excluded_pages`、`gate_profile: structural_and_semantic`〔D3〕、`semantic: passed`、`disputes: {total, resolved_by_human, unresolved: 0}`、`evidence_level_counts: {glyphbox_level, offset_level}`
  - `manifest.counts`：`spans`、`batches`、`semantic_spans`、`windows`、`disputes`、`human_decisions`（fixture：43/5/46/2/1/1）；`manifest.content_sha256` = `semantic_spans` 修订字节的 sha256（语义文档内含 `structural_spans_sha256`，间接绑定结构层）
  - `lineage.transformations`：`compile_corpus` ×1、`propose_boundaries` ×（窗口数×2）、`reconcile_semantic_spans` ×1（其 `human_event_revision_ids` = 全部裁决事件）
- **`semantic_spans` 修订**（YAML，`serialize.dump_yaml` 规则）：
  - 文档键序：`work, source_id, edition_part_artifact_id, structural_spans_sha256, gate_profile, segmentation_profile, content_status, span_count, window_count, dispute_count, evidence_level_counts, spans`
  - Span 键序：`semantic_span_id, page, sequence, start_offset, end_offset, text, quote_sha256, boundary_origin(rule|cross_model_agreed|human_decided), window_id, structural_refs[{span_id, start, end}], evidence_level, source_anchor{page, image_sha256, line_id, bbox, glyphs[{glyph_id, char, box}]}`
  - offset 相对页块（与结构层同一坐标）；`start`/`end` 相对所引结构 Span 文本
- **M4 消费约束**：只消费 D3 规定的包；EvidenceLink 记录 `semantic_span_id`（`entity_id`）+ `semantic_spans` 的 `artifact_revision_id`（§8.1:265）；不得读 `corpus_spans` 代替语义层。
- **M5 G2/G3**：可直接复算 `quote_sha256`、同层覆盖与逐片 `evidence_level`；`offset_level` 片段不得进入 `PUBLIC_RELEASE`。
- **M6/Review Console M3 模式**：待裁决队列 = `boundary_review_queue` 修订（由 `await_human` 事件的 `pending_queue` 引用）；裁决写回 `human_event`（`schema: m3_boundary_decision/1`，含 `structural_span_id` 与 `seen_review_queue_revision_id`），`decision_type` 按 D6。
- **Local Orchestrator `PendingQueue`/`StageProgress`**：`run_status` 显示 `awaiting_human`；m3 Checkpoint 的 `pending_queue` 含 `review:<window_id>` 项。

## 6. 目录规划（落地后）

```text
pipeline/corpus/_fixture/mini_ed01_semantic/        ACT 00（D7）
  README.md  manifest.yaml  recordings.yaml  human_decisions.yaml  semantic_spans.yaml
  expected/m3.stage_package.yaml  tools/build_semantic_fixture.py  verify.sh
pipeline/corpus_compiler/semantic/
  __init__.py          M3S_TOOL / M3S_TOOL_VERSION / GATE_PROFILE             ACT 01
  errors.py            RecordingSetInvalid RecordingMiss ModelCallDisabled DecisionRejected DisputesUnresolved  ACT 01
  proposer.py          模板、build_request、ReplayProposer、LiveProposer(桩)、load_recordings  ACT 01
  proposals.py         parse_proposal、compare_proposals                       ACT 01
  rules.py             select_windows                                          ACT 02
  anchors.py           glyph_aligned、sub_anchor                               ACT 02
  reconcile.py         validate_decision、resolve_windows                      ACT 02
  assemble.py          compile_semantic（金标字节）                             ACT 02
  semantic_gate.py     evaluate_semantic（独立，不 import 上述任何模块）          ACT 03
  step.py              run_m3_full（到 await_human 或直接完成）                 ACT 04
  review.py            submit_boundary_decision、resume_m3_full                ACT 05
  __main__.py          python -m pipeline.corpus_compiler.semantic run|decide|resume  ACT 05
  acceptance.py        九项语义子判定 + check_semantic_layer                   ACT 06
  tests/               test_proposer test_proposals test_assemble test_semantic_gate test_step_full test_review test_acceptance_semantic
修改（D9）：pipeline/corpus_compiler/acceptance.py、pipeline/corpus_compiler/tests/test_acceptance.py、openspec/acceptance/m3-coverage.sh
```

## 7. 依赖与派发

- **硬前置**：impl-02 README 状态为 `ACCEPTED`（J3 返工验收通过），`$TC` 全绿，`m3-coverage.sh` exit 2。未满足时执行者开工即停。
- **裁决前置**：D1、D4、D7、D9 未裁决时不得派发；D2、D3、D5、D6、D8、D10–D14 未裁决时按推荐项执行。
- 分两轮：J1 = ACT 00–03（金标 + 纯函数 + 独立 Gate，不碰 Ledger）；J1 全部 ACCEPTED 后派 J2 = ACT 04–06（Ledger 集成、人工裁决与恢复、验收）。
- 与其他并行草案的接口假设见 §5.2；M4 草案若假设「SourceSpan = `ss_`」或「m3 包只有 `corpus_spans`」，须按 D1/D3 对账。
