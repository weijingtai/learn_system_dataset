# T-05 Executor Prompt

你是 T-05 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t05/README.md`
- `docs/blackbox-spec-rework/work-items/t05/BDD.md`
- `docs/blackbox-spec-rework/work-items/t05/TDD.md`
- `docs/blackbox-spec-rework/work-items/t05/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 10 FAIL，T-05 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 写入以下两处修改：
   - **位置 1（`§11 M3 Corpus Compilation` 末尾）**：
     增加子节「11.1 证据级别枚举（evidence_level）与发布约束」：
     - 依据 `pipeline/DATASET_ACCEPTANCE_STANDARD.md §4-G3` 与 `LEARN_SYSTEM_TARGET.md:140`，语料切片与证据链锚点建立两档 `evidence_level` 枚举：
       - `offset_level`（通用档）：每个 span 必须包含 source offset（或等价确定性 anchor）以及 quote hash；属于开发级证据，只可用于 `INTERNAL_DEMO` 与 `DEV_SEARCH`；
       - `glyphbox_level`（扫描档）：在 offset 与 quote hash 基础上，追加扫描页、图像哈希和 OCR 字框范围（四点坐标）；属于最终无损证据链，`PUBLIC_RELEASE` 必须达到 `glyphbox_level`（依据 TARGET:140：「纯文本引用只能算开发级证据，不能算最终无损证据链」）。
   - **位置 2（`§13 M5 Automatic Validation`）**：
     在 G3 门禁对接描述中追加对 `evidence_level` 的判定规则（目标消费级别为 `PUBLIC_RELEASE` 时必须满足 `glyphbox_level`，`offset_level` 仅限内部与开发检索）。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t05/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 10 严格减少至 9，且 T-05 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: define evidence_level enum and release constraints`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、两处修改核验对照及全局 T 结果。
