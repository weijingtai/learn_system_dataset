# NC-001 开工包审查 R2（wjt-react 四查）与返工落实

日期：2026-09-10。审查对象：提交 `aadd1fc`（R1 返工落实后的 `work-items/nc-001/`）。审查人：独立只读 Agent（Opus，未参与编写）；返工裁定与落实：主 Agent（C/S 会话）。守卫：`bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh`，取代 `nc001_r1_guard.sh`（后者的 K02/K03 只对 `aadd1fc` 成立，R2 守卫已把这两项改为核对该提交的内容，永久为真）。

## 0. 审查结论

| 四查 | 结论 | 要点 |
|---|---|---|
| 忠实性 | PASS | 每个 STEP 可追溯；SIGNATURE 与契约 §6/§7 一致；ACCEPTANCE/TASKS 的改动全部对应 R1 替换 1～3、14～16；契约 §7 的 23 行可由契约独立复算 |
| 覆盖性 | FAIL | BDD B01～B17 全覆盖且有反例，但契约 §2～§3 的类型/枚举/固定值规则（head、dirty_entries、write_policy、kind、choice、openapi_validator 五值、emulator 常驻字段、account_deletion 固定值、顶层固定值、仓库集合）零负例 |
| 可执行性 | FAIL | 路径、类型来源、命令空跑、依赖白名单、模糊词均 PASS；ESTIMATE 55 分钟与工作量不相称；契约两处双解 |
| 独立性 | PASS | DEPENDS_ON 与串行明确；与 G3 线产出文件零重叠；共享守卫存在耦合（见返工 6） |

判定：**REWORK**，6 条返工项。

## 1. 返工项与裁定

| # | 返工项（审查者原文摘要） | 主 Agent 裁定与落实 |
|---|---|---|
| 1 | §4 状态闸门与 §3「未验证态验证字段必须全为 null」在 integrated 下先后关系有两种解释，执行者会按 Stop Condition 停工 | 裁定：闸门只作用于 §4 增量表；§3 半填检查两档都保留、不受抑制。契约 §4 补裁定句与示例；BDD 新增 B18；TDD 新增 `test_integrated_half_filled_unverified` |
| 2 | `test_missing_required_keys` 的「必填键」集合无定义，16 与 140 差一个数量级，缩水也能全绿 | TDD §3.1 逐字写出 103 条路径 + 2 个定位键用例；测试文件须含模块顶层字面量 `REQUIRED_KEY_PATHS`；守卫 K07 数 103 条，K08 核对 103 个字面量逐一出现在测试文件 |
| 3 | §2～§3 十组规则零负例，错误实现可全绿 | 新增 9 个方法：`test_root_not_object`、`test_top_level_values`、`test_client_and_identity_values`、`test_openapi_validator_rules`、`test_repositories_rules`、`test_emulator_constants`、`test_notification_presentation_rules`、`test_account_deletion_constants`、`test_local_test_fixture_suffix`；既有方法补 subTest（ports kind/重复、tests.reason、half-filled 多对象、fake PASSED count=0 等）。方法 21 → 31；BDD 新增 B19～B22 |
| 4 | JSON 根不是 object 时输出未定义 | 裁定：退出 1，stdout 恰为一行 `root`。契约 §2 表与 §6 写明；同时写明数组元素不是 object / 缺定位键只报数组路径 |
| 5 | ESTIMATE 55 分钟与工作量不相称 | 拆为四步：act/01（40，CLI+§2+§6+夹具）、act/02（50，§3 前六对象）、act/03（55，repositories/ports/integration+必填键全表）、act/04（55，§4/§5/§7）。每个 ACT 增 `WORKLOAD` 行写明判据条数与方法数 |
| 6 | 共享守卫在并行工作树下非封闭，且未记录开工基线退出码 | README 记录 `aadd1fc` 时四条基线均为 0；四个 ACT 的 ON_FAIL 增加「先 `git diff --stat`，失败源在两文件之外判外部失败，只记录不返工不停工」；PROMPT 同步 |

