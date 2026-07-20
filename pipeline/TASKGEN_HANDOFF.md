# TASKGEN 平台化 · 交接文档

> 写给接手本项目监管/开发的 AI agent 或人类。读完这一篇即可独立维护、验证、扩展
> "任务包生成器"这条线，无需追溯对话历史。
>
> **更新时间**：2026-07-18　**分支**：`codex/docs/knowledge-compilation`
> **覆盖范围**：`pipeline/tools/` 下游任务包生成器的平台化重构（P0–P3，全部完成）。
> 不覆盖：知识内容本身的编纂、RAG、tag_system、工位9/10 的实现。

---

## 〇、30 秒速览

- **这条线是什么**：把"为工位4/5/6 生成任务包"的三个脚本，从各自硬编码 `bazi/qtbj`
  的复制品，收敛成一个配置驱动的公共库 `tools/lib/taskgen.py` + 三个薄壳工具。
- **现在什么状态**：P0–P3 全部完成并提交。产物 byte 不变，回归门禁已固化。
- **怎么确认没坏**：`cd pipeline && python3 validators/check_taskgen.py`（应 PASS）。
- **谁在跟踪进度**：AI 记忆文件 `platform-refactor-assessment.md`（见本文末"记忆指针"）。
- **原始需求文档**：`knowledge_system/PLATFORM_REFACTOR_ASSESSMENT.md`（定义 G1–G4 缺口和 P0–P3 方案）。

---

## 一、项目背景与目标

### 1.1 大项目在做什么
`learn_system` 是一条**术数典籍知识编译流水线**：把古籍原文，经过多个"工位"逐步加工成
结构化、可校验、每条主张都能指回原文的知识单元，最终供 APP 使用。核心铁律是
**任何模型输出都不得绕过校验直接成为发布知识**，且**原文只能复制粘贴、禁止凭知识编造**。

完整流水线（见 `pipeline/HANDBOOK.md` 第1章）：

```
原书 → [1]转录核对 → [2]结构盘点 → [3]语义切分 → [4]术语识别
     → [5]主张提取 → [6]白话释义 → [9]词条聚合 → [10]跨技法连接 → validate.py
```

新 agent 入门必读顺序：`pipeline/AGENT_GUIDE.md`（六条铁律+工作循环）→
`pipeline/HANDBOOK.md`（各工位规程）→ 本文（若你要动 taskgen）。

### 1.2 这条线的目标（platform 化）
项目已能跑通两个技法（八字《穷通宝鉴》qtbj、奇门《烟波钓叟歌》）。但"技法无关"
只做到一半：**制度层通用（注册表/schema/校验器/文档），执行层仍带硬编码**。
本次重构的目标：**把执行层也收敛成配置驱动**，让新技法/新书目尽量开箱即用，
而不是每次复制脚本再改。

判断性质：**不是重写，是收敛与参数化。**

---

## 二、重构前的四个缺口（G1–G4）

来自 `PLATFORM_REFACTOR_ASSESSMENT.md`，是本次工作的靶子：

| # | 缺口 | 后果 |
|---|------|------|
| **G1** | gen 工具硬编码书目/技法/源ID（`qtbj`/`bazi`/路径前缀写死） | 换书目要改代码而非传参 |
| **G2** | 模板分叉成"通用版 + _bazi 版"；stage6 **只有** `_bazi` 版 | 工位6对奇门不可用；逻辑双份维护 |
| **G3** | `tasks/`(小写) 硬编码，实际产物在 `TASKS/` | macOS 大小写不敏感侥幸没炸，**Linux/CI 上会分裂出两套目录、丢产物** |
| **G4** | 5 个 gen 工具是同骨架的复制品 | 一处改 bug 要改 5 处 |

---

## 三、P0–P3 做了什么（实际落地，含与原方案的偏差）

> 重要：以下是**实际做法**。个别处与 `PLATFORM_REFACTOR_ASSESSMENT.md` 的原始设想不同，
> 已注明"偏差"。以本文为准。

### P0 — 修大小写隐患（G3）　commit `1b9b87b`
把三工具里写死的 `tasks/` 统一成 `TASKS/`；核对仓库不再同时存在两种大小写目录。
风险低、独立可先落。

### P1 — 抽公共库，去重去硬编码（G1+G4）　commit `1a3198b`
- 新建 `tools/lib/taskgen.py`：封装"读 spans → 按 batch 收 segments → 拷模板+glossary
  → 写 task.yaml"的公共骨架，以 `DownstreamTaskSpec` dataclass 承载各工位差异。
