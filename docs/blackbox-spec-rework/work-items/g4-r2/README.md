# G4 第二批：前缀登记 / D-15 mini fixture / D-18 §20 判据化

状态：`READY`（主 Agent 2026-09-10 编写并自审）
task_id：`blackbox-g4-r2-fixture-and-acceptance`
权威需求来源：`docs/blackbox-spec-rework/D-design.md` D-15、D-18；`openspec/id-prefix-registry.md` §3.3；用户 2026-09-10 三项裁定（前缀方案、§22 分期、页图不进 Git）
基线提交：`38d44f3`
分支：`codex/docs/knowledge-compilation`

## Goal

1. 把 `sch_` / `sv_` / `cg_` 三个前缀登记进规格 §8.1，并把 §12.2 的占位句改为引用。
2. 建立最小可跑 fixture `pipeline/corpus/_fixture/mini_ed01/`：《三辰通载》page_001..003 的 OCR 页面 JSON、机器转录、异常终态、带字框锚点的 spans、m1–m3 期望 StagePackage，以及自校验脚本；页图不进 Git，缺图报 `BLOCKED_SOURCE_ASSET_MISSING`。
3. 把 §20 十一条完成标准改写为「命令 + 期望退出码」，新建 `openspec/acceptance/run_all.sh` 逐条打印 `PASS / FAIL / BLOCKED(前置缺失: …)`；允许 BLOCKED，不允许「无法执行」；第 7 条加入准入阈值使其现在为真红。

## 分组与顺序

| 组 | ACT 顺序 | 写入范围 | Prompt |
|---|---|---|---|
| D | `act/r2-01.yaml` → `act/r2-02.yaml` | 规格 §8.1 / §12.2 / §22.1；`openspec/id-prefix-registry.md` §5；新建 `pipeline/corpus/_fixture/mini_ed01/` | `PROMPT-D.md` |
| E | `act/r2-03.yaml` | 规格 §20；新建 `openspec/acceptance/run_all.sh` | `PROMPT-E.md` |

**E 组必须在 D 组提交之后开工**（`run_all.sh` 调用 fixture 的 `verify.sh`），两组不得同时开工。

## Scope

- 允许写（D）：`openspec/learn-system-blackbox-architecture.md`、`openspec/id-prefix-registry.md`、`pipeline/corpus/_fixture/mini_ed01/**`（新建）
- 允许写（E）：`openspec/learn-system-blackbox-architecture.md`（仅 §20）、`openspec/acceptance/run_all.sh`（新建）
- 允许读：`AGENTS.md`、本目录、`docs/blackbox-spec-rework/D-design.md`、`openspec/schemas/**`、`openspec/legacy-storage-transition.md`、`ocr/data_work/data/page_00{1,2,3}.json`、`ocr/data_work/logs/anomalies.jsonl`、`ocr/data_work/sanche_pages/page_00{1,2,3}.png`（只读本机素材）、`pipeline/corpus/bazi/qtbj_ed01/`（格式参考）
- 其余一切路径禁止写入；`ocr/data_work/` 只读

## Forbidden

1. 把任何 `.png`、`.pdf` 或其他页图副本写入仓库；fixture 只引用本机路径 + SHA-256。
2. 缺素材时创建空文件、替代图片或伪造哈希（`legacy-storage-transition.md` §6）。
3. 修改 `openspec/schemas/verify.sh`、`verify-T.sh`、`mutations.sh`、D-02 Schema 文件。
4. 触动 G3 冻结区域、§3–§18 `状态：` 行；改动 §20 条目编号或条数。
5. 新造前缀（三前缀之外）、新造门禁代号。
6. 在 `run_all.sh` 中把不能判定的项写成 PASS；BLOCKED 必须写明缺什么。
7. `git add -A` / `git add .` / stash / reset / clean / rebase / push / worktree。
8. ACT 未写明的决定自行拍板。

## Inputs（HEAD `38d44f3` 事实）

- 本机素材：`ocr/data_work/sanche_pages/page_001.png`（sha256 `e46bffa38119df1bb03f5a38e4f3f99405a476ba5d7b6a7c489956ccf2e58e65`，1203×1654）、`page_002.png`（`aa5301d98c230a875eeb0b8d8d071393e4d15546d4f352cfb53747af1590f753`）、`page_003.png`（`3c138fc9f32d2cfefe029d62dec2a9a0ce0f095c373af41a8a98f4c8f8afb268`）；三页尺寸相同。
- OCR 页面 JSON：`ocr/data_work/data/page_001.json`（4 行 37 字框）、`page_002.json`（0 行，无文字页，已在 `logs/anomalies.jsonl` 登记 `no_text`）、`page_003.json`（39 行 193 字框）。顶层键 `page/book/image/width/height/lines/chars/extra`；`lines[i]` 有 `id/box{x,y,w,h}/text/children`；`chars[j]` 有 `id/box/parent/char/conf/status`。**注意：行 ID 与该行首字 ID 同名**（如 `page_001c0000` 既是行也是字），锚点必须同时记录 `char_index`。
- Schema 校验：`.venv/bin/check-jsonschema --schemafile openspec/schemas/stage_package.schema.json <yaml>`；`.venv/bin/python` 可 `import yaml, jsonschema`。
- D-02 示例：`openspec/schemas/examples/qtbj_ed01.m1.stage_package.valid.yaml`。
- §20 当前 11 条（第 11 条由 D-06 新增）；§22.1 三元组已确认。
- `openspec/acceptance/` 目录当前不存在；§19.0 引用的 14 个脚本也不存在（不在本批范围）。

## Dependencies

- D-14 `ACCEPTED`（§22 已确认设计）；D-08 `ACCEPTED`（占位句待替换）；D-02 Schema 冻结。
- 本机 `.venv` 存在；`export LC_ALL=en_US.UTF-8`。

## Stop Conditions

- 任一锚点整行命中不为 1；
- 本机素材（三张 PNG、三个 JSON）任一缺失或哈希与 Inputs 不符；
- `check-jsonschema` 不可用；
- 任一既有门禁变红；
- 需要新前缀、改 Schema 或改 `openspec/schemas/verify.sh` 才能完成；
- 对 ACT 有两种理解。

## 决定记录

**2026-09-10 主 Agent 设计裁定（执行者不得改动）**
- 前缀：`sch_<technique>_<3位数字>`、`sv_<32hex>`、`cg_<32hex>`，登记为 §8.1「3b」小节；`pat_`/`ent_` 不在本批。
- fixture 身份：`source_id=src_sanche_ed01`；span `ss_sanche_ed01_p000N_sNN`；EditionPart 声明记录作为 Artifact（`art_000000000000000000000000000000e1`）；期望包与运行 ID 用零填充 32hex 常量（见 `act/r2-02.yaml`）。
- fixture 内容为机器转录（`machine_extracted`），只作结构验收宿主，不作知识来源；page_002 终态 `known_unrecognizable`。
- 一行 OCR = 一个 span；batch：page_001 一批，page_003 按行序每 10 行一批（4 批），共 5 批。
- `run_all.sh` 退出码 = FAIL 条数；BLOCKED 不计；每条 BLOCKED 必须引用 §19 差距行名。
- §20 第 7 条阈值：只有 `original_text` 非空且来源引用可解析的 rule 才可作 Candidate；当前 496 条全空 → 现在必为 FAIL。

**2026-09-10 转译审查（原规划者四查）**：见 `ACCEPTANCE.md` §0。
