# NC-009：公共发布事务、权限扫描与命令账本服务（服务端）

状态：`DRAFT`（2026-09-11，待 wjt-react 四查）。派发前置：**NC-003 ACCEPTED（含 act/06，已合入契约 §9 P1/P2）**；环境阻塞已于 2026-09-11 解除（见 Baseline）。执行由用户交外部 Agent，PROMPT.md 原样发送。task_id：`NC-009`。权威需求来源：TASKS NC-009；DESIGN §4、§7.3、§7.4、§11.4～11.5；PRD R-05/R-20、§6.2；契约 `contracts/community_server.md`（本任务专属，主 Agent 编写）与 `community_api.md`（NC-003）。

## Goal

在 canonical SERVER（`xuan-server/functions-py`）实现：事务级命令账本服务（同键重放/异载荷 409/拒绝终态/14 天精简/410）、内容命令 W1～W6 与读端点 R1/R5/R6、ACL 扫描矩阵 18 条（本任务实现 9 条，其余 `xfail(strict)` 标注所有者）、Firestore 规则单测、可观测性断言。执行者不做设计：集合、字段、判定顺序、错误码全部来自契约。

## Scope

- 允许写（SERVER）：`xuan/community/{__init__,errors,ids,command_service,content_service,access}.py`、`xuan/handlers/{community_contents,community_commands}.py`、`tests/{community_helpers,test_community_commands,test_community_publications,test_community_acl_sweep}.py`；`xuan/config.py`（只追加 `COLLECTIONS` 键）、`main.py`（只追加导出）、`tests/conftest.py`（只向 `clean_collections` 的 `names` 追加社区集合）。
- 允许写（RULES 仓 `xuan-migration/xuan-server/server`）：仅 `functions/test/community_rules.test.ts`。
- 只读：其余 SERVER 文件（含 `idempotency.py`、`playground_rest.py`、`notifications.py`）、`firestore.rules`、learn_system。
- 禁止：改 `firestore.rules`；用 `with_idempotency` 包装社区命令；在事务回调内上传/推送/sleep；`skip`；`assert status in (...)` 二选一；用内存 fake 代替 Emulator；新增 Python 依赖；把 `xuan-migration/xuan-server/server/functions-py` 当写入目标。

## Inputs

契约 `community_server.md` §1（仓库与环境）、§2（文件与集合）、§3（账本事务流程）、§4（六个命令的前置顺序与写集）、§5（读路径与 ACL 矩阵）、§6（规则测试）、§7（测试名）、§8（决定）；`community_api.md` §2～§7（端点、头、错误、Schema）。

## Dependencies / Baseline

- SERVER HEAD `30a868c`；Emulator `192.168.0.165:8080/9099` 2026-09-11 可达；RULES 仓 `functions/node_modules` 已装（jest + `@firebase/rules-unit-testing`）。
- **环境基线（2026-09-11 磁盘清理后主 Agent 重建 `functions-py/.venv`，Python 3.14.6、pytest 9.1.1）**：`pytest tests -q` → `411 passed, 5 failed, 58 subtests passed`。5 个既有失败与本任务无关，原样保留、不得修改：`tests/test_config.py::test_集合名与_ts_逐项一致`（读取已不存在的 `xuan-server/functions/src/index.ts`）；`tests/test_registration.py` 的 `test_全部_callable_已在入口注册`、`test_三个_trigger_已注册`、`test_与_入口总数对齐`、`test_没有多余的未声明导出`（清单停留在 37 个入口，未含 fcm/follow/search 等后续导出）。本任务新增导出不改变失败集合；验收比较**失败用例名称集合**与本清单相同。
- 共享守卫：`bash docs/blackbox-spec-rework/reviews/nc009_guard.sh --require-impl`（只读）。

## Stop Conditions

契约有两种以上解释；Emulator 不可达；`.venv` 缺失或 `firebase_admin` 不可导入；`firestore.rules` 需要改动才能通过规则测试；需要改 `idempotency.py`/`playground_rest.py`；需要新依赖；NC-003 未 ACCEPTED。遇到即停，原样报告。

## 执行顺序

`act/01`（账本服务 + 注册 + 12 测试）→ `act/02`（publish/update/withdraw + access + R1 + 9 测试）→ `act/03`（trash/restore/purge + R5/R6 + 精简 + 7 测试）→ `act/04`（ACL 18 条 + 规则 jest + 可观测性）。每步一个提交在 SERVER 仓；act/04 另在 RULES 仓一个提交。

## 一次性交付与阅读顺序

1. 本 README；2. `contracts/community_server.md`；3. `contracts/community_api.md`；4. [BDD](BDD.md)、[TDD](TDD.md)；5. [ACT](ACT.yaml) 与 act/01～04；6. [ACCEPTANCE](ACCEPTANCE.md)；7. [PROMPT](PROMPT.md)。
