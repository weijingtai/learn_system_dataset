# I 波轨道 2 回报（ACT 30，分支 m7/i-gate）

执行机器：Windows 11（另一台机器），分叉点 `m7/i-base` @ `53a9107`。
执行方式：原计划把编码外派给 Freebuff（DeepSeek V4.1 Flash，tmux 里跑），并只给它一个去掉引擎模块的沙箱副本；
本机权限策略把「把私有仓库内容交给第三方服务」判为数据外泄并拦下，所以**全部由本会话直接完成**，没有外派。
独立性：实现只凭 CHARTER §25/§28/§29、README §6 与 ACT 30；未打开 incremental.py / apply.py / orchestrate.py / matcher.py 的对勘实现。

## 1. 环境与基线

- Python 3.14.7（≥3.11），`.venv` 按任务书装 `pyyaml jsonschema pydantic ruamel.yaml check-jsonschema`。
- Windows 适配（均不进提交，主 Agent 已认可）：
  - 仓库本地 `core.autocrlf=false`、`core.eol=lf` 后重新检出（系统级 autocrlf=true 会把金标变成 CRLF）。
    重新检出用了一次 `git rm --cached -r . && git reset --hard`——当时尚未读到 AGENTS.md 的禁令；
    是刚 clone 的干净副本，无任何改动丢失。此后不再使用。
  - `pipeline/ledger/lock.py` 需要 `fcntl`：在仓库外（scratchpad）放一个用 `msvcrt.locking` 实现 `flock` 的垫片，经 `PYTHONPATH` 注入。
  - `.venv/bin` 做成指向 `.venv/Scripts` 的目录联接（shell 脚本写死 `.venv/bin/python`）。
- 基线（未改代码）：

```
Ran 229 tests in 157.738s
FAILED (failures=5, skipped=2)
```

5 条失败全部是「本机无 `var/ledgers/qianyuan_w8` 真书账本」导致（主 Agent 裁决：接受为环境基线，单列为 A 组）：

1. `test_acceptance.TestAcceptance.test_blocked_lines_exact_text` — 输出含 `BLOCKED upstream_m6_real_book 宿主缺失: 无真书账本`
2. `test_acceptance.TestAcceptance.test_genesis_acceptance_summary_and_exit_2` — 期望 `pass=16 fail=0 blocked=1`，实得 `pass=15 fail=0 blocked=2`
3. `test_acceptance.TestAcceptance.test_shell_returns_2` — 同上
4. `test_acceptance.TestAcceptance.test_shell_summary_pass_16_fail_0_blocked_1` — 同上
5. `test_acceptance.TestAcceptance.test_upstream_m6_real_blocked_until_impl06_accepted` — `startswith("BLOCKED upstream_m6_real")` 命中了 `BLOCKED upstream_m6_real_book`（主 Agent 确认是测试缺陷，由主 Agent 修）

## 2. 口径裁决（已全部落定）

读完 ACT 30 / §25 / README §6 后向主 Agent 提了 11 条（Q1–Q11）+ 2 条假设 + 1 条推论，全部已裁定并写进
CHARTER §28、§29（`m7/i-base` 依次推到 25969a4 → 6891280 → 3408465，均已并入本分支）。本实现严格照 §28/§29：

- 完整性覆盖四类 + R07b 落点：每个可比单元恰一条关系 ∈ {alignment, variant_reading, addition, omission, distinct_from(human)}（Q1/Q2）
- subject 两端都非空且相等才算同一对象；只约束 mode=auto 的 alignment/variant_reading；mode=human 不验 subject（Q3 + 推论）
- 新 knowledge 的 `editions[视图 source].collation_units` == 视图声明（仅 `{collation_key, present}`、升序、不含 null 键）；其他 source 条目与基底逐字节相同（Q4）
- 视图一侧只认 `collation_units`；有键未声明 → `view_undeclared`（Q5）
- 闭包触点 (a)(b)(c)（Q6）
- not_comparable 清单在 `edition_collation_set.not_comparable`，每项恰 `{source_id, collation_key, assertion_id, reason}`，按 `(source_id, collation_key or "", assertion_id or "")` 排序；Gate 与判据都独立算、逐项比（Q7 + 补充、Q11）
- 同侧同键 >1 条获批断言 → `multiple_assertions_per_unit`，零关系（假设一）
- 涉及视图 source 的关系按本轮角色重算、逐个基底版次算完整性；不涉及视图的关系与基底逐字节相同（Q8）
- 基底缺 `collation_units` 不开口子，Gate 仍判 FAIL（Q9）
- 两端都是断言且 detail 带 `collation_key` 的 distinct_from 才归对勘管（Q10）