非阻断建议 1～3 一并采纳：B19 补 devices/account_pairs/test_runs 可观察行为；`test_local_test_fixture_suffix` 锁住 local 的 TEST_FIXTURE 后缀；PROMPT 明示允许新建 `openspec/annotation-community/tools/` 目录。建议 4（K05 WARN）无需处理。

## 2. 本次改动文件

- `work-items/nc-001/VALIDATION_CONTRACT.md`：状态行、§2（根）、§4 闸门、§6 两条
- `work-items/nc-001/BDD.md`：B18～B22
- `work-items/nc-001/TDD.md`：整文件重写（四步、31 方法、103 必填键、共享守卫规则、R2 守卫）
- `work-items/nc-001/ACT.yaml`、`act/01.yaml`～`act/04.yaml`：整文件重写（原 act/02 内容并入 act/04）
- `work-items/nc-001/README.md`、`PROMPT.md`、`ACCEPTANCE.md`：四步、31 方法、R2 守卫、外部失败规则
- `reviews/nc001_r2_guard.sh`：新增；`reviews/NC-001-REVIEW-R2.md`：本文

## 3. 完成标准

```bash
bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh
git diff --check
```

均为 0（K08 允许 SKIP）。随后由另一位未参与编写的审查者做第二轮 wjt-react 四查；READY 后主 Agent 在 SUBAGENT_TODO 登记并派发 PROMPT.md。两轮不收敛则停止并上报用户。

## 4. 第二轮审查（R3，2026-09-10）与落实

审查人：另一独立只读 Agent（Opus）。结论：上一轮 6 项中 5 项 CLOSED、第 6 项部分 CLOSED；新报 3 条阻断、5 条建议。判定 REWORK。主 Agent 落实如下（提交见 git log）：

| # | R3 返工项 | 落实 |
|---|---|---|
| 1 | `test_inputs_unchanged` 括注「integrated 此时退出 2」在步骤 4 失效，与「不改前步期望」冲突 | TDD §3.4 改为只断言哈希与目录列表，不断言退出码与 stdout；守卫 K10 拒绝「后者此时退出 2」残留 |
| 2 | 契约 §4 六条取值规则零负例 | 新增 `test_integrated_value_rules`（9 个 subTest，含两个容器类型负例）；`test_integrated_fixture_pass` 的完整夹具取值逐字写死；BDD B23；方法 31 → 32；守卫 K07/K08 同步 |
| 3 | 外部失败豁免未覆盖 `nc001_r2_guard.sh` 的 K01 | 四个 ACT、README、PROMPT、TDD 七处逐字追加「K01 同样按外部失败处理；K02～K10 仍按本任务失败停工」；新增守卫 K11 核对七处一致 |

建议 1～5 全部采纳：契约 §3 写明 status 枚举约束；`openapi_validator.evidence` 在 local 下不检查；`test_test_runs_set_rules` 补 command/count 负例；`test_integrated_fixture_evidence_removed` 的 11 条期望路径逐条写出；ACCEPTANCE 复述外部失败规则。

第三轮审查若仍不 READY，按 wjt-react 规则停止并上报用户。

## 5. 第三轮审查（R4，2026-09-10）：READY

审查人：第三位独立只读 Agent（Opus）。R3 三项阻断全部 CLOSED，五条建议全部落实；`git diff 7ba3f35 3e5d1d8` 逐 hunk 无新矛盾（含「恰为一行」在完整夹具上的可判定性、§7 的 23 行独立复算吻合）；四查全 PASS；守卫 0、`--require-impl` 仅 K08 未实现（预期）、`git diff --check` 0、模糊词零命中。两条非阻断建议（ACCEPTANCE 的 B01～B22 → B23；七处豁免句 K02～K10 → K02～K11）已由主 Agent 落实。

**决定记录：转译审查 R4：READY，4 个 ACT 可开工。** 主 Agent 在 SUBAGENT_TODO 登记 NC-001-01 为 READY 并派发 `work-items/nc-001/PROMPT.md`。
