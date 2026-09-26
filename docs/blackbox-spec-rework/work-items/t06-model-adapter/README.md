# T06：M4 本机模型适配器（README）

状态：草案，供执行者严格照做。执行者不得自行判断、不得跳步、不得替用户做 Phase B 的裁决。

## 0. 你是谁、要做什么、不做什么

你是一个**严格执行者**（本机 FreeBuff / OpenCode 之类 Agent）。本文档、`TDD.md`、
`act/01.yaml` 三份文档是你唯一的指令来源。三份文档有冲突时，`act/01.yaml` 的
「停手条件」优先于本文档的叙述。任何一步你拿不准，**停手写「待裁决」**，不要自己选。

你**只写文档时不动的东西**（本任务本身不产生代码，代码由你在 Phase C 才写，且要先得
用户批准 Phase B）：本 README 只是任务书，不是代码；不要因为读到某处"应该怎么做"就
提前在 Phase A/B 写代码。

## 1. 目标

把 `pipeline/corpus/_fixture/qianyuan_ed01_text/m4/README.md:1-67` 与
`m4/brief.md:1-57` 记录的「主 Agent 手工把任务书分别派给两路抽取员、拿回抽取件、
用 `task_pipeline.py` 转换成提交件」这套人工流程，改造为**本机命令行 Agent
（FreeBuff、OpenCode）** 可自动调用的 Model Adapter，使：

1. M4 拿到真正意义上的「两个不同模型独立抽取（A/B）+ 第三个模型复核（C）」输入，
   而不是主 Agent 手动搬运；
2. `openspec/acceptance/m4-stage-gate.sh` 里恒为 BLOCKED 的 `cross_model_extraction`
   （`pipeline/knowledge_extraction/acceptance.py:93-96`，见 §2.5）能有真实数据支持，
   从静态占位变成可计算的判定；
3. `other_ports_adapters`（`pipeline/contract_registry/acceptance.py:266-285`）里
   `model` 端口的可替换 Adapter 数从 0 变成 ≥2（T03b 的一半，T06 只负责 model 端口）。

## 2. 背景（引出处 file:line）

### 2.1 TODO.md 的任务定义

- `TODO.md:36`（T06 行）：「M4 接真模型。**没有模型 API**（用户 2026-09-23），可用的
  只有：FreeBuff（DeepSeek V4.1 Flash、GLM 5.3 Flash）、OpenCode（MiMo V2.6 Flash、
  Muse Spark V1.3）、主 Agent 自己（Claude）。所以 Model Adapter 要包的是这些
  **命令行 / 会话工具**，不是 HTTP API。第一步：实测哪些能非交互调用……再定 A/B 抽取
  与 C 复核分别用谁（A/B 必须不同模型）。」完成判据：`m4-stage-gate.sh` 的
  `cross_model_extraction` PASS；真书至少一个 EditionPart 由两个不同真模型独立抽取、
  第三个复核，过 M4 Gate；Adapter 可替换（20.10 不退步）。
- `TODO.md:26`（T03b 行）：「OCR / 模型 / 索引三个端口各自至少 2 个可替换 Adapter
  （契约注册表 `other_ports_adapters`，实测 ocr=0、model=0、index=0）。与 T06 相连：
  模型端口的两个 Adapter 正好是 FreeBuff 与 OpenCode。」

### 2.2 本地会话 2026-09-26 的答复（第 3 节，逐字引用要点）

`docs/handoff/ASK-2026-09-26.reply.md` 第 3 节「M4 本机适配器」（该文件位于分支
`claude/wizardly-maxwell-pqrzh9`，提交 `7ddea59`；本 worktree 当前分支上尚未合并
此提交，读取方式见 `TDD.md` §0）：

> 没有半成品，也没有设计文档。现有的只是三处接口预留：渠道闭集里预留了
> `model_adapter`……原文写的是「日后接入 Model Adapter 只新增渠道，不改 M4
> Interface」。Ledger 的 `record_transformation` 已经有 `model_ref` 参数……
> `pipeline/knowledge_extraction/adapters/` 下的两个文件都不调模型……
> **这个手工流程就是将来 Adapter 要自动化的东西**，可以直接当设计起点：输入是
> 任务书加片段清单，输出是抽取件，`producer.model_id`、`prompt_sha256`、
> `response_sha256` 这几个字段现成就有。T06 的第一步（实测 FreeBuff、OpenCode
> 能不能非交互调用）**没开始**。本机 `/Users/jingtaiwei/tmux-agents/bin/` 里只有
> tmux 交互驱动和屏幕监控脚本，没有非交互调用的尝试。

