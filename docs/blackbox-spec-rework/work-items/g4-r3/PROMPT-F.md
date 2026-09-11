# G4 第三批 · F 组 Executor Prompt（r3-01 D-16 映射表 → r3-02 pat_/ent_ 登记）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `2978ad9`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释与文档使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g4-r3/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/r3-01.yaml`、`act/r3-02.yaml`、`docs/blackbox-spec-rework/D-design.md` §D-16、`PLAN.md` 全文、规格 §19 主表与 §8.1 第 3b 节。

只允许写：`PLAN.md`（只插入一节，任何既有行一个字节不改）、`pipeline/TODO.md`、`pattern_knowledge_workbench/TODO.md`、`LEARN_SYSTEM_TARGET.md`（各只替换 ACT 指定的一整行）、新建 `docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`、`openspec/learn-system-blackbox-architecture.md`（只在 §8.1 第 3b 节插入）。其余一切路径禁止写入；工作树里其他人的未提交改动原样保留。

严格执行：

0. 开工前提：`git status --short PLAN.md pipeline/TODO.md pattern_knowledge_workbench/TODO.md LEARN_SYSTEM_TARGET.md openspec/learn-system-blackbox-architecture.md` 必须无输出；`grep -c '^- \[ \]' PLAN.md` 必须为 63。任一不符停手报告。记下 `BASE=$(git rev-parse HEAD)`。
1. `export LC_ALL=en_US.UTF-8`。运行 TDD §0 全部基线并记录原始输出。
2. 按 `act/r3-01.yaml`：断言四个锚点；**先**按 `checker` 六条规则写 `check_d16.py`，运行确认 Red；再把 `plan_section` 逐字（去掉 YAML 两格缩进）插入到 `plan_insert_before` 行之前；三处整行替换；运行 `check_d16.py` 得 `D16 OK`、ACT `verify` 全部（含两例篡改自检必须 FAIL）、TDD §1 Green、TDD §3 回归；`git add` 五个文件后按 `commit.message` 提交。
3. 按 `act/r3-02.yaml`：断言两个锚点；插入 `rows` 两行与 `note`；ACT `verify` 与 TDD §2 Green、TDD §3 回归；`git add openspec/learn-system-blackbox-architecture.md` 后按 `commit.message` 提交。
4. 两个提交。不得 `git add -A` / `git add .`。
5. 停手规则：锚点命中不为 1；PLAN 未勾选基线不是 63；`plan_section` 里任一「开头文字」在 PLAN 中匹配不到恰 1 条 `- [ ]` 行（说明主 Agent 的表有误，**不得自行改表或改 PLAN 既有行来凑数**）；`git diff $BASE -- PLAN.md` 出现任何 `-` 内容行；任一门禁变红；对 ACT 有两种理解。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：两个提交 hash 与各自 `git show --stat --oneline`；基线输出；r3-01 的 `check_d16.py` Red/Green 原文、两例篡改自检输出、`git diff $BASE --numstat -- PLAN.md`、未勾选计数 63→66；r3-02 的 TDD §2 五个值；TDD §3 回归；`git status --short`；以及一句「等待主 Agent 独立验收」。