本实现自定、未单独请示的一处：「获批断言」一律只数 `reviewed_edition.approved` 里 kind=assertion 的（视图侧），
未获批的视图断言不参与单元判定，也不进 not_comparable 清单。

## 3. Red（先写测试，Gate 未改）

`pipeline/assembly/tests/test_gate_collation.py`（31 个用例，含子用例；ACT 30 列的 15 个具名用例全在，
另加 §28/§29 口径用例：null 主体、方向反转、detail 键错、重复关系、多断言单元、视图未声明键、三版次逐对完整性、
带过来的关系逐字节、R07b 两种落点、editions 写入一致、not_comparable 清单逐项）。输入全部手工构造成 §25 形状。
每条篡改用例断言三件事：`collation_comparable_only` passed=False、总体 passed=False、失败理由含实指标记（如「自环」「完整性」「不可比」）。

对未改的 Gate 跑：

```
Ran 31 tests in 0.055s
FAILED (failures=38)
```

5 个正向用例（四类齐全、三版次、多断言单元无关系、R07b 两种落点）在旧 Gate 上就是绿的——说明手工世界本身让 13 项全过；
`test_tamper_omission_but_view_actually_present` 旧 Gate 已能抓到（旧口径也拒「两侧都 present 的 omission」）。
其余全红。三条探针对应用例的 Red 原文（旧 Gate 放行）：

```
test_tamper_self_loop:                           AssertionError: True is not false : collation_comparable_only 未转红: 对勘/并入关系均可由确定性依据解释；3 个 not_comparable 单元无对勘关系
test_tamper_comparable_unit_without_any_relation: AssertionError: True is not false : collation_comparable_only 未转红: 对勘/并入关系均可由确定性依据解释；3 个 not_comparable 单元无对勘关系
test_tamper_relation_on_unit_undeclared_by_base:  AssertionError: True is not false : collation_comparable_only 未转红: 对勘/并入关系均可由确定性依据解释；3 个 not_comparable 单元无对勘关系
```

`pipeline/assembly/tests/test_acceptance_collation.py`（8 个用例；ACT 30 列的 4 个具名用例 + 不可比单元上有关系、
自环对齐、not_comparable 清单/计数错、清单推导对照 §29 Q11）。用临时目录里的假夹具（manifest + 两份视图 + r2 金标）
加假 release 驱动真的 `check_edition_collation`。

**顺序说明（如实）**：acceptance 这一半我是先写了实现、后写测试。为了仍然拿到真 Red，
把新 `acceptance.py` 存到仓库外，从 git 取回改动前的版本跑新测试，再放回新版本（`cmp` 核对一致）。改动前的判据下：

```
Ran 8 tests in 0.321s
FAILED (failures=13, errors=1)
- test_not_comparable_expected_matches_charter_fixture | AttributeError: module 'pipeline.assembly.acceptance' has no attribute '_collation_expected'
- test_edition_collation_fail_when_a_kind_missing | AssertionError: '四类对勘关系须各至少一条' not found in "对勘关系 addition:sanche-0005 落在不是「两侧都声明 present」的单元上 …; 不可比单元必须如实入册（夹具恰有 1 个无 collation_key 的单元），实际 report=3"
- test_edition_collation_pass_when_four_kinds_match_gold | FAIL（旧判据把正确的 §25 形状判成 FAIL：addition/omission 落在「非两侧 present」单元、计数写死 1）
```

