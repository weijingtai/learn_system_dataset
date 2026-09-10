# T-13 主 Agent 验收清单

状态：`REWORK_REQUIRED`（R1，提交 `be2c6ce`）

## 1. Scope and Commits

- [ ] 提交只修改 `openspec/learn-system-blackbox-architecture.md`
- [ ] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [ ] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [ ] 提交消息严格为 `docs: annotate section status tags across sections 3 to 18`

## 2. Section Status Tags Verification

- [ ] §3 至 §18 全部 16 个章节逐节添加状态标签
- [ ] 全文 `^状态：` 计数达到 16 处以上（实际应为 17 处）
- [ ] 全文无任何一处出现 `状态：最终规范`
- [ ] 各章节状态标签映射严格符合 BDD/TDD 规定

## 3. Evidence and Regression

- [ ] `docs/blackbox-spec-rework/work-items/t13/TDD.md` 中的全部 Green checks 通过
- [ ] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码严格为 0，FAIL 合计为 0
- [ ] `T-13` 由 FAIL 转为 PASS
- [ ] `T-13b` 保持 PASS
- [ ] `git diff --check` 通过
- [ ] 主 Agent 规格审查通过
- [ ] 主 Agent 质量审查通过
- [ ] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [ ] 主 Agent 标记 `ACCEPTED`

最终结论：`REWORK_REQUIRED`。章节级标签数量通过，但遗漏 §16 建议句的局部“讨论候选”标签，现有门禁为假绿；返工项见 `../../reviews/G3-REVIEW-R1.md`。
