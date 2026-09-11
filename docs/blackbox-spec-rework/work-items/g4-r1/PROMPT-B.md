# G4 第一批 · B 组 Executor Prompt（D-06 → D-08）

你是规格落实执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `cb175c4`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复与文档文本使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g4-r1/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/d06.yaml`、`act/d08.yaml`。需要背景时读 `docs/blackbox-spec-rework/D-design.md` 的 D-06/D-08 条，以及 `docs/blackbox-spec-rework/verify-T.sh` 中 `G3-D07-*`、`G3-T07-*`、`G3-T08-*` 段落，理解 §16 哪些区域是冻结的。

只允许修改一个文件：`openspec/learn-system-blackbox-architecture.md`。其余一切路径禁止写入。工作树里其他人的未提交改动原样保留，不暂存、不提交、不删除。

最重要的边界：§16 中从 `` `TechniqueProfilePack` 承载…`` 那一行起直到 `## 17.` 之前的全部内容是 G3 冻结区域，你的两个新块必须插在该行**之前**（`act/d06.yaml` 与 `act/d08.yaml` 给了精确锚点），且插入后 TP 起始行之前必须恰好只有一个空行。`mutations.sh all` 保持 `109/109 rejected` 是你没有触动冻结区域的机器证明。

严格执行：

1. `export LC_ALL=en_US.UTF-8`。运行 `git merge-base --is-ancestor cb175c4 HEAD && echo ANCESTOR_OK`，再运行 TDD §0 其余四条基线（`openspec/learn-system-blackbox-architecture.md` 必须干净；`verify-T.sh` 尾行 `FAIL 合计: 0`；`mutations.sh all` 尾行 `109/109 rejected`；`openspec/schemas/verify.sh` exit 0）并记录原始输出。不符即停手报告。
2. 按 `act/d06.yaml` → `act/d08.yaml` 串行执行。每个 ACT：先用 `LC_ALL=C awk '$0 == ENVIRON["A"]'` 断言每个锚点整行恰命中 1 次；记录 TDD §1 该 ACT 的 Red 值；把 ACT 的 `text_*` / `*_replacement` / `s20_item_11` 字段**逐字**写入指定位置（YAML `|` 块的两格缩进是 YAML 语法，落到 Markdown 时去掉；块内空行照原样保留）；运行该 ACT 的 `verify` 全部命令与 TDD §2 回归五条；全部符合后 `git add openspec/learn-system-blackbox-architecture.md` 显式暂存并按 ACT 的 `commit.message` 提交。
3. 两个 ACT 共两个提交，每个只含这一个文件。不得使用 `git add -A` 或 `git add .`。
4. 停手规则：锚点命中不为 1；任一门禁变红（尤其 `G3-*`、`T-06s`、`T-13` FAIL 或 mutations 不是 109/109）；对 ACT 文本有两种理解；需要新造 `school_id` 前缀或其他 ID 格式；需要改第二个文件。一律停止、不自行决定、不放宽任何命令，把原始输出与 `git status --short` 写进报告交主 Agent 裁定。
5. 不得修改任何既有句子，除 ACT 明确指定的替换；不得删除内容；不得往 §16 树里加 `SchoolViewPack`（它是逻辑分包）。

最终报告必须包含：两个提交 hash 与各自 `git show --stat --oneline`；基线输出；每个 ACT 的 Red/Green 判据原始输出；最后一次回归五条原始输出（含 mutations 尾行）；`git status --short`；以及一句「等待主 Agent 独立验收」。
