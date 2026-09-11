# G4 第二批 · D 组 Executor Prompt（r2-01 前缀登记 → r2-02 mini fixture）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `38d44f3`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释与文档使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g4-r2/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/r2-01.yaml`、`act/r2-02.yaml`、`openspec/id-prefix-registry.md`、`openspec/legacy-storage-transition.md` §6、`openspec/schemas/stage_package.schema.json` 与 `openspec/schemas/examples/qtbj_ed01.m1.stage_package.valid.yaml`。

只允许写：`openspec/learn-system-blackbox-architecture.md`、`openspec/id-prefix-registry.md`、新建目录 `pipeline/corpus/_fixture/mini_ed01/`。`ocr/data_work/` 只读。其余一切路径禁止写入；工作树里其他人的未提交改动原样保留。

硬约束：任何图像文件（png/jpg/pdf）不得进入仓库；三张页图只以本机路径引用 + SHA-256 登记；缺素材时脚本报 `BLOCKED_SOURCE_ASSET_MISSING` 并退出 3，绝不创建空文件、替代图或伪造哈希。

严格执行：

0. 开工前提：`git status --short openspec/learn-system-blackbox-architecture.md openspec/id-prefix-registry.md pipeline/corpus/_fixture` 必须无输出（这三处若已有他人未提交改动，你的 `git add` 会把它们一并带进提交）。有输出即停手报告。
1. `export LC_ALL=en_US.UTF-8`。运行 TDD §0 全部基线（含 `git merge-base --is-ancestor 38d44f3 HEAD`、三张 PNG 的 sha256 与 README Inputs 逐一比对、`.venv/bin/check-jsonschema` 存在）并记录原始输出。任一不符即停手报告。
2. 按 `act/r2-01.yaml`：断言三处锚点；记录 TDD §1 Red；插入 `text_3b`（逐字，去掉 YAML 两格缩进）、替换 §12.2 占位子串、勾选登记册待办；运行 ACT `verify` 与 TDD §4 回归；`git add openspec/learn-system-blackbox-architecture.md openspec/id-prefix-registry.md` 后按 `commit.message` 提交。
3. 按 `act/r2-02.yaml`：**先写 `verify.sh`**（V1–V8 定义一条不少），运行确认 Red；再写 `tools/build_fixture.py`（确定性，只用标准库 + yaml），生成 `layout` 列出的全部文件；`constants` 与 `formats` 是硬规定，不得改 ID、哈希、batch 划分或字段名；page_002 按 `known_unrecognizable` 处理；spans 恰 43 条 5 批。然后运行 TDD §2 全部 Green 判据（含缺图模拟 exit 3、两种篡改检出 exit 1、`build_fixture.py --out` 重放 `diff -r` 无差异）与 TDD §4 回归；在规格 §22.1 按 `spec_edit` 插入一行；`git add pipeline/corpus/_fixture/mini_ed01 openspec/learn-system-blackbox-architecture.md` 后按 `commit.message` 提交。
4. 两个 ACT 共两个提交。不得使用 `git add -A` 或 `git add .`。
5. 停手规则：锚点命中不为 1；素材缺失或哈希不符；`check-jsonschema` 不可用；任一门禁变红；某条 V 检查无法按定义实现；对 ACT 有两种理解；需要改 Schema 或 `openspec/schemas/verify.sh`。一律停止、不自行决定、不放宽任何命令，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：两个提交 hash 与各自 `git show --stat --oneline`；基线输出（含三个 PNG 哈希）；r2-01 Red/Green；r2-02 的 `verify.sh` Red 输出、Green 全文（含 `FIXTURE OK`）、缺图模拟输出与退出码、两种篡改输出与退出码、重放 `diff -r` 结果、`43 5` 计数；TDD §4 回归；`git status --short`；以及一句「等待主 Agent 独立验收」。
