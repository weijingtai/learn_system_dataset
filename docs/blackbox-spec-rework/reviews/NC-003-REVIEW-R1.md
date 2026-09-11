# NC-003 转译审查记录

## R1（2026-09-11，Sonnet 独立审查，只读；对象 `0fce3d3`）：返工 6 项
1. 「8 处断言」不实 → 实测 14 行；2. 「35 处 operation 级 headers」不实 → PyYAML 按 `paths.*.<method>` 复算为 22 个 operation（全部）；3. 契约 §4.2 `type` 与 `xuan/errors.py` `_L0_MAP` 真实 L0 集合不符；4. §7 的 410 用 `full=true` 收窄，偏离 DESIGN §7.4；5. 缺 `conflict.access_version` 与「原始 applied_version 对当前状态」正反例；6. act/02 体量偏紧。建议：D-NC003-12 登记 forbidden.not_owner 扩展；guard 运行时机注明。
落实（`11b9267`）：计数勘误同步 DESIGN §7.4 与 TASKS；§4.2 逐字按 `_L0_MAP`；§7 改为同键重放过期才 410、R5 恒 200；示例集 8 个；act/02 拆为组件/端点两步（5 ACT，全量 +65）；D-NC003-12；act/05 守卫只在提交后跑一次。

## R2（2026-09-11，Sonnet；对象 `11b9267`）：返工 1 根因 3 落点
二～六查与另核全部通过（22 个 operation、`_L0_MAP` 映射、410/503 语义与 B26/B27、示例集 8 个、5 ACT 估时与计数 52/55/58/63/65、`nc003_guard.sh` 0、D-NC003-12、模糊词零命中）。唯一问题：14 行断言按所在 `test(` 分箱为 **10** 个块（138/152/208/230/284/298/310/323/333/343），非 12；其余为 9 个测试，非 7；契约 §8 表仍有旧「8 处/11 个」措辞。

## R2 落实与 R3（主 Agent，同日）
用脚本按 `test(` 起始行分箱自证（19 个块，命中 10 个，其余 9 个），把契约 §1.1/§3.1/§8、README、BDD B04、TDD、act/01、ACCEPTANCE、PROMPT、TASKS 勘误行全部改为 10/9；grep 残留为 0；守卫 0。判定：READY，5 个 ACT 可开工。
