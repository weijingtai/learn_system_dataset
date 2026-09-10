# T-11 主 Agent 验收清单

状态：`REWORK_REQUIRED`（R1，2026-09-09）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `4deb1ce`，+11 -3）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: correct gap table with measured metrics and missing items`

## 2. Gap Table Metrics & Items Verification

- [x] M1 补充 `pipeline/registry/works/`、`tools/ingest_epub.py` 与不可重放差距
- [x] M6 补充 496 rules，original_text 非空 0，is_verified=1 为 0 等实测数字
- [x] M8 写入 148 span 塌缩为 18 键碰撞事实
- [x] 补充 8 项工程遗漏，附对应判据命令
- [x] §19 表格行数达到 21 行以上（实际 29 行）
- [x] 未将「pipeline 无依赖声明」写入遗漏

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t11/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 3 严格降为 2
- [x] `T-11` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`REWORK_REQUIRED`。路径、私有依赖、数据安全缺陷和测试数量存在过时或错误事实，门禁未验证逐行真实性；返工项见 `../../reviews/G3-REVIEW-R1.md`。