### 2.3 手工两路抽取流程（就是要自动化的东西）

`pipeline/corpus/_fixture/qianyuan_ed01_text/m4/README.md:1-67`：

- 六份提交件由两个不同厂商的 AI **独立盲抽**、经主 Agent **机械转换**而成
  （`README.md:3-5`）。
- 抽取范围：连续两节正文「天官」「七煞」，RawText 字符偏移 `[8663, 9397)`，对应
  M3 导出的 41 个片段，片段清单 `spans_tianguan_qisha.yaml`（`README.md:12-15`）。
- 抽取任务书 `brief.md`（协议 v2），sha256
  `c3e72bd4a9482258a6868322f371ec1b8993ca24099bb88f5143e7d538bf295e`
  （`README.md:16-18`，即六份提交件 `producer.prompt_sha256` 的取值）。
- 两路模型（`README.md:30-38`）：a 路 `claude-sonnet-5`（`producer.name: w8_lane_a`）；
  b 路 `deepseek/deepseek-v4.1-flash`（`producer.name: w8_lane_b`）。两路抽取员
  **互不可见、不读 `pipeline/**` 任何代码**，只读片段清单；每类候选合计不超过 20 条。
- 提交件性质（`README.md:43-49`）：`channel: task_pipeline_manual`、
  `producer.kind: external_agent`；六份提交件的 `items` **一字未改**（机械转换只把
  抽取件顶层结构映射到提交件契约）；内容为 `machine_extracted`，未经人工审核。
- `brief.md:1-57`：任务书铁律——只读片段清单；只抽原文明说的内容；证据以整片段为
  单位（只写 `source_span_id`/`support_type`）；三类候选合计 ≤20 条；不写审核结论。
  产出顶层结构：`lane / model / assertion / pattern / concept_mention / notes`。
- `M4_BRIEF_TEMPLATE.md:1-95`（协议 v2.1，ACT 19 Q1）是**此后新派发批次**的权威模板：
  把固定上限 20 条改为自适应上限 `ceil(1.2 × 本批片段数)`，并要求「因上限略去任何
  候选必须在 `adapter_notes` 中逐条点名，没有逐条点名的截断视为违规提交」
  （`M4_BRIEF_TEMPLATE.md:36`）。**已发出的 `qianyuan_ed01_text/m4/brief.md` 实例
  不改**（v2.1 只约束此后新派发的批次，见 `M4_BRIEF_TEMPLATE.md:11-14`）。

### 2.4 Adapter 现状（`task_pipeline.py`）

`pipeline/knowledge_extraction/adapters/task_pipeline.py`：

- `normalize_task_output(doc, *, category, lane, channel, technique_id, producer,
  source_task=None, seg_span_map=None)`（:111-147）目前**只支持 `category` ∈
  {assertion, concept_mention}**（:125-134，`pattern`/`school_view` 会抛
  `SchemaViolation(SCH_002)`）——但真书六份提交件里 `submission_pattern_a/b.yaml`
  是**直接手写**成提交件形态、不经过 `normalize_task_output`（`brief.md` 产出的顶层
  结构 `pattern: [...]` 与提交件 `items: [...]` 字段名不同，说明当时 pattern 类别是
  主 Agent 手工映射，没有走这个函数）。**这是 Phase C 要补的缺口之一**：
  `normalize_task_output` 要支持 `pattern` 类别（工位输出顶层键 `pattern`），否则
  自动化流程遇到 pattern 候选就要退回手工。
- `export_task_inputs(spans_doc, *, out_dir, task_id, category, lane, technique_id,
  template_path, id_range, instruction_version, spans_revision_id=None)`（:155-204）
  只支持 `category` ∈ {assertion, concept_mention}（`_STAGE_BY_CATEGORY` 只有这两个
  键，:21），且只导出 `segments.yaml`/`spans.yaml`/`task.yaml`/`INSTRUCTIONS.md`，
  不导出 `brief.md` 这种自由格式任务书。真书六份提交件的输入（片段清单 + 任务书）
  也是主 Agent 手工写的，不是这个函数导出的。
- 本文件顶部注释（:1-5）：「Adapter 只负责把外部形态转成提交件；产物必须先登记进
  Ledger 才能被 M4 核心消费。本模块不读 Ledger、不调用模型。」——这条约束对 Phase C
  仍然成立：**新的 Model Adapter 负责「调用命令行工具、拿到抽取件」，`task_pipeline.py`
  仍然负责「把抽取件转提交件」，两件事不合并**。

