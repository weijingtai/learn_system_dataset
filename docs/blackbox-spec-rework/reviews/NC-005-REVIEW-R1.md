# NC-005 工作包审查 R1/R2（wjt-react 四查）与返工落实

日期：2026-09-11。审查对象：`73bbd1b`。审查人：独立只读 Agent（Sonnet；首次 Opus 审查因会话额度中断未产出）；返工裁定与落实：主 Agent（C/S 会话）。守卫：`nc005_guard.sh`。

## 1. R1：REWORK 3 项 + 3 建议

| # | 问题 | 落实 |
|---|---|---|
| 1（可执行性） | 契约 §6/B28 用已弃用 `textScaleFactor`，会击穿 `flutter analyze` 零 issue 闸门 | 改 `MediaQueryData(textScaler: TextScaler.linear(2.0))`；TDD/ACT FORBIDDEN/守卫扫描禁用 `textScaleFactor` |
| 2（契约内部歧义） | 「注入 Timer 工厂」未传导到禁止清单与守卫 | TDD §6、四个 ACT FORBIDDEN 禁裸 `Timer(`；守卫 K05 扫描 `Timer(` |
| 3（覆盖性） | TASKS「自动保存不改变已发布正文」无断言 | 契约 §1 不变式；BDD B31；TDD `autosave only calls saveSnapshot`；ACT DEFERRED 说明；测试 74→75 |
| 建议 | 替身用 `implements NoteRepository` 隐式接口；契约 §5.1 行号 11-19；B12 补 saving+blur/leave | 全部落实 |

忠实性与独立性 PASS：契约 §2 非法边与 SM-1 一致；§3 三态文案与 PRD §6.1 逐字节一致；§4 方案 (b)；§5.1 事实与 1.0.12 源码逐条核实。

## 2. R2（缩范围）：READY

6 条全部 CLOSED；计数 8+19+7+6=40，加 35 = 75 七处一致；B01～B31 与守卫 range 一致；`Timer(` 朴素扫描对 `TimerFactory(`/`Timer Function(` 无误报；守卫 0、`git diff --check` 0、模糊词零命中。

**决定记录：转译审查 R2：READY，4 个 ACT 可开工。** 派发前置（NC-004 ACCEPTED）已满足。执行 Prompt 为 `work-items/nc-005/PROMPT.md`。
