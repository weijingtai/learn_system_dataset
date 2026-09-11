# G4 第一批 · C 组 Executor Prompt（D-14）

你是规格落实执行 Agent，工作在 Agent 工具为你创建的独立 git worktree 中（祖先含 `e64f2a4`）。不要 `cd` 到主工作树 `/Users/jingtaiwei/Git/Public/learn_system`，不切分支、不 stash、不 reset、不 clean、不 rebase、不 push。所有回复与文档文本使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g4-r1/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/d14.yaml`。需要背景时读 `docs/blackbox-spec-rework/D-design.md` 的 D-14 条与 `docs/blackbox-spec-rework/verify-T.sh` 的 `T-11` 段（§19 有事实门禁，既有单元格文字一个字节不能改）。

只允许修改两个文件：`openspec/learn-system-blackbox-architecture.md` 与根目录 `LEARN_SYSTEM_TARGET.md`。

严格执行：

1. `export LC_ALL=en_US.UTF-8`，运行 TDD §0 五条基线并记录原始输出。
2. 按 `act/d14.yaml` 执行：先断言锚点（注意 §19 分隔行 `|---|---|---|---|` 在文件中不唯一，必须取表头的紧邻下一行）；记录 TDD §1 d14 的 Red 值；对 19 个数据行按 `labels` 表逐行在行尾追加分期列——只改行末 ` |` 为 ` | <标签> |`，其余字节不动；插入 `legend_line`；把 `text_22` 逐字追加到文件末尾（§21 末行之后空一行；YAML `|` 块的两格缩进去掉，块内空行与代码围栏照原样保留）；在 `LEARN_SYSTEM_TARGET.md` 指定位置插入 `target_note`。然后运行 ACT 的 `verify` 全部命令与 TDD §2 回归五条；全部符合后 `git add openspec/learn-system-blackbox-architecture.md LEARN_SYSTEM_TARGET.md` 显式暂存并按 ACT 的 `commit.message` 提交，消息末尾附一行 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。
3. 一个提交，只含这两个文件。
4. 停手规则：锚点命中不为 1；§19 数据行不是 19 行；任一门禁变红（尤其 `T-11s` 任一项、`T-13`、`G3-*`）；对 ACT 文本有两种理解；需要改第三个文件。一律停止、不自行决定、不放宽任何命令，把原始输出与 `git status --short` 写进报告交主 Agent 裁定。
5. `labels` 表中的分期取值是主 Agent 的裁定，不得改动；不得改写 §19 既有单元格、§19.0、§19.1 或 §21 的任何文字。

最终报告必须包含：worktree 路径与分支名；提交 hash 与 `git show --stat --oneline`；基线五条输出；Red/Green 判据原始输出（含 19/4/9/6 四个计数）；回归五条原始输出；`git status --short`；以及一句「等待主 Agent 独立验收与合并；§22 分期待用户过目」。
