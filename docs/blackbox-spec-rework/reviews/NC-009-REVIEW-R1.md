# NC-009 转译审查记录

## 主 Agent 自审（2026-09-11，审查子代理额度中断期间；`caa517d`）
修正五项：随机假名映射（§11.3）、W1 重新发布 If-Match（对齐 NC-002 fixture）、事务外固定对象 ID、500 state_corrupted、R2-05 移交 NC-011；§9 NC-003 前置补丁（后合入 NC-003 act/06）。

## R1（2026-09-11，Sonnet 独立审查；对象 `caa517d`）：返工 3 项 + 2 建议
① `event_id` 被归入随机 `new_ids`，违反 DESIGN §11.2 确定性哈希；② 契约 §6 仍写 7 集合/56 断言，与 §2.2 的 8 集合及 BDD/TDD 不一致；③ README 基线占位、VERIFICATION 写「0 failed」而实测 411 passed / 5 个既有失败。建议：他人对不可读内容写入应按 §7.3 边界返回 404；`forbidden.not_owner` 覆盖 publish 需登记。自审修正五项均核实正确（含 B30 在 google-cloud-firestore 2.30.0 下可实现、RULES 仓默认拒绝与测试骨架、Emulator 可达、依赖链与计数一致）。

## R1 落实（主 Agent，同日）
③ 已于 `a6dbdc5` 落地（审查读取的是之前的状态）。① `ids.server_event_id` 按 §11.2 公式并复用 `community_hash.encode`，从 `new_ids` 剔除，create-if-absent 写入，B30 断言事件 ID 等于公式（D-NC009-14）。② §6 改为 8 集合逐一列名、64 + 1 = 65 断言。建议采纳：存在性与归属合并判定并置于版本/生命周期之前，他人可读 403（含他人对公开内容 W1）、不可读 404 共用体（D-NC009-13），B04 与测试名 `other_scope_write_is_403_when_visible_404_when_not` 同步。待 R2。