### 2.5 渠道闭集与 `model_adapter` 被拒的位置

- `pipeline/knowledge_extraction/__init__.py:17`：
  `CHANNELS = ("fixture_gold", "task_pipeline_manual", "model_adapter", "legacy_workbench")`
  ——`model_adapter` **已经在完整闭集里**，`validate_submission`
  （`pipeline/knowledge_extraction/submission.py:258`）不会因为 channel 是
  `model_adapter` 而报 `SCH_002`。
- `pipeline/knowledge_extraction/__init__.py:18`：
  `ACCEPTED_CHANNELS = ("fixture_gold", "task_pipeline_manual")  # D-01：首切片只收前两个`
  ——这是**真正拦住 `model_adapter` 的地方**。
- `pipeline/knowledge_extraction/submit.py:84`（`run_m4_submit` 内）：
  ```python
  if doc["channel"] not in ACCEPTED_CHANNELS or doc["lane"] == "c":
      raise ExtractionRefused(
          "首切片不收 channel=%s lane=%s" % (doc["channel"], doc["lane"]), code="SCH_002"
      )
  ```
  在 `begin_step_run` 之前拒绝（`submit.py` 模块顶注 :1-5：「`begin_step_run` 之前的
  任何拒绝都不得写入 Ledger」）。**同一行也拒绝 `lane == "c"`**——即使开放
  `model_adapter` 渠道，复核路 c 仍单独被这一行挡住，Phase B/C 都要处理这两个闭集。
- `docs/blackbox-spec-rework/work-items/impl-05-knowledge/README.md:94`
  （D-01 / G7-Q01）：「候选只经提交件 Adapter 登记，渠道闭集中只收 `fixture_gold`、
  `task_pipeline_manual`；`model_adapter` 渠道在 `run_m4_submit` begin 前拒收；验收
  `cross_model_extraction` 恒 BLOCKED。Ledger `record_transformation` 已有 `model_ref`
  参数（`service.py:787`），日后接入 Model Adapter **只新增渠道，不改 M4
  Interface**。」——`service.py:787` 在当前工作树上实际位于
  `pipeline/ledger/service.py:877`（`def record_transformation`）与 `:887`
  （`model_ref=None` 形参），行号已随后续提交漂移，但参数确实存在，已核实。
- `docs/blackbox-spec-rework/work-items/impl-05-knowledge/README.md:114`
  （§5 第 2 条，「已固化默认」）：「渠道闭集 `{fixture_gold, task_pipeline_manual,
  model_adapter, legacy_workbench}`；首切片只收前两个。」——与 `__init__.py:17-18`
  逐字一致。
- `docs/blackbox-spec-rework/work-items/impl-05-knowledge/README.md:163`
  （§6.2 提交件契约）：`channel: fixture_gold  # 闭集 fixture_gold /
  task_pipeline_manual / model_adapter / legacy_workbench；首切片只收前两个`。
- `docs/blackbox-spec-rework/work-items/impl-05-knowledge/README.md:46`（§2 依据
  §14:618-627）：「M6 签发；M4 模式输出类别 ReviewDecision；**Model Adapter 属
  M4**。」——确认 Model Adapter 的归属模块。

### 2.6 `cross_model_extraction` 恒 BLOCKED 的具体位置

`pipeline/knowledge_extraction/acceptance.py`：

- `:92-105`：`BLOCKED_CHECKS` 是一个**静态元组**，三项恒定文本，与 T02
  已修过的 `run_all.sh` 写死判定同形（`TODO.md:23` 完成记录）：
  ```python
  BLOCKED_CHECKS = (
      ("cross_model_extraction",
       "前置缺失: M4 Knowledge Extraction；生产模型 A/B 独立抽取与复核模型 C"
       "（§12.2）未接入 Model Adapter，本批为无模型薄接入"),
      ("semantic_span_input", ...),
      ("term_layering_scan", ...),
  )
  ```
- `:658-660`（`main()` 内）：
  ```python
  for name, text in BLOCKED_CHECKS:
      blocked += 1
      print("BLOCKED %s %s" % (name, text))
  ```
  **无条件打印**，不读任何实际状态。这与 `semantic_span_input`（依赖 T07，M3
  SemanticSpan 未实现）、`term_layering_scan`（依赖 T08，术语分层未实现）不同：
  这两项在 T06 完成前也**理应**保持 BLOCKED；`cross_model_extraction` 是**唯一**
  一项本任务范围内要让它变成可计算的判定。

