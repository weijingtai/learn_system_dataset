# D-07 执行 Prompt（G3 R2 返工）

你是 D-07 门禁返工执行 Agent。在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支 `codex/docs/knowledge-compilation` 工作，禁止切换分支或进入其他 worktree。

先完整阅读：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`、`docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`、本目录六件套。

## 背景

D-07 正文基本正确，但 R1 门禁存在可复现假绿：`TechniqueProfilePack` 与 `QueryContractPack` 的要素按整节 grep，`RuleIndexPack` 的逐规则版本声明没有独立校验，因此删除正文条目后门禁仍返回 0。本轮只修门禁与六件套，**不改规格正文**。

## 写范围

- `docs/blackbox-spec-rework/verify-T.sh`（仅 D-07 段）
- `docs/blackbox-spec-rework/work-items/d07/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

`openspec/learn-system-blackbox-architecture.md` 为只读基线，仅允许复制到 `/tmp` 做临时变异。

## 严格执行顺序

1. 记录起点：分支、`HEAD`、`git status --short`、`git diff --check`、正常规格门禁退出码。
2. 在 `/tmp` 建立 Red baseline：以下三个变异在加固前必须仍返回 0（证明假绿），每个变异都从权威规格重新复制、只改该副本、单独运行。
   - 变异 1：删除 `TechniqueProfilePack` 的「事实字段与枚举」整条；
   - 变异 2：把该条改成「包中不列任何事实字段与枚举；字段由客户端自由猜测」；
   - 变异 3：删除 `RuleIndexPack` 的「每条规则必须显式声明 Profile 版本及 AST schema 版本」整条。
3. 改 `verify-T.sh`：三份契约按各自导语锚点切成专属块，只在块内断言；锚点缺失或重复即 FAIL；`TechniqueProfilePack` 必须含 `FactSet Profile`、`事实字段与枚举` + 闭集枚举（拒绝否定语义）、`operator 集合`、`AST schema 版本`、禁止可执行或模型生成 Python；`QueryContractPack` 必须含四接口与向后兼容声明；`RuleIndexPack` 必须含每条规则 + 显式声明 + `profile_version` + `AST schema 版本` + `结构化 AST/YAML/JSON`；§13 必须确认 M5 在 G6 下只校验、不生产。
4. 运行正常规格门禁，必须退出 0 且 `FAIL 合计: 0`。
5. 逐一重跑三个变异，必须各自非零退出，且不得连带触发无关断言。
6. 更新六件套并写入真实证据；状态写 `IMPLEMENTED_AWAITING_REVIEW`，不得写 `ACCEPTED`。
7. 运行 `git diff --check`、`git status --short`，独立提交：`fix: harden D-07 package-specific gates`。

## 停手条件

- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件；
- 正常规格门禁非零且失败不由本工作包造成；
- 任一强制变异仍返回 0；
- 允许文件存在他人的未提交修改。

出现任一情况立即停止并报告精确冲突，不得自行改写正文、不得自行宣布验收通过、不得启动 G4。