## 4. Green

```
$ .venv/bin/python -m unittest pipeline.assembly.tests.test_gate_collation pipeline.assembly.tests.test_acceptance_collation -v 2>&1 | tail -5
----------------------------------------------------------------------
Ran 39 tests in 0.288s

OK
```

Gate 实现要点（`gate.py`，全部在 `collation_comparable_only` 内部，13 项名字与顺序未动）：
1. 任一 `editions` 条目（基底或新 knowledge）缺 `collation_units` → FAIL
2. 新 knowledge 的视图版次 `collation_units` == 视图声明；其他版次条目与基底逐字节相同
3. `_asm_collation_plan` 按「视图 × 每个异 source 同 work_key 的基底版次」逐对重算单元，推出 not_comparable 清单并与 `edition_collation_set.not_comparable` 逐项比对
4. 所有对勘关系先过形状（null 端点只在 addition/omission、无自环、端点是断言、两端不同版次、absent_source_id 是另一版次）；不涉及视图的关系集合与基底逐字节相同
5. 涉及视图的关系逐条核：方向（§25.6）、detail.collation_key、absent_source_id、落在可比单元、类型与端点对上推出的断言；auto 的 alignment/variant_reading 两端 subject 非空且相等；alignment 同 text_sha256、variant_reading 异；对勘 distinct_from 必须 human
6. 完整性：每个可比单元恰一条关系
7. 并入类（alias_of / merged_into）的配对依据检查原样保留
8. `_asm_closure`：对勘单元触点改为 §28 Q6 的 (a)(b)(c)；`_asm_declared_presence` 只读 `collation_units`

gate.py 仍只导入 `canonical`、`model`、`pipeline.ledger.ids` 与标准库；实现只凭 §25/§28/§29 与 README §6，未读引擎对勘实现。

acceptance.py：`check_edition_collation` 改为调用纯函数 `_judge_edition_collation`（新增私有辅助 `_collation_signature`、
`_collation_expected`），不再有 BLOCKED 分支；`EDITION_COLLATION_GAP` 因此成了孤儿，已删（全仓只有这一处引用）。
not_comparable 清单取纯函数层 `result["collation"]`（即 `edition_collation_set`，Ledger 的 assembly 包里不存这份清单），
计数取 Ledger 里 r2 的 `assembly_report.not_comparable_count`。

## 5. verify 段输出

