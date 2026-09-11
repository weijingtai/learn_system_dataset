# NC-001-01 执行提示

发送前提：wjt-react 四查判定 READY，且主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把下面分隔线以下的全文原样发给执行 Agent。

---

你在 `/Users/jingtaiwei/Git/Public/learn_system` 的当前工作树执行 NC-001-01：实现集成基线校验器。其他 Agent 在同一工作树并行工作，不要回退、暂存或提交任何不属于你的改动。

**先读（按顺序）**：`AGENTS.md`；工作包目录 `docs/blackbox-spec-rework/work-items/nc-001/` 下的 README.md、VALIDATION_CONTRACT.md、BDD.md、TDD.md、ACT.yaml、act/01.yaml、act/02.yaml、act/03.yaml、act/04.yaml、ACCEPTANCE.md。

**只允许写**：`openspec/annotation-community/tools/check_integration_baseline.py` 与 `openspec/annotation-community/tools/test_check_integration_baseline.py`；允许且仅允许新建目录 `openspec/annotation-community/tools/`。

**禁止**：修改工作包、契约、`integration_baseline.json`、`INTEGRATION_BASELINE.md`、四份规格与既有守卫、PLAN.md、HANDOFF.md、SUBAGENT_TODO.md；写入任何外部仓库；读取凭据、连接 Emulator 或访问网络；安装依赖；创建 `reading-notes` 目录；读取外部文件内容（只允许判断路径是否存在）。

**步骤**：严格按 act/01 → act/02 → act/03 → act/04。每步先写该步的测试，按 TDD §4 取得真实断言失败（Red），再实现（Green），再运行该 ACT 的 VERIFICATION 全部命令。act/03 必须把 TDD §3.1 的 103 条路径逐字抄成模块顶层 `REQUIRED_KEY_PATHS`。

**共享守卫**：`review_v1_5_guard.sh`、`verify.sh`、`git diff --check` 读取共享工作树，并行的 G3 线可能让它们失败。失败时先 `git diff --stat`；失败来源不在你的两个文件之内的，判为外部失败，写进报告即可，不返工、不停工。`nc001_r2_guard.sh` 的 K01 失败同样按外部失败处理；其 K02～K11 失败仍按本任务失败停工。

**提交**：每步一个提交，只 `git add` 上面两个文件。提交消息按各 ACT 的 COMMIT_MESSAGE：`feat(nc-001): 集成基线校验器 CLI 与顶层规则`、`feat(nc-001): 集成基线校验器对象规则（一）`、`feat(nc-001): 集成基线校验器对象规则（二）`、`feat(nc-001): 集成基线校验器 integrated 档`。

**停止条件**：命令结果与 TDD 期望不符，且不是你的实现错误；契约有两种以上解释；需要写允许范围之外的文件。停止时报告失败命令、退出码与原文，不自行修改契约或期望。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败断言原文；
3. Green：VERIFICATION 每条命令的退出码与输出末 20 行；
4. 步骤 4 另附：integrated 命令的完整 stdout，以及 `bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh --require-impl` 的退出码；
5. 跳过项、未运行项与剩余风险。

integrated 对当前快照退出 1 是必须保留的负例，不要把它报告成失败；也不要把本任务说成 NC-001 总项完成。
