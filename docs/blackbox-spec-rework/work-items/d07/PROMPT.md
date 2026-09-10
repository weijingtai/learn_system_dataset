# D-07 执行 Prompt

你正在执行黑箱架构规格 R1 返工序列中的 **05 D-07**：TechniqueProfilePack 与 QueryContractPack。

## 目标

在 `openspec/learn-system-blackbox-architecture.md` 中完整定义两个新增发布子包及查询与规则规约：
1. `TechniqueProfilePack`：FactSet Profile、事实字段与枚举、operator 集合、规则 AST schema 版本；
2. `QueryContractPack`：定义 `getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts` 四个只读查询接口及兼容声明；
3. `RuleIndexPack`：每条规则显式声明所依据的 TechniqueProfile 版本；
4. 规则纯声明式结构化 AST/YAML/JSON 表达，禁止可执行 Python；
5. M5 依据 G6 增加规则对 FactSet 可执行性校验，明确 M5 仅做校验，不生产 Tag 字段。

## 严格执行顺序

1. 查阅权威打底：
   - `DATASET_ACCEPTANCE_STANDARD.md §4-G6`
   - `LEARN_SYSTEM_TARGET.md §7`
   - `docs/blackbox-spec-rework/D-design.md` §D-07
2. 在 `docs/blackbox-spec-rework/verify-T.sh` 中增加针对 D-07 的语义断言；
3. 执行 `bash docs/blackbox-spec-rework/verify-T.sh` 确认旧规格为红（Red）；
4. 修改 `openspec/learn-system-blackbox-architecture.md` 补全规格；
5. 执行 `bash docs/blackbox-spec-rework/verify-T.sh` 确认转绿（Green）；
6. 制作临时副本执行负向变异测试，验证删除任一接口或字段时门禁必须生效失败；
7. 运行 `git diff --check` 确保格式无误；
8. 检查 `git status` 确认未触碰任何未授权文件；
9. 独立提交并记录证据至 `docs/blackbox-spec-rework/work-items/d07/ACCEPTANCE.md`。