```
$ .venv/bin/python -m unittest pipeline.assembly.tests.test_gate_collation pipeline.assembly.tests.test_acceptance_collation -v 2>&1 | tail -5
Ran 39 tests in 0.288s
OK

$ .venv/bin/python -m unittest discover -s pipeline/assembly/tests -t . 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^OK|^FAILED"
FAIL: test_blocked_lines_exact_text (pipeline.assembly.tests.test_acceptance.TestAcceptance.test_blocked_lines_exact_text)
FAIL: test_genesis_acceptance_summary_and_exit_2 (pipeline.assembly.tests.test_acceptance.TestAcceptance.test_genesis_acceptance_summary_and_exit_2)
FAIL: test_shell_never_trusts_copy_verify (pipeline.assembly.tests.test_acceptance.TestAcceptance.test_shell_never_trusts_copy_verify)
FAIL: test_shell_returns_2 (pipeline.assembly.tests.test_acceptance.TestAcceptance.test_shell_returns_2)
FAIL: test_shell_summary_pass_16_fail_0_blocked_1 (pipeline.assembly.tests.test_acceptance.TestAcceptance.test_shell_summary_pass_16_fail_0_blocked_1)
FAIL: test_edition_collation_judged_from_real_run (pipeline.assembly.tests.test_acceptance.TestAcceptanceIncremental.test_edition_collation_judged_from_real_run)
FAIL: test_identity_delta_judged_from_real_run (pipeline.assembly.tests.test_acceptance.TestAcceptanceIncremental.test_identity_delta_judged_from_real_run)
FAIL: test_incremental_multi_edition_judged_from_real_run (pipeline.assembly.tests.test_acceptance.TestAcceptanceIncremental.test_incremental_multi_edition_judged_from_real_run)
FAIL: test_rework_replacement_judged_from_real_run (pipeline.assembly.tests.test_acceptance.TestAcceptanceIncremental.test_rework_replacement_judged_from_real_run)
FAIL: test_r2_incremental_all_checks_pass (pipeline.assembly.tests.test_gate_incremental.IncrementalGateCase.test_r2_incremental_all_checks_pass)
FAIL: test_incremental_round_report_carries_gate_result (pipeline.assembly.tests.test_gate_incremental.IncrementalGateWiringTest.test_incremental_round_report_carries_gate_result)
FAIL: test_rework_round_all_checks_pass (pipeline.assembly.tests.test_gate_incremental.ReworkGateCase.test_rework_round_all_checks_pass)
FAIL: test_release_run_scope_key_allows_two_independent_runs (pipeline.assembly.tests.test_incremental_inputs.IncrementalInputsCase.test_release_run_scope_key_allows_two_independent_runs)
FAIL: test_run_m7_accepts_sealed_base_snapshot (pipeline.assembly.tests.test_incremental_inputs.IncrementalInputsCase.test_run_m7_accepts_sealed_base_snapshot)
FAIL: test_prev_revision_and_meta_base_agree_still_holds (pipeline.assembly.tests.test_incremental_orchestration.LedgerAgreementTest.test_prev_revision_and_meta_base_agree_still_holds)
FAIL: test_prev_revision_and_meta_base_agree (pipeline.assembly.tests.test_incremental_proposals.PrevMetaAgreementTest.test_prev_revision_and_meta_base_agree)
FAIL: test_rework_ed01r2_end_to_end_through_run_m7 (pipeline.assembly.tests.test_release_fixture.TestReleaseFixture.test_rework_ed01r2_end_to_end_through_run_m7)
Ran 268 tests in 137.135s
FAILED (failures=17, skipped=2)

$ git diff --stat 53a9107 -- pipeline/assembly/model.py … pipeline/corpus/_fixture/ openspec/acceptance/
（无输出）

$ .venv/bin/python -c "import ast; …gate.py 导入检查…"
[]
```

268 = 基线 229 + 新增 39。17 条红全部属于下面第 7 节的 B 组；2 条 skip 见 A 组。

## 6. 三条篡改探针（在仓库外的 `pipeline/` 副本上各改一处；改前三份副本均 `OK`）

| 探针 | 改动 | 目标用例 | 结果 |
|---|---|---|---|
| P1 | 删掉 `_asm_collation_shape` 里的自环判断 | `test_tamper_self_loop` | **转红**：`'自环' not found in 'alignment alignment:sanche-0001 两端同属一个版次 src_sanche_ed99（同一版次不跟自己比，§25.3）'` |
| P2 | 完整性判断 `if got != 1:` 改成 `if False:` | `test_tamper_comparable_unit_without_any_relation` | **转红**（4 个子用例全红）：`True is not false : collation_comparable_only 未转红: 对勘关系按 §25/§28/§29 独立重算全部吻合：4 个可比单元各恰一条关系…` |
| P3 | 基底声明改回从断言推（F3 口径：该版次有断言的键 = present，其余一律当 present:false；去掉 base_undeclared 分支） | `test_tamper_relation_on_unit_undeclared_by_base` | **转红**：`'不可比' not found in "edition_collation_set.not_comparable 与 Gate 独立推出的清单不一致…"` |

如实说明：
- P1：自环必然两端同版次，去掉自环判断后篡改**仍会被**「同一版次」那道拦下；用例转红是因为它要求失败理由实指「自环」。自环判断是带专属理由的第一道，不是唯一一道。
- P3：转红时先暴露的是 not_comparable 清单不一致。另做了加强版：P3 副本里让上报清单也按同一错误口径算，篡改世界（0004 上的增文）被**整体放行**
  （`collation_comparable_only passed = True`）。「基底声明只从 editions[].collation_units 读」是这条的唯一防线。