### 2.7 契约注册表 `other_ports_adapters`（T03b 的判定，T06 只碰 model 端口）

`pipeline/contract_registry/acceptance.py:266-285`：
```python
def _other_ports_adapters(registry):
    counts = {}
    for port_id in ("ocr", "model", "index"):
        port = registry.ports.get(port_id) or {}
        counts[port_id] = sum(
            1 for adapter in (port.get("adapters") or []) if adapter.get("entry")
        )
    if any(counts[port_id] < 2 for port_id in counts):
        return ("BLOCKED", "other_ports_adapters", "…端口 Adapter 数不足 2…")
    return ("BLOCKED", "other_ports_adapters", "…端口未登记一致性套件")
```
**重要事实（已核实）**：这个函数**没有任何 PASS 分支**——即使三个端口都各自登记
≥2 个 `entry` 非空的 Adapter，函数仍然落到第二个 `return`，继续输出 BLOCKED
（理由变成"未登记一致性套件"）。**registry.yaml 加两个 model Adapter，不能让
`other_ports_adapters` 变成 PASS**；给它加 PASS 分支、设计"一致性套件"是 T03b
的范围（T03b 同时管 ocr/model/index 三个端口），**T06 不做**、**不许改
`pipeline/contract_registry/acceptance.py`**（该文件属 M8 生产模块登记 ACT，
`impl-05-knowledge/README.md:81` 明文禁止 impl-05 系执行者改
`pipeline/contract_registry/**`，本任务沿用同一边界）。T06 的判据因此是
`TODO.md:36` 写的「Adapter 可替换（20.10 不退步）」——即 `other_ports_adapters`
的 `model` 计数从 0 变成 ≥2，且总体退出码不劣化，而不是这一项本身变 PASS。

`pipeline/contract_registry/registry.yaml:212-214`（当前状态，行号随 T04 登记
M1–M8 为生产模块后已整体后移，本任务合并 `claude/wizardly-maxwell-pqrzh9`
到当前 worktree 后重新核实）：
```yaml
  - port_id: model
    adjacent_interface: [step_request, step_result]
    adapters: []
```
`ocr` 端口（:207-211）有一个 `entry: null` 的占位 Adapter（不计入 T03b 的
`entry` 非空计数）；`storage` 端口（:200-206）是唯一已有两个真 Adapter 的例子
（`ledger_direct` → `DirectLedgerAdapter`、`ledgerd_client` → `LedgerdClientAdapter`，
均在 `pipeline/contract_registry/ports.py:81-137`），**是本任务 Adapter 类命名与
`entry` 字符串写法唯一可抄的现成范例**（`entry: "模块路径:类名"`）。

**T04 补充事实（合并后核实）**：`registry.yaml` 现在 M1–M8 全部登记为生产模块
（`entry`/`resume_entry` 分别指向各包的 `entry.py` 或 `step.py`，例如 M4 行
`entry: "pipeline.knowledge_extraction.entry:run_m4"`，`resume_entry:
"pipeline.knowledge_extraction.step:resume_m4"`，`registry.yaml:98-99`）。
新增了 `pipeline/knowledge_extraction/entry.py`（调度器入口，包一层
`step.run_m4`，校验运行输入里的 `technique_profile.{technique_id,canon_dir}`，
若某类别/路别缺提交件则返回零写入拒收 `{"refused": True, "reason": ...}`，
`entry.py:57-84`）。**这意味着 Phase C 验收时，真书两节可以经调度器
（`pipeline.orchestrator`）整线跑，不必像 `test_qianyuan_text_host.py` 那样手工
调 `run_m1/run_m2/run_m3_text/run_m4_submit`**——但 `entry.py` 本身不在本任务
写权限范围内（属 `pipeline/orchestrator/**` 相邻的 T04 成果），T06 只读它、
不改它。

### 2.8 提交件 schema 对 Model Adapter 已经就位的部分

`pipeline/knowledge_extraction/__init__.py:19`：
`PRODUCER_KINDS = ("fixture", "human", "external_agent", "model")`——`producer.kind`
闭集里 `model` 已经存在。`pipeline/knowledge_extraction/submission.py:117-135`
（`_normalize_producer`）对 `producer.model_id` / `prompt_sha256` / `response_sha256`
不作强制校验（可选字段，缺省 `None`），**Phase C 的 Adapter 必须如实填写这三个字段**
（本任务硬性要求，见 §「必须写进去的内容」第 3 条）。

