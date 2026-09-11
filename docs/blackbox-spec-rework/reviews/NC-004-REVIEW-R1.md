# NC-004 工作包审查 R1（wjt-react 四查）与返工落实

日期：2026-09-11。审查对象：提交 `ab11e28`。审查人：独立只读 Agent（Opus，未参与编写）；返工裁定与落实：主 Agent（C/S 会话）。守卫：`bash docs/blackbox-spec-rework/reviews/nc004_guard.sh`。

## 0. 结论

判定 **REWORK**：7 项阻断 + 3 项次级 + 7 条建议。忠实性/覆盖性/可执行性各有 FAIL，独立性 PASS。

## 1. 返工项与落实

| # | 问题 | 落实 |
|---|---|---|
| 1（契约与 DESIGN 冲突） | §5.1 去重规则 ② 恒不可达；`summaryTouched=true` 且投影全等时契约判 saved、DESIGN 判 unchanged | 重写为 ①全等→unchanged（无论 touched）②仅说明不同且未碰→unchanged ③其余→saved；新增 B24 与测试 `summary touched but identical projection is unchanged` |
| 2（可执行性） | merge 测试构造违反头校验与 FK | 改为 R1→R2 后把已存在的 R1 重新 INSERT 回 `note_heads` 构成双头 |
| 3（可执行性） | FailingExecutor 拦不到事务内语句 | 改用 Drift 官方 `QueryInterceptor`（覆盖五个 run*），先断言 `SaveFailed.cause` 为注入异常再断言回滚；未拦截即停止 |
| 4（忠实性） | README 缺 outbox 二选一 | README 新增「outbox 二选一」节：选择 A |
| 5（契约内部歧义） | 严格扫描器规则未写死 | §6 写死 (a) 字符串态不检查 (b) 裸字面量 (c) 数字 token (d) 对象栈递归重复键；新增正例测试 B27 |
| 6（契约内部歧义） | Note 字段与 §1.1 不一致 | §3 列出 Dart `Note` 字段清单，`headRevisionIds` 由 `note_heads` hydrate，`updatedAt` 为本地列 |
| 7（忠实性） | 文件名与 TASKS 不符 | 拆为 `note.dart`、`note_revision.dart`（D-NC004-08）；README 登记偏离 |
| 8 | 时钟格式无测试 | 新增 B25 与 `timestamps come from injected clock` |
| 9 | mergeHeads 事务未定义 | §5.1 第 7 条补四步 |
| 10 | 会话代数适用范围两处不一致 | 统一为全部公开方法（含只读）；B19 同步 |
| 建议 | 131→35 处真文件；ESTIMATE 偏低；ArgumentError 越界；title/summary 长度；example；ncommits；memory 措辞 | act/01 拆出 act/02（扫描器），五步 250 分钟；新增 `MentionCountExceeded`/`FieldLengthExceeded`（D-NC004-05）与 B26；`example/` 推迟 NC-010（D-NC004-09）；守卫恰 5 提交、memory 0 处 |

测试总数 8+4+12+6=30 → 7+2+4+14+8=35。

## 2. 完成标准

`nc004_guard.sh` 与 `git diff --check` 均 0；第二轮审查由另一位未参与者缩范围复核本节 17 项与 `ab11e28..HEAD` 的回归。

## 3. 第二轮审查（R2，2026-09-11）：READY

审查人：另一独立只读 Agent（Opus，缩范围）。R1 的 10 项 + 7 建议全部 CLOSED；去重规则四组合（投影全等/仅说明不同 × touched 真/假）无遗漏无重叠且与 DESIGN §7.2 逐句一致；`QueryInterceptor` 五个方法名与 drift 2.31.0 源码逐字一致，事务内 INSERT 经 `_InterceptedTransactionExecutor` 必被拦截；测试计数 7+2+4+14+8=35 七处一致；`ab11e28..75633ad` 无新矛盾；守卫 0、`git diff --check` 0、模糊词零命中。8 条非阻断建议已由主 Agent 落实（`runBatched` 判定写法、B13～B15 标签对齐契约编号、merge 测试第二次保存须正文不同、TDD §4 标题、`openScoped` 注入形状、act/05 期望 +35、README 35 处措辞；N8 保留 `WRITE_NEW` 键并以「追加」注明）。

**决定记录：转译审查 R2：READY，5 个 ACT 可开工。** 执行 Prompt 为 `work-items/nc-004/PROMPT.md`，由用户交外部 Agent；主 Agent 按 ACCEPTANCE.md 验收。