- P2 是纯粹的唯一防线：去掉后「可比单元漏关系」完全放行。

## 7. 预期中的红（逐条）

### A 组：环境（Windows / 无真书账本）

- 基线的 5 条环境红已被 c40f864 修掉：在并入 i-base 之后、本分支改动之前的代码上单独跑这 5 条 + `test_upstream_m6_real_blocked_until_impl06_accepted` → `Ran 6 tests … OK`。
- 本机现在 **0 条**环境红；只有 2 条 skip，都因无真书账本：
  `test_acceptance.…test_upstream_m6_real_book_passes_on_this_host`、`test_gate_incremental.…test_real_book_second_round_all_checks_pass`。
- 未发现路径分隔符或换行导致的红。

### B 组：旧 fixture / 旧引擎产出在新 Gate 下的红（17 条）

归因是机械核对，不是推测：
1. 包一层 `gate._run_check`，记录每条红用例里哪项 Gate 检查失败、理由前 200 字；
2. 把 53a9107 版的对勘检查、`_asm_closure`、`_asm_declared_presence` 与旧 `check_edition_collation` 换回去重跑 → 进程内的 14 条**全部转绿**；
3. 3 条 shell 用例走子进程（`m7-assembler.sh`），打不了补丁，直接跑脚本看判定行。

共同根因：旧引擎写出的 Snapshot `editions[]` 没有 `collation_units`（§25.5 新增的必填字段，轨道 1 在补），
新 Gate 按合同一·1 / §29 Q9 判 FAIL、不许静默当空 → 增量轮 `failed` → 没有 r2 Snapshot → r3 被当作重复创世拒收。

| 用例 | 失败的 Gate 检查 | 失败明细（前 200 字） | 为什么是旧口径导致的 |
|---|---|---|---|
| test_gate_incremental.IncrementalGateCase.test_r2_incremental_all_checks_pass | collation_comparable_only | `基底 editions[src_sanche_ed01] 缺 collation_units 字段（不得当作空）` | fixture r1 金标（旧引擎产出）无该字段；换回旧对勘口径即绿 |
| test_gate_incremental.ReworkGateCase.test_rework_round_all_checks_pass | collation_comparable_only | 同上 | r2 金标同样无该字段；换回即绿 |
| test_gate_incremental.IncrementalGateWiringTest.test_incremental_round_report_carries_gate_result | collation_comparable_only | 同上；用例层 `'failed' != 'succeeded'` | 基底缺字段 → Gate FAIL → 该轮 failed；换回即绿 |
| test_incremental_inputs.IncrementalInputsCase.test_release_run_scope_key_allows_two_independent_runs | collation_comparable_only | 同上；`'failed' != 'succeeded'` | 同上 |
| test_incremental_inputs.IncrementalInputsCase.test_run_m7_accepts_sealed_base_snapshot | collation_comparable_only | `新 knowledge editions[src_sanche_ed01] 缺 collation_units 字段（不得当作空）`；`'failed' != 'succeeded'` | 旧引擎合并时不写该字段；换回即绿 |
| test_incremental_orchestration.LedgerAgreementTest.test_prev_revision_and_meta_base_agree_still_holds | collation_comparable_only | `基底 editions[src_sanche_ed01] 缺 collation_units 字段（不得当作空）`；`'failed' != 'succeeded'` | 同上 |
| test_incremental_proposals.PrevMetaAgreementTest.test_prev_revision_and_meta_base_agree | collation_comparable_only | 同上；`'failed' != 'succeeded'` | 同上 |
| test_release_fixture.TestReleaseFixture.test_rework_ed01r2_end_to_end_through_run_m7 | collation_comparable_only | 同上；`'failed' != 'succeeded'` | 同上 |
| test_acceptance.TestAcceptanceIncremental.test_incremental_multi_edition_judged_from_real_run | collation_comparable_only（r2 实跑） | `'FAIL' != 'PASS'`；判据行 `FAIL incremental_multi_edition RuntimeError: 夹具实跑准备失败: AssemblyRefused: technique qizheng 已汇编，创世汇编不可重复执行` | r2 被新 Gate 判 failed → 无 r2 Snapshot → r3 当创世被拒；换回即绿 |
| test_acceptance.TestAcceptanceIncremental.test_identity_delta_judged_from_real_run | 同上 | `'FAIL' != 'PASS'`（同一条「夹具实跑准备失败」） | 同上 |
| test_acceptance.TestAcceptanceIncremental.test_rework_replacement_judged_from_real_run | 同上 | `'FAIL' != 'PASS'`（同上） | 同上 |
| test_acceptance.TestAcceptanceIncremental.test_edition_collation_judged_from_real_run | 同上 + 判据本身 | `'FAIL' != 'BLOCKED'` | 用例还在断言旧口径的 BLOCKED；本 ACT 按合同二把判据改为实跑、不再 BLOCKED。旧 fixture 本身也过不了新判据（只有一条自环对齐、没有四类）。换回旧判据与旧 Gate 即绿 |
| test_acceptance.TestAcceptance.test_blocked_lines_exact_text | 同上 | `'BLOCKED edition_collation 多版次对勘（缺文/增文/异文）引擎缺口，见 CHARTER §19' not found in 'PASS genesis_snapshot…'` | `KNOWN_GAP_BLOCKED` 仍含 edition_collation（§27：集成时清空），另 4 条判据因上面的实跑失败变 FAIL；换回即绿 |
| test_acceptance.TestAcceptance.test_genesis_acceptance_summary_and_exit_2 | 同上 | `AssertionError: 1 != 2` | 4 条 FAIL → 退出码 1；换回即绿 |
| test_acceptance.TestAcceptance.test_shell_returns_2 | 同上（子进程） | `1 != 2 : stdout: PASS genesis_snapshot…`；脚本实跑 `SUMMARY pass=12 fail=4 blocked=1` | 4 条 FAIL 全是「夹具实跑准备失败: AssemblyRefused … 创世汇编不可重复执行」，同一根因 |
| test_acceptance.TestAcceptance.test_shell_summary_pass_16_fail_0_blocked_1 | 同上（子进程） | `1 != 2 : stdout: PASS genesis_snapshot…` | 同上 |
| test_acceptance.TestAcceptance.test_shell_never_trusts_copy_verify | 同上（子进程） | `AssertionError: 1 != 2` | 同上 |