## 3. 范围

**写**（仅当 Phase B 获批、进入 Phase C 后才动笔；Phase A/B 阶段只产出报告文件，
不改任何生产代码）：

- `pipeline/knowledge_extraction/adapters/freebuff.py`（新建，Phase C）
- `pipeline/knowledge_extraction/adapters/opencode.py`（新建，Phase C）
- `pipeline/knowledge_extraction/adapters/task_pipeline.py`（Phase C：补 `pattern`
  类别支持，见 §2.4）
- `pipeline/knowledge_extraction/__init__.py`（Phase C，且仅当用户在 Phase B 选择
  「新增 model_adapter 渠道」方案：把 `"model_adapter"` 加入 `ACCEPTED_CHANNELS`；
  这是**改规格判定的一部分**，必须等用户批准，见 §4 阶段 B）
- `pipeline/knowledge_extraction/submit.py`（Phase C，若 Phase B 选定方案需要放开
  `lane == "c"` 的复核路，需要另外的用户批准，见 `act/01.yaml` 阶段 B 步骤）
- `pipeline/knowledge_extraction/tests/**`（新增测试）
- `docs/handoff/T06.report.md`（各阶段的回报，见 §5）
- `docs/handoff/T06-phase-a.md`（阶段 A 的实测记录，见 §5）

**只读**（禁止改动）：

- `pipeline/knowledge_extraction/entry.py`、`pipeline/knowledge_extraction/step.py`
  （T04 的调度器接线成果，见 §2.7 末尾「T04 补充事实」；本任务不改调用协议，只让
  新 Adapter 产出的提交件走既有的 `run_m4_submit`）
- `pipeline/contract_registry/**`（T03b 范围，见 §2.7）
- `pipeline/corpus/_fixture/qianyuan_ed01_text/m4/**`（已封存的真书宿主，六份提交件
  与 `brief.md` 一字不动；`SHA256SUMS` 已覆盖）
- `openspec/**`（规格正文与 acceptance 脚本，除非 Phase B 明确要求且用户批准）
- `openspec/id-prefix-registry.md`
- `pipeline/ledger/**`
- `pipeline/dataset_compiler/**`、`pipeline/orchestrator/**`
- `TODO.md`、`PLAN.md`、`HANDOFF.md`（按 AGENTS.md「受限执行 Agent 例外」，你不改这三
  个协调文件；由主 Agent 在独立验收后更新）

## 4. 非目标（P7 铁律）

**T06 不做任何形式的自动审核或自动签发**。具体列出，防止执行者「顺手做了」：

1. 不实现、不触碰任何让候选自动获得 `expert_verified` / `cross_model_reviewed` 的
   代码路径（`M4_STATUS_CEILING = ("machine_extracted", "disputed", "needs_expert")`，
   `pipeline/knowledge_extraction/__init__.py:28`，本任务产出的候选上限不变）。
2. C 路（复核模型）产出仍然是**候选**，不是裁决。M4 类别分歧（a/b 不一致）仍然要
   进人工队列，由用户裁决（`m4/README.md:53-55`：「M4 分歧必须由用户本人裁决后
   方能 `resume_m4` 封存」）。**C 路复核结果不能替代人工裁决，只能作为分歧队列里
   给用户看的额外参考信息**（如果 Phase B 选定的方案里包含 C 路复核环节，该环节的
   落地形态必须在 Phase B 报告里写清楚"C 路输出如何进入分歧队列、如何标注"，
   并经用户批准后才能在 Phase C 实现）。
3. 不新建任何脚本让 M6 审核队列、M4 分歧队列自动出结论。
4. 不修改 `derive_content_status`（`pipeline/knowledge_extraction/review_events.py`）
   的推导规则。
5. 不伪造任何人工事件（`synthetic_fixture` 标记只在测试夹具里出现，且必须显式标注，
   参照 `impl-05-knowledge/README.md:456` 的 `ruling_m4_d001.yaml` 写法）。

## 5. BDD 场景

### 场景 1：探测 FreeBuff 能否非交互调用（阶段 A）

