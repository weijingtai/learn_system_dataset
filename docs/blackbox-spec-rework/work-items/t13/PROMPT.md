# T-13 Executor Prompt

你是 T-13 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t13/README.md`
- `docs/blackbox-spec-rework/work-items/t13/BDD.md`
- `docs/blackbox-spec-rework/work-items/t13/TDD.md`
- `docs/blackbox-spec-rework/work-items/t13/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 1 FAIL，T-13 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 为 `§3` 到 `§18` 的每个二级章节标题下一行添加状态标签：
   - 格式统一为：在二级标题（`## X. ...`）的下一行单独起行写入 `状态：<四态之一>`，后空一行再接正文。
   - 具体各章节状态映射（严禁自由发挥）：
     - `## 3. 书籍、版本与载体` → `状态：讨论候选`
     - `## 4. Pattern（格局）` → `状态：待验证假设`
     - `## 5. 总体组织` → `状态：已确认设计`
     - `## 6. 两种运行` → `状态：已确认设计`
     - `## 7. 统一 Module Interface` → `状态：待验证假设`
     - `## 8. Package 公共结构` → `状态：待验证假设`
     - `## 9. M1 Source Intake` → `状态：讨论候选`
     - `## 10. M2 Digitization & Correction` → `状态：待验证假设`
     - `## 11. M3 Corpus Compilation` → `状态：待验证假设`
     - `## 12. M4 Knowledge Extraction` → `状态：待验证假设`
     - `## 13. M5 Automatic Validation` → `状态：待验证假设`
     - `## 14. M6 Review & Curation 与 Review Console` → `状态：待验证假设`
     - `## 15. M7 Incremental Knowledge Assembly` → `状态：讨论候选`
     - `## 16. M8 Dataset Compilation` → `状态：待验证假设`
     - `## 17. Artifact Ledger` → `状态：待验证假设`
     - `## 18. 双图与 Graph 无损要求` → `状态：已确认设计`
   - **铁律约束**：**绝对禁止给任何一节标注为 `最终规范`**。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t13/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（**FAIL 数必须降为 0！**）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: annotate section status tags across sections 3 to 18`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、16 节状态标签逐项核验结果以及全局 T 脚本最终 0 FAIL 完整输出。