- 三个下游工具（concept/assertion/paraphrase）瘦身为"声明 spec + 调 build()"。
- 技法/源ID 从 `corpus/<technique>/<edition>/manifest.yaml` 读取，不再写死。
- **偏差**：原方案说"5 个 gen 工具"，实际只有 **3 个**是"下游任务包生成器"同骨架
  （concept/assertion/paraphrase）。另外 `gen_task`(工位3切分)/`gen_spans`/`gen_outline`/
  `gen_canon` 数据源和产物结构不同，**不属于同一骨架，未纳入 taskgen**（见 §6）。

### P2 — stage6 通用基座 + 按技法解析（G2）　commit `ed69f98`
- 新建 `task-templates/stage6_paraphrase/INSTRUCTIONS.md`：技法无关的白话释义通用基座
  （抽掉八字专属举例），补齐 stage4/5 已有的"通用版 + _bazi 版"成对模式。
- `taskgen` 新增 `resolve_template(stage_dir, technique_id)`：
  优先 `<stage_dir>_<technique>`（如 `stage6_paraphrase_bazi`），
  缺派生则回落通用基座 `<stage_dir>`，均缺抛 `FileNotFoundError`。
- glossary 也改为按技法自动解析：`schemas/techniques/<technique>/glossary_v0.yaml`。
- 三工具改用 `template_stage_dir` 声明，移除 bazi 硬编码路径。
- **偏差**：原方案设想的是 "base.md + technique_addendum.md 拼装" 机制；实际采用了更简单的
  **"通用基座目录 + 技法覆盖目录，整份择一"** 机制（`resolve_template`）。理由：与 stage4/5
  既有的 `stageN_x` / `stageN_x_bazi` 成对结构一致，改动面最小、无需引入拼装逻辑。

### P3 — 固化回归门禁　commit `65b28ec`
- 新建 `validators/check_taskgen.py`：用当前三工具生成任务包，与
  `validators/goldens/taskgen/` 黄金快照 **byte 比对**；并单测 `resolve_template` 三路径。
- 黄金快照只存**生成类**文件（`task.yaml`/`segments.yaml`/`spans.yaml`）；
  `INSTRUCTIONS.md`/`glossary_v0.yaml` 是逐字拷贝，改由脚本核对来源解析。
- 配套：`build()` 增 `out_root` 参数（仅落地位置、内容不变），测试写临时目录、
  不触碰真实 `TASKS/`；三工具抽出 `make_spec()`，`main` 变薄，供测试注入。
- **偏差**：原方案 P3 设想的是 "扫 tools/ 里 qtbj/bazi 字面量的 `check_platform.py`"；
  实际做的是**黄金快照回归门禁**——更直接地锁住"产物不变"这个真正要保的东西。字面量扫描
  未做（低价值，硬编码已在 P1 移除）。

---

## 四、重构后的架构（当前真实状态）

### 4.1 三个下游工具 = 薄壳
```
tools/gen_concept_task.py     工位4 术语识别任务包
tools/gen_assertion_task.py   工位5 主张提取任务包
tools/gen_paraphrase_task.py  工位6 白话释义任务包
```
每个工具只做两件事：
1. `make_spec(corpus, round_name, batch_ids)` → 返回一个 `DownstreamTaskSpec`（声明本工位差异）；
2. `main()` → `build(make_spec(...))`。

CLI 用法不变：`python3 tools/gen_paraphrase_task.py corpus/bazi/qtbj_ed01 s1 qtbj_b001 qtbj_b002 ...`

### 4.2 公共库 `tools/lib/taskgen.py`
关键导出：
- `DownstreamTaskSpec`（dataclass）：承载各工位差异。字段顺序即 YAML 输出顺序，**byte 敏感**。
  - `seg_builder`：组装单个 segment 的回调，签名 `(bid, span_id, seg_local, raw_seg) -> (seg_dict, sp_dict|None)`。
  - `template` **或** `template_stage_dir` 二选一（后者触发按技法解析）。
  - `glossary` 可留空 → 按技法解析。
- `build(spec, out_root=None)`：执行骨架，返回任务目录。`out_root` 默认 `PIPELINE/TASKS`，
  测试可指临时目录（内容与默认路径完全一致）。
- `resolve_template(stage_dir, technique_id)`：模板按技法解析（命中派生/回落基座/全缺报错）。
- `load_manifest(corpus)`：读 `corpus/<t>/<ed>/manifest.yaml`。

### 4.3 模板与术语表布局
```
task-templates/
├── stage4_concept_candidates/   ⚠ 见 §5 历史遗留坑
├── stage4_concepts_bazi/        ← bazi 派生
├── stage5_assertions/           ⚠ 见 §5
├── stage5_assertions_bazi/      ← bazi 派生
├── stage6_paraphrase/           ← P2 新建的技法无关通用基座
└── stage6_paraphrase_bazi/      ← bazi 派生
schemas/techniques/<technique>/glossary_v0.yaml   ← 按技法解析的术语表
```