```gherkin
Given 本机已安装 FreeBuff 命令行工具
When 执行者用同一条命令、同一个固定 prompt，连续调用 3 次
Then 每次调用都不需要人工在终端里交互（无需按键确认、无需 tmux 附着）
  And 每次调用的 stdout 都拿到完整的模型输出（不是被截断的流）
  And 命令的退出码在三次调用里都是 0（或对同一失败原因给出同一非 0 退出码）
  And 记录三次调用的耗时、原始输出前 200 行、退出码
```

### 场景 2：探测失败 → 停手（阶段 A）

```gherkin
Given 执行者已尝试 FreeBuff 与 OpenCode 各自的非交互调用方式
When 两者都无法在不使用 tmux 屏幕抓取的情况下拿到完整、确定性的输出
Then 执行者停止 Phase A，把「命令、错误信息、退出码」写进
  docs/handoff/T06-phase-a.md
  And 在 docs/handoff/T06.report.md 顶部写「T06 阶段 A 不通过，停手待裁决」
  And 不进入阶段 B、不进入阶段 C
```

### 场景 3：用户尚未批准渠道开放（阶段 B 停手点）

```gherkin
Given 阶段 A 已确认 FreeBuff 与/或 OpenCode 可非交互调用
When 执行者需要开放 model_adapter 渠道才能继续
Then 执行者不得自行修改 ACCEPTED_CHANNELS
  And 执行者把候选方案（a. 新增 model_adapter 渠道；b. 仍走
      task_pipeline_manual，只自动化产出抽取件）写进
      docs/handoff/T06.report.md 的「待用户决定」小节
  And 执行者停手，等待用户在 TODO.md 或本报告里给出选择
```

### 场景 4：两个 Model Adapter 独立产出提交件（阶段 C，用户已批准方案 a）

```gherkin
Given 用户已批准「新增 model_adapter 渠道」方案
  And pipeline/knowledge_extraction/adapters/freebuff.py 已实现
  And pipeline/knowledge_extraction/adapters/opencode.py 已实现
When 分别用 FreeBuff Adapter 跑 lane a、OpenCode Adapter 跑 lane b，
  输入同一份任务书与片段清单
Then 两份提交件的 producer.kind 都是 "model"
  And producer.model_id 分别是两个 Adapter 各自调用的真实模型名（不同）
  And producer.prompt_sha256 等于任务书字节的 sha256
  And producer.response_sha256 等于模型原始输出字节的 sha256
  And 两份提交件都能被 run_m4_submit 接受（channel=model_adapter）
```

### 场景 5：模型调用失败或产出非法 → fail-closed（阶段 C）

```gherkin
Given Model Adapter 调用命令行工具时超时，或工具返回非零退出码，
  或返回内容不是合法 YAML/JSON
When Adapter 处理该次调用的结果
Then Adapter 不吞掉错误、不产出一份「空提交件」或「部分提交件」
  And 该次调用整体标记失败并抛出异常（不静默丢弃某几条候选）
  And 失败原因（命令、退出码、stderr 前 N 行）被完整记录
  And run_m4_submit 侧不会看到一份形状不完整的提交件
```

### 场景 6：真书两节验收（阶段 C 的验收步骤，不在单测里，只在人工验收步骤里跑真模型）

```gherkin
Given 真书《乾元秘旨》「天官」「七煞」两节的片段清单（m4/README.md 的
  spans_tianguan_qisha.yaml，41 个片段）
When 用 FreeBuff Adapter 与 OpenCode Adapter 各自独立抽取一路
  （lane a 与 lane b 用不同模型）
Then 产出的提交件被 run_m4_submit 接受
  And 与现有人工提交件（submission_assertion_a/b.yaml 等）的条数、字段形状
  逐项对照，差异如实列出（不要求条数一致，只要求「差异被列出并能解释」）
  And 该 EditionPart 上跑 run_m4，观察分歧队列条数是否有意义地变化
```

## 6. 与其他任务的边界

- T03b：`ocr`、`index` 两个端口的 Adapter，以及 `other_ports_adapters` 的 PASS 分支，
  都不是本任务的事。T06 只处理 `model` 端口的两个 Adapter 数量。
- T07（SemanticSpan）、T08（术语分层）：`semantic_span_input`、`term_layering_scan`
  两项 BLOCKED 与本任务无关，T06 完成后它们仍应保持 BLOCKED。
- T26（`docs/handoff/ASK-2026-09-26.reply.md` 建议表）：全书分批抽取计划依赖 T06先
  把「谁来抽」定下来，T06 完成后应更新 T26 的前置状态（属主 Agent 事后维护，本任务
  执行者不改 TODO.md）。
