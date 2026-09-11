# G4 第三批：D-16 PLAN 映射与唯一 owner ＋ `pat_`/`ent_` 前缀登记

状态：`READY`（2026-09-11 主 Agent 四查通过，待用户交外部 Agent；C/S 会话已给 `PLAN.md` 时间窗：NC-004 验收完成之前）

## 1. 目标

- **r3-01（D-16）**：在 `PLAN.md` 只增不删地加入一节「黑箱差距 → PLAN 条目 → owner 映射」：§19 主表 19 行每行有归属；本文件 63 条未勾选项每条标 `mapped / superseded-by / out-of-scope`；为 §19 中没有既有条目的三行（Artifact Ledger、Local Orchestrator、M7）新增登记；`KnowledgeReleaseCompiler` 四处重复登记收敛到唯一 owner `pipeline/TODO.md` P2 第 1 条，其余三处改为引用。
- **r3-02**：把用户 2026-09-11 确认的 `pat_<technique>_<6位数字>` 与 `ent_<32hex>` 登记进规格 §8.1 第 3b 节表（登记册 `openspec/id-prefix-registry.md` §3.4 已由主 Agent 改为「已确认」）。

## 2. 依据

- `docs/blackbox-spec-rework/D-design.md` §D-16：绝对禁令「不得删除 PLAN.md 中任何未勾选项」；三列映射表；每条既有未完成项三选一标注；重复登记收敛；判据 `git diff PLAN.md | grep "^-" | grep -c "^-- \[ \]"` = 0。
- `openspec/id-prefix-registry.md` §3.4（已确认）与 §4 规则 4「先登记后使用」。
- 用户决定：2026-09-11「关于那个登记的 3.4，这个是可以的」。

## 3. 范围

写：`PLAN.md`（只插入一节，零删行）、`pipeline/TODO.md`（P2 第 1 条整行替换）、`pattern_knowledge_workbench/TODO.md`（第 17 行整行替换）、`LEARN_SYSTEM_TARGET.md`（第 258 行整行替换）、`openspec/learn-system-blackbox-architecture.md`（§8.1 第 3b 节表尾插入两行 + 表后一句）。

禁止：删除或改写 `PLAN.md` 任何既有行；碰 `PLAN.md` G6 及注解社区各节；改 §19/§20/§22；改 `openspec/id-prefix-registry.md`；改 Schema、`verify-T.sh`、`mutations.sh`、`openspec/schemas/verify.sh`；`git add -A`。

## 4. 输入（主 Agent 2026-09-11 于 HEAD 实测）

- `PLAN.md` 未勾选项 63 条（本批派发前主 Agent 已勾掉「用户确认 `pat_`/`ent_` 前缀」一条）；其中黑箱相关 43 条逐条列于 ACT 表 B，G6/NC 各节 20 条以一句归 `out-of-scope`。
- §19 主表 19 行（首列名逐字见 ACT 表 A）。
- `KnowledgeReleaseCompiler` 登记处：`PLAN.md`「实现发布级 KnowledgeReleaseCompiler…」、`pipeline/TODO.md:24`、`pattern_knowledge_workbench/TODO.md:17`、`LEARN_SYSTEM_TARGET.md:258`。
- §8.1 第 3b 节表现 3 行（sch_/sv_/cg_），规格内 `pat_<technique>` 与 `ent_<32hex>` 均 0 命中。

## 5. 决定

- 标注含义：`mapped` = 有 §19 差距行或 owner 文件承接、继续有效；`superseded-by` = 已被所列提交/章节完成或取代，勾选由主 Agent 事后凭证据做，本 ACT 不勾；`out-of-scope` = 不在 §22 本阶段范围，保留不删、不派发。
- 三行新增登记以 `run_all.sh 20.N` 由 BLOCKED 变 PASS 为判据，避免再写散文标准。
- 勾选 R1 返工项等已完成条目不属于本 ACT（会触碰「零删行」判据），由主 Agent 在验收后单独提交。
