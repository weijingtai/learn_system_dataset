# T-07 Executor Prompt（G3 R2 返工）

你是 T-07 门禁返工执行 Agent。在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支 `codex/docs/knowledge-compilation` 工作，禁止切换分支或进入其他 worktree。

先完整阅读：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`、`docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`、本目录六件套。

## 背景

T-07 正文基本正确，但 R1 门禁只做子串匹配，存在三处可复现假绿：追加第二归属、给非目标项追加归属、把肯定句改成否定句，门禁均仍返回 0。

## 写范围

- `docs/blackbox-spec-rework/verify-T.sh`（仅 T-07 段）
- `docs/blackbox-spec-rework/work-items/t07/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

`openspec/learn-system-blackbox-architecture.md` 为只读基线，仅允许复制到 `/tmp` 做临时变异。

## 严格执行顺序

1. 确认 D-07 已提交（前一任务未提交不得启动本任务），记录起点：分支、`HEAD`、`git status --short`、`git diff --check`。
2. 在 `/tmp` 建立 Red baseline：以下三个变异在加固前必须仍返回 0，每个变异都从权威规格重新复制、只改该副本、单独运行。
   - 变异 1：给 `query-contract` 追加 `EvidenceMapPack`；
   - 变异 2：给 `optional-vector-index` 追加「同时归入 `SearchIndexPack`」；
   - 变异 3：把取代声明中的「正式取代」改成「不得取代」。
3. 改 `verify-T.sh`：
   - §16.2 表格解析保持 15 行、每 key 恰好一次；
   - 右列改为规范化（去反引号与空白）后**精确相等**：`query-contract` = `QueryContractPack（查询契约与接口定义）`，`optional-vector-index` = `本期不产出（依据§21非目标）`；
   - 取代声明必须在同一句肯定语义中包含 `PublicationPackage`、`KnowledgeDataPack`、`正式取代`、`KnowledgePack`，出现 `不得取代` 等否定式即失败。
4. 运行正常规格门禁，必须退出 0 且 `FAIL 合计: 0`。
5. 逐一重跑三个变异，必须各自非零退出，且不得连带触发无关断言。
6. 同步六件套：删除旧的双 IndexPack 映射、旧 8→7 FAIL 口径、禁止修改门禁与旧单文件写范围指令；状态写 `IMPLEMENTED_AWAITING_REVIEW`，不得写 `ACCEPTED`。
7. 运行 `git diff --check`、`git status --short`，独立提交：`fix: enforce T-07 exact package mappings`。

## 停手条件

- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件；
- 正常规格门禁非零且失败不由本工作包造成；
- 任一强制变异仍返回 0；
- 允许文件存在他人的未提交修改。

出现任一情况立即停止并报告精确冲突，不得自行改写正文、不得自行宣布验收通过、不得启动 G4。
