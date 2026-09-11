# G4 第一批 · A 组 Executor Prompt（D-13 → D-10 → D-11）

你是规格落实执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `cb175c4`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复与文档文本使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g4-r1/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/d13.yaml`、`act/d10.yaml`、`act/d11.yaml`。需要背景时读 `docs/blackbox-spec-rework/D-design.md` 的 D-13/D-10/D-11 条。这些文件包含全部背景、精确锚点、要写入的确定文本、判据与停手条件，不依赖聊天上下文。

只允许修改一个文件：`openspec/learn-system-blackbox-architecture.md`。其余一切路径禁止写入。工作树里其他人的未提交改动（如 `openspec/annotation-community/` 下的文件）原样保留，不暂存、不提交、不删除。

严格执行：

1. `export LC_ALL=en_US.UTF-8`。运行 `git merge-base --is-ancestor cb175c4 HEAD && echo ANCESTOR_OK`，再运行 TDD §0 其余四条基线（`git status --short` 允许出现他人已有的脏文件，但 `openspec/learn-system-blackbox-architecture.md` 必须干净；`verify-T.sh` 尾行 `FAIL 合计: 0`；`mutations.sh all` 尾行 `109/109 rejected`；`openspec/schemas/verify.sh` exit 0）并记录原始输出。不符即停手报告。
2. 按 `act/d13.yaml` → `act/d10.yaml` → `act/d11.yaml` 串行执行。每个 ACT：先用 `LC_ALL=C awk '$0 == ENVIRON["A"]'` 断言每个锚点整行恰命中 1 次；先记录 TDD §1 该 ACT 的 Red 值；再把 ACT 的 `replacement_*` / `text_*` 字段**逐字**写入指定位置（YAML `|` 块内的两格缩进是 YAML 语法，落到 Markdown 时去掉；块内空行照原样保留）；然后运行该 ACT 的 `verify` 全部命令与 TDD §2 回归五条；全部符合后用 `git add openspec/learn-system-blackbox-architecture.md` 显式暂存并按 ACT 的 `commit.message` 提交。
3. 三个 ACT 共三个提交，每个提交只含这一个文件。不得使用 `git add -A` 或 `git add .`。
4. 停手规则：锚点命中不为 1；任一门禁变红（尤其 `verify-T.sh` 出现 `G3-*` 或 `T-13` FAIL、`mutations.sh all` 不是 109/109）；对 ACT 文本有两种理解；需要改第二个文件才能通过。一律停止、不自行决定、不放宽任何命令，把原始输出与 `git status --short` 写进报告交主 Agent 裁定。
5. 不得修改任何既有句子，除 ACT 明确指定的替换；不得删除内容。

最终报告必须包含：三个提交 hash 与各自 `git show --stat --oneline`；基线输出；每个 ACT 的 Red/Green 判据原始输出；最后一次回归五条原始输出；`git status --short`；以及一句「等待主 Agent 独立验收」。
