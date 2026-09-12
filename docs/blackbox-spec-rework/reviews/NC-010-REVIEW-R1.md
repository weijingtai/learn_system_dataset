# NC-010 转译审查记录

## R1（2026-09-11，Sonnet；对象 `f6373b0`）：返工 7 项 + 2 建议
通过：payload_hash Python 复算一致；§3 头与路径和 REST 仓 `5730ed9` 的 openapi.yaml 一致；D-NC010-04/06 不构成上游冲突；计数自洽；reading-notes 基线实测 +150；依赖类型全部存在；守卫 0；模糊词零命中；依赖链与串行明文。
返工：① 退避 `min(2^n,60)` 无上限与 DESIGN §9.1「1s/2s/4s/8s 上限 5 次」冲突；② `hiddenByAdmin` 丢失 PRD §6.2「附申诉入口」；③ 不写已存在的 `notes.pending_op` 缺上游依据；④ DESIGN §7.4 第 5 条「超 14 天待办先查询对账」无规则无测试；⑤ 第 6 条「迟到响应不回滚 UI」无缓存版本单调规则；⑥ 验收盲测「真实关闭重开」「并发 drain 单发」未下沉为可回归测试；⑦ PRD §5.1 五个确认层只交付三个未登记决定。建议：trashed+hidden 重叠文案登记；B05 明确真实关闭重开步骤。

## R1 落实（主 Agent，同日）
① 自动重试 1/2/4/8s、5 次后 `paused`（非终态、同键、用户重试归零窗口），新增列 `auto_attempts`/`next_attempt_at`，D-NC010-07 改写，B33；② 文案附「申诉」按钮与 `AppealHandler` 端口，B37；③ 队列为来源、经 `NoteRepository.db` 回写 `notes.pending_op`、重启按队列重算，不改 NC-004 文件，D-NC010-03 改写，B35；④ §4.2 增 14 天先 R5 规则，B34；⑤ §5.1 版本单调，B36；⑥ B31 真实文件库关闭重开、B32 并发 drain 单发，ACCEPTANCE ②③ 改为核对正式测试；⑦ D-NC010-08；建议采纳 D-NC010-09 并入 B17，B05 写明关闭重开步骤。计数：act/02 14、act/03 9、act/04 7，全量 +211。待 R2。

## R2（2026-09-11，Sonnet；对象 `f3b3782`）：返工 2 项
R1 的②③④⑤⑥⑦与两条建议全部核实落地（含 reading-notes `db` 公开字段、`pendingOp` 列、`StaleSessionError` 存在；local-persistence 无「只经仓储写入」限制）；计数与 BDD↔TDD 对应一致；守卫 0；模糊词零命中。问题：① 契约 §4.2 承诺 `paused` 显示「发送失败，点此重试」，但 §6 待处理队列枚举不含 `paused` 且无测试；② ACT.yaml 估时合计 265 ≠ 分项和 275。
## R2 落实（主 Agent，同日）
§6 队列枚举补 `paused` 与点击重试规则（同键、`auto_attempts` 归 0、立即 drain），新增 B38 与 act/04 测试 `pending_queue_paused_item_retries_with_same_key`，计数 act/04 8、全量 +212；估时合计改 275。另：editor.md（NC-005）不变式「本包不存在发布接口」收窄为 `lib/src/editor` 与 `lib/src/persistence` 不含也不导入发布接口，守卫 K05 与 ACCEPTANCE 作弊扫描加导入检查。机械修正经 grep 自证，判定：**READY，5 个 ACT 可开工**。
