# T-08 Executor Prompt（G3 R2 返工）

你是 T-08 门禁返工执行 Agent。在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支 `codex/docs/knowledge-compilation` 工作，禁止切换分支或进入其他 worktree。

先完整阅读：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`、`docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`、本目录六件套。

## 背景

T-08 正文基本正确，但 R1 门禁只查字段名与 M5 缺席，生产 Module 与归属子包完全不校验，接口只查名字出现，因此把 `concept_id` 改成 `M2 / SourceAssetPack`、只改 Module、只改 Package、把接口改成错误供给包，门禁都仍返回 0。

## 写范围

- `docs/blackbox-spec-rework/verify-T.sh`（仅 T-08 段）
- `docs/blackbox-spec-rework/work-items/t08/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

`openspec/learn-system-blackbox-architecture.md` 为只读基线，仅允许复制到 `/tmp` 做临时变异。

## 严格执行顺序

1. 确认 T-07 已提交（前一任务未提交不得启动本任务），记录起点：分支、`HEAD`、`git status --short`、`git diff --check`。
2. 在 `/tmp` 建立 Red baseline：以下四个变异在加固前必须仍返回 0，每个变异都从权威规格重新复制、只改该副本、单独运行。
   - 变异 1：把 `concept_id` 改为 `M2 / SourceAssetPack`；
   - 变异 2：任选五字段，只改成错误 Module（Package 保持正确）；
   - 变异 3：任选五字段，只改成错误 Package（Module 保持正确）；
   - 变异 4：将任一接口改为错误供给包。
3. 改 `verify-T.sh`：
   - 三接口供给子包必须精确校验：`最小盘面概念字典` → `KnowledgeDataPack`；`MarkContentBinding` → `KnowledgeDataPack` 与 `RuleIndexPack`；`EvidenceBundle` → `EvidenceMapPack`；§16.3.1 的「供给子包」行与 §1 的「由 … 供给」片段必须同时正确；
   - §16.3.2 表格：五字段各恰好一次，`生产Module|归属子包` 规范化后精确等于期望（`omen_carrying`=M4/KnowledgeDataPack；`condition_affordance`=M4/RuleIndexPack 与 KnowledgeDataPack；`school_variance_display`=M4 / M6/KnowledgeDataPack；`concept_id`=M4/KnowledgeDataPack；是否改变当前判断=M4 / M7 / M6/KnowledgeDataPack（MarkContentBinding）），生产列不得含 M5；
   - 保留：最小概念字典不含规则 DSL、Tag 的 G4 必须写成 `TAG_SYSTEM_DESIGN.md §12.2` 命名空间形式。
4. 运行正常规格门禁，必须退出 0 且 `FAIL 合计: 0`。
5. 逐一重跑四个变异，必须各自非零退出，且不得连带触发无关断言。
6. 同步六件套：删除 M4/M5 共同生产、旧 7→5 FAIL 与旧提交指令；BDD、TDD、ACT、Prompt 必须一致说明 **M5 只校验**；状态写 `IMPLEMENTED_AWAITING_REVIEW`，不得写 `ACCEPTED`。
7. 运行 `git diff --check`、`git status --short`，独立提交：`fix: enforce T-08 ownership mappings`。

## 停手条件

- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件；
- 正常规格门禁非零且失败不由本工作包造成；
- 任一强制变异仍返回 0；
- 允许文件存在他人的未提交修改。

出现任一情况立即停止并报告精确冲突，不得自行改写正文、不得自行宣布验收通过、不得启动 G4。