没有一条红是「新 Gate 写错」导致的：进程内 14 条换回旧对勘口径全部转绿，shell 3 条的 4 条 FAIL 判据行都是同一条实跑准备失败。没有为让它们变绿放宽任何检查。

## 8. 疑问与集成提醒

1. **有真书账本的主机上，这里的 2 条 skip 会变红**：`var/ledgers/qianyuan_w8` 里旧引擎封存的 r1 缺 `collation_units`。§29 Q9 定的是引擎入口先拒收；
   若轨道 1 的入口拒收还没接上，Gate 会以「基底 editions 缺 collation_units」判 FAIL——这是预期的第二道防线，不是 Gate 错。
2. **集成时 test_acceptance.py 需要主 Agent 改**：清空 `KNOWN_GAP_BLOCKED`（§27）；`test_edition_collation_judged_from_real_run` 还在断言 BLOCKED 文案，要改成实跑判定
   （它的负向对照「从金标删掉 alignment → FAIL」在新判据下仍成立：签名与金标不一致）。
3. `report.dropped_relations` 里 `collation_recomputed` 的记录（§29 Q8）Gate 没有验——ACT 30 与 §29 都没要求 Gate 验这一项；需要的话可以补。
4. 本实现自定的一处：视图一侧的「获批断言」只数 `reviewed_edition.approved` 里 kind=assertion 的；未获批的视图断言既不参与单元判定，也不进 not_comparable 清单（含无键断言）。引擎若按候选集全体数，清单会对不上。
5. Gate 与判据的 not_comparable 推导各写一份（Gate 支持多基底版次；判据只按 fixture 的 ed01/ed99 两版次写），两份独立实现互为对照。
