# IMPL-00 W5H（act/13）复审 R2（独立审查者 W4-R5）

- 复审对象：返工提交 `af17496`（docs(impl-00): fix act/13 Red expectation per review）后的 `act/13.yaml`，对照 R1（`a56ff34`）G1–G3；以 HEAD（`e2c8d79`）文本为准。
- 现状基准：act/13 **尚未执行**——`check_interfaces.py` 实测 `I00-IF SUMMARY pass=24 fail=0`、`INTERFACES.md:348` M6 行仍为旧五行（含 `correction_request`、状态「纵切后（D-14）」）、现存测试 13 个。故 R1 的 Red 预期订正以「现状推演 + 算术核验」方式复核，实际实跑取证留待 act/13 执行时按新预期进行。

## R1 发现闭合核对

- G1｜闭合｜act/13.yaml:11（tests_first）｜Red 预期改为实测口径：**Red = FAIL IF11**（M6 四类型状态列「纵切后（D-14）」，M6_TYPES 纳入 IF11 循环）**+ FAIL IF29**（§4 表出现 `correction_request`），末行 `I00-IF SUMMARY pass=27 fail=2`；IF25–IF28 因类型名已在行内而 PASS（明示「属预期」）；Green 为 `pass=29 fail=0`、IF25–IF29 五 PASS。算术对照现状核验：当前 24 项全过 → 新增 IF25–IF28（名称已在 :348 行内，各恰 1 次）→ 28 过；IF11 因 M6 四类型状态列失败、IF29 因 correction_request 在表失败 → **27 过 2 败 = 29 项** ✓；Green 替换 M6 行为四行（状态更新、无 correction_request）后 IF11/IF29 转过 → **29/0** ✓。与「在副本上实跑」的取证要求相容：执行者按此预期在 Red/Green 两点实测即可。
- G2｜闭合｜act/13.yaml:20（A 条）｜删除 `correction_request` 的依据标注改为「impl-06 D-10（A）与 §4.2 C7；第 62 条关联」——与 G7-RULINGS 第 62 条正文（仅裁 D-08）不再错位。
- G3｜闭合｜act/13.yaml:33（D 条）｜§3.4 改写补 `consumption_level(INTERNAL_DEMO|DEV_SEARCH|PUBLIC_RELEASE)` 三值闭集与 `evidence_refs[sourceSpanId]`（元素 `ss_` 前缀、`validate("source_span_id")`）——与 `review_events.py:23` 及 impl-05 act/06 V4 一致。
- 联动同步：D 条补「`target.artifact_revision_id`（恒为 seen 修订，第 68 条）」与「modify 的修改产出锚不入事件，由 M6 `decision_entry.modified_revision_id` 承载」；E 条 `reviewed_edition.decisions` 增 `modified_revision_id`——与 impl-06 返工（479d44e）及第 68 条逐字一致，两包契约无漂移。
- 其余维持 R1 结论：A–K 各条、写范围（仅 INTERFACES/check_interfaces/tests）、单写者 P2、IF01–IF24 冻结、第 54 条 fail=0 形式、时长 60 ≤ 110、用例 18 = 现存 13 + 新增 5。

## 判定

**READY**（G1/G2/G3 全部闭合；Red/Green 数值经现状推演核验自洽；与 impl-06 返工的第 68 条联动同步无漂移；无新问题。act/13 可按订正后的预期执行，执行时以实跑 Red `27/2`、Green `29/0` 取证。）

（审查者：W4-R5；以 HEAD `e2c8d79` 只读核查；`git diff --check` 无输出。）