---

## 五、⚠ 已知的坑（接手前必看）

1. **stage4/5 的"通用版"名不副实**。`stage4_concept_candidates` / `stage5_assertions` 里
   装的其实是**奇门/早期原版**（引用 yanbo_ed02），与 `_bazi` 版是各自演化的**分叉**，
   不是干净的"基座+覆盖"。且 `stage4_concept_candidates` 与派生 `stage4_concepts_bazi`
   **无共享前缀**，所以 `resolve_template("stage4_concepts", <非bazi技法>)` 回落不到那个
   "通用版"。**真要上第二技法前，必须先理清 stage4/5 的模板命名和归属**——只有 stage6
   是这次做干净的。
2. **只有 bazi 走通了全链路**。qimen 的 stage6 会回落到通用基座（能跑），但没有实际
   生成过 qimen 的工位6任务包做冒烟。上 qimen 时要跑一遍验证。
3. **byte 敏感**。`DownstreamTaskSpec` 里字段顺序 = YAML 输出字段顺序。改动 seg_builder
   或字段顺序会改产物 byte，check_taskgen 会 FAIL。若是**有意**变更，跑 `--update` 重采快照；
   若非有意，说明改错了。

---

## 六、未纳入本次重构的部分（不是遗漏，是范围外）

- `tools/gen_task.py`（工位3切分）、`gen_spans.py`、`gen_outline.py`、`gen_canon.py`：
  数据源/产物结构与三个下游工具不同，**不是同一骨架**，未纳入 taskgen。
  如需统一需另做评估，不要硬套 `DownstreamTaskSpec`。
- 校验器（`validate.py` 等）：已通用，本次未动。注意 `validate.py` 是**单元校验器**、
  **不是** `check_*` 的聚合器——各 `check_*.py` / `validate_*_task.py` 独立运行。
- corpus 数据、已签发的主张/释义产物：未动。

---

## 七、常用命令

```bash
cd pipeline

# 生成一个任务包（工位6示例）
python3 tools/gen_paraphrase_task.py corpus/bazi/qtbj_ed01 s1 qtbj_b001 qtbj_b002 qtbj_b003

# taskgen 回归门禁（改了 taskgen 或三工具后必跑）
python3 validators/check_taskgen.py

# 有意变更产物后，重采黄金快照
python3 validators/check_taskgen.py --update

# 全量单元校验
python3 validators/validate.py --all
```

---

## 八、如何扩展（新增一个技法，如 qimen 的工位6）

1. **先解决 §5 坑1**：确认 stage4/5 模板命名分叉已理清（若只做 stage6 可暂缓，但要知道 stage4/5 会回落失败）。
2. 建技法派生模板 `task-templates/stage6_paraphrase_<technique>/INSTRUCTIONS.md`
   （若通用基座够用，可不建，会自动回落基座）。
3. 确认 `schemas/techniques/<technique>/glossary_v0.yaml` 存在。
4. 确认 `corpus/<technique>/<edition>/manifest.yaml` 里 `technique_id` 正确。
5. 跑 `python3 tools/gen_paraphrase_task.py corpus/<technique>/<edition> <round> <batch...>` 冒烟。
6. 若要把该技法纳入回归门禁，在 `check_taskgen.py` 的 `CASES` 加用例并 `--update`。

---

## 九、记忆指针（AI agent 用）

本线进度长期记录在 AI 记忆文件（非仓库内）：
`~/.claude/projects/-Users-jingtaiwei-Git-Public-xuan-migration-learn-system/memory/`
- `platform-refactor-assessment.md` — P0–P3 逐步进度、验收方式、历史遗留坑（最权威的进度源）。
- `gen-tools-taxonomy.md`（若存在）— gen 工具分类：哪些是同骨架、哪些不是。

接手时先读这两个记忆文件 + `knowledge_system/PLATFORM_REFACTOR_ASSESSMENT.md`（原始需求）。

---

## 十、提交历史（本线）

```
65b28ec  test(pipeline): 固化 taskgen 回归门禁 + 黄金快照(P3)
ed69f98  feat(pipeline): stage6 补通用基座 + 模板/术语表按技法解析(P2)
1a3198b  refactor(pipeline): 抽 taskgen 公共库,下游三工具去重去硬编码(P1)
1b9b87b  fix(pipeline): 统一 tasks/ → TASKS/ 大小写(P0 平台化重构)
```
（P3 门禁文档本身的提交在此之后；以 `git log` 为准。）
