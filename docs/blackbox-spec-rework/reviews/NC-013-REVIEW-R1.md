# NC-013 四查审查（R1 → R2）

## 审查者与独立性

R1 审查者未参与 NC-013 交付物编写；本机 subagent 与编写者同为 ZCode 平台不同会话，厂商口径（E1）已在交付说明中向用户标注，待用户最终裁定；若用户裁定需异厂商，R1 结论需重跑。R2 复核由另一独立会话执行，未复用 R1 结论之外的信息。

## R1 判定：REWORK

阻断项：

- **F1**（计数族 29→30/567→568，守卫 K06 机械锁定）
- **F2**（契约 §11 与 §3.4/§4.1/BDD S01 矛盾）
- **F17**（act/03 文件数 6/7 自相矛盾）

同轮修复项：

- **F3**（S19 退避边界）
- **F8**（nmute_ 未登记 DESIGN §2.1）
- **F9**（契约悬空引用「（§10.3）」）
- **F14**（守卫 exactly-once 扫描缺口）

R1 通过项：参考值 3 组实机复算 MATCH、19 处行号抽查属实、三仓基线实跑复现、覆盖性/独立性通过。

## R1 返工落实

7 项（F1/F2/F17/F3/F8/F9/F14）全部落实，另含 2 处必要派生（守卫 K03 计数串同步至 `5 failed, 568 passed, 3 xfailed`、K06 标签同步「30 个测试名」）。落点证据：契约 `openspec/annotation-community/contracts/community_deliveries.md:149/151/207/231`、`DESIGN.md:80`、守卫 `nc013_guard.sh:83/95/133-134/147/149`。

两守卫规格跑均为 0（2026-09-12 实跑）：

- `bash docs/blackbox-spec-rework/reviews/nc013_guard.sh` 末行原文：`NC-013 失败条数：0`
- `bash docs/blackbox-spec-rework/reviews/nc012a_guard.sh` 末行原文：`NC-012a 失败条数：0`

## R2 判定：READY

| # | 复核项 | 结果 | 证据（文件:行 / 命令输出原文） |
|---|---|---|---|
| 1 | 契约 community_deliveries.md 七子点 | PASS | §9：`community_deliveries.md:149` 期望 `5 failed, 568 passed, 3 xfailed`、`:151`「测试名（逐字，30 个）」；§11：`:207`「触发器薄壳在 `dispatch_outbox_event` 后立即执行一次 `advance_deliveries`；测试断言 `advance_deliveries` 首试后…」，全文 grep「dispatch_outbox_event 返回后」零命中；§14②：`:231` `+0.9/1.9/3.9/7.9s（四档均不到期）与 +1.0/2.0/4.0/8.0s（四档均到期，退避 1/2/4/8）` 配对；§6.3：`:131`（community_api §13.5）；§15：`:256` D-NC013-15（nmute_）；§4.1：`:102` `data={... "event_count": <窗口内同类事件数，首试=1>}`；全文 grep「§10.3」零命中 |
| 2 | DESIGN §2.1 前缀表 NotificationMute 行 | PASS | `DESIGN.md:80` `\| NotificationMute（服务端内部对象，NC-013 D-NC013-15） \| nmute_ \| nmute_<32 hex> \|` |
| 3 | 六件套计数与口径 | PASS | `README.md:14`「新增 30 测试」；`TDD.md:9`（§1 568）、`:87`（§6 `5/568/3`）、`:61`「追加后 11 个」+`:77`「前 19 + 后 11 = 30 个测试」；`BDD.md:38`（S19 前组 0.9/1.9/3.9/7.9 四档不到期 + 后组 1.0/2.0/4.0/8.0 四档到期）、`:36`（S17 含 event_count）；`act/03.yaml:41`（VERIFICATION 第 1 条 568）、`:42`（第 2 条「期望恰 7 个文件」）；`ACCEPTANCE.md:10`（§3 568） |
| 4 | nc013_guard.sh 静态 + 规格跑 | PASS | `:147` tuple `("5", "568", "3")`；`:83` K02 标签「30+4 测试名」；`:149` K06 标签「30 个测试名」；`:133` src 拼接两份新文件（notification_dispatch.py + community_deliveries.py）+ `:134` `ok &= not exactly_once`（连同 `t` 即三新文件）；规格跑末行 `NC-013 失败条数：0`（退出码 0） |
| 5 | nc012a_guard.sh 规格跑 | PASS | 末行 `NC-012a 失败条数：0`（退出码 0）；K05 manifest 同步 ≥17（`nc012a_guard.sh:109/120`，D-NC013-10） |
| 6 | 模糊词零命中 | PASS | `grep -rn '适当\|优雅\|合理\|必要时\|酌情\|尽量\|大致\|视情况' docs/blackbox-spec-rework/work-items/nc-013/ openspec/annotation-community/contracts/community_deliveries.md` 无输出（exit 1，零命中） |
| 7 | 残留旧计数零命中 | PASS | `grep -rn '567\|29 个测试名\|29+4\|追加后 10 个\|新增 29 测试' docs/blackbox-spec-rework/work-items/nc-013/ docs/blackbox-spec-rework/reviews/nc013_guard.sh openspec/annotation-community/contracts/community_deliveries.md` 无输出（exit 1，零命中） |
| 8 | K06 扫描为验收期行为、规格跑不受文件缺失影响 | PASS | `notification_dispatch.py` 尚不存在；扫描代码（`:130-134` read/src）整体位于 `:126` `if "server" in req:` 分支内，规格模式 `req` 为空走 `:151` SKIP 分支；实跑输出 `SKIP  K06 SERVER 产物（验收时 --require-impl server，必须 PASS）` 且退出码 0，未因文件缺失而崩 |

守卫原始输出末行（2026-09-12 实跑）：

```text
NC-013 失败条数：0
NC-012a 失败条数：0
```

## 备注

F12/F22 已随手或留作实现期提示，不阻断。另记（不阻断、未列入 R2 检查项）：`DESIGN.md` §2.1 导语仍为「本期新增 17 类对象的前缀如下」，nmute_ 登记后表实为 18 行，导语计数与 D-NC013-15「原为 17 类闭集」表述并存，留作实现期随手指正。
