# T-13 主 Agent 验收清单

状态：`ACCEPTED`（R1 返工）

## 1. Scope and Commits

- [x] 提交只修改白名单文件：规格、`verify-T.sh` 与本验收单
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改其他工作包文档、TODO.md、PLAN.md、HANDOFF.md 或业务代码
- [x] 提交消息使用 T-13 返工语义

## 2. Section Status Tags Verification

- [x] §3 至 §18 全部 16 个章节逐节添加状态标签，并由章节号→状态闭集断言校验
- [x] 全文 `^状态：` 计数达到 18 处
- [x] 全文无任何一处出现 `状态：最终规范`
- [x] §16「建议一个 Technique 一个 Release」附近独立局部标签为 `状态：讨论候选`
- [x] 删除局部标签后门禁退出码为 1

## 3. Evidence and Regression

- [x] 新增结构门禁通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码严格为 0，FAIL 合计为 0
- [x] `T-13`、`T-13a`、`T-13b` 全部 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [ ] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新（由后续总验收统一处理）
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`ACCEPTED`。局部候选标签已补齐，章节映射与负向变异门禁有效。
