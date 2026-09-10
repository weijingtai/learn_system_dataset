# T-10 Executor Prompt

你是 T-10 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t10/README.md`
- `docs/blackbox-spec-rework/work-items/t10/BDD.md`
- `docs/blackbox-spec-rework/work-items/t10/TDD.md`
- `docs/blackbox-spec-rework/work-items/t10/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 4 FAIL，T-10 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 的 `§10 M2 Digitization & Correction` 末尾（在 `## 11. M3 Corpus Compilation` 之前），新增子节「10.1 异常页终态枚举与 M2 Gate 放行规则」：
   - 明确定义异常页的三种终态枚举：
     1. `manually_transcribed`（人工转录完成）：由人工校订介入完成文本录入与校准；
     2. `known_unrecognizable`（已知客观不可识别）：如纯图无文字页、手绘盘面页或严重残卷（证据见 `ocr/data_work/logs/anomalies.jsonl` 中登记的 page_002 无文本、page_010 盘面页），**必须附理由与证据 Artifact，严禁裸标**；
     3. `deferred`（暂缓处理/未决）：暂未处理或等待后续工具链支持（如弧线字切分原型 `ocr/experiments/curve_segment.py` 生产化），保持未决状态。
   - 明确 M2 Gate 放行与阻断规则：
     - `manually_transcribed` 与 `known_unrecognizable` 允许 M2 Gate 放行；
     - `deferred` 严格阻断 M2 Gate 通过，禁止进入 M3；
     - 规则声明：此放行规则与 `§6.1「失败为零」`不冲突，因为「客观不可识别」属于已受控登记的输入边界局限，不是加工流程执行失败；
     - 严禁将任何异常页静默跳过或绕过 Gate。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t10/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 4 严格减少至 3，且 T-10 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: define anomaly page terminal states for M2`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、三种终态与 Gate 放行规则核验对照及全局 T 结果。
