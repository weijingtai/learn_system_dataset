# G3 R5 Executor Prompt

你是 G3 R5 区域边界封闭的执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`，不切换分支、不 stash、不 reset、不 clean。所有回复与代码注释使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g3-r5/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/01.yaml`、`act/02.yaml`。这些文件包含全部背景、精确常量、用例表、期望输出与停手条件，不依赖任何聊天上下文。`docs/blackbox-spec-rework/work-items/g3-r3/` 下除 `mutations.sh` 之外的文件是过时草稿，不要按它们执行。

只允许修改两个文件：`docs/blackbox-spec-rework/verify-T.sh` 与 `docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh`。其余一切路径禁止写入，包括 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、规格正文与本工作包。

严格执行：

1. `export LC_ALL=en_US.UTF-8`。运行 TDD §0 四条基线命令并记录原始输出；两个授权脚本相对 `ffe19df` 必须无差异，正常规格必须 `FAIL 合计: 0`、selftest `37/37`、矩阵 `98/98`。不符即停手报告。
2. 按 `act/01.yaml` 只改 `mutations.sh`：新增 9 个常量（逐字照抄 TDD §1.1）、2 个原语（`append_gap_line`、`append_suffix`，带全部命中断言）、11 个用例（TDD §1.3 的 cid、操作、绑定 ID 一字不差）、4 个 `[7]` selftest、分母 34/28/47。验证：selftest `41/41`；d07/t07/t08 的 `not-rejected` 恰 4/2/5 行且全是新增 cid；`MUTATION_NOT_APPLIED` 为 0；`all` 为 `98/109`。用 `git add docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh` 显式暂存后提交，消息 `test: add G3 R5 permanent red mutations for region boundaries`。
3. 按 `act/02.yaml` 只改 `verify-T.sh`：D-07 改为区域提取（TP→QC START、QC→RI START、RI→`### 16.2`，区域去空行后与「START + 条目」序列相等）；T-07 新增表格 17 行封闭（表头、分隔行、15 个 canonical 行各恰一次、每行恰 3 个 `|`）；T-08 新增 §16.3.1 去空行 11 行序列相等与三个标题各计数为 1。所有 expected 硬编码；不加任何否定词或关键词黑名单；不用 `sort -u` 或 `[[:space:]]`。验证：正常规格 `FAIL 合计: 0` 且 `PASS  G3-` 行数 12；selftest `41/41`；d07 `34/34`、t07 `28/28`、t08 `47/47`、all `109/109`；`MUTATION_NOT_APPLIED` 为 0；`git diff --check` 无输出。用 `git add docs/blackbox-spec-rework/verify-T.sh` 显式暂存后提交，消息 `fix: close final G3 region boundary bypasses`。
4. 提交消息末尾按 AGENTS.md 与环境要求附署名行。不得使用 `git add -A` 或 `git add .`；开工前已存在的脏文件原样保留，不暂存、不提交、不删除。
5. 任一步骤不符合期望：停止，不扩大范围，报告失败 ACT、命令、退出码、cid、Anchor 命中数和 `git status --short`。

实现原则：比较「完整区域结构和逐字规范化值」，不是猜测自然语言含义。放宽断言、跳过变异、忽略替换失败、固定返回码、缩减矩阵、分母与实际不一致，均视为任务失败。

最终报告必须包含：两个提交 hash 及各自 `git show --stat --oneline`；基线四条输出；Red 阶段 not-rejected 行原文与 selftest 尾行；Green 阶段正常门禁尾行、`PASS  G3-` 计数、selftest、d07/t07/t08/all 尾行、`MUTATION_NOT_APPLIED` 计数、`git diff --check`；最终 `git status --short`；以及一句「等待主 Agent 独立验收；未启动 G4」。
