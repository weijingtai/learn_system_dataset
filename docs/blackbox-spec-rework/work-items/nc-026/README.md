# NC-026：行为事件数据源、假名化与私人笔记元数据上报

状态：`PREPARING`（六件套与守卫就绪，待 wjt-react 四查后转 `READY`）。task_id：`NC-026`。各仓 HEAD：SERVER（functions-py master）`992088e`、CLIENT（reading-notes main）`19afe37`（NC-014 落地后基线，D-NC026-26）、REST（repository-rest-adapter main）`b60bfbd`、RULES（xuan-server main）`a354463`。派发前置：NC-002、NC-003、NC-005、NC-009 均 `ACCEPTED`。

权威需求来源：`TASKS.md` NC-026（§201-208）；专属契约 `openspec/annotation-community/contracts/community_behavior.md`（§1～§15）；API 补丁 `community_api.md` §14。**执行者不做设计：字段全集、事件目录、假名规则、上报端点、错误码、参考值、测试名、文案全部来自契约。**

## Goal

冻结并交付**只追加**的行为事件数据源：`BehaviorEvent.attributes` 由开放式 `type: object` 收紧为按 `event_type` 的封闭允许集、`event_type`/`platform` 闭集、服务端事件补齐 DESIGN §11.2 的六个缺失外层字段；新增 `POST /v1/analytics/events`（客户端私人笔记元数据上报，服务端按 `event_id` create-if-absent 去重、补齐 `received_at` 与 `actor_pseudonym`）与 `GET /v1/analytics/pseudonym`（假名交付，供客户端计算 `note_ref`）；客户端 `PrivateNoteMetrics` 提供默认开启的本地队列（上限 10000、超限丢最旧、下一条带 `dropped_before`）与不含任何内容的字段白名单；BehaviorEvent 禁 update/delete 由 RULES 显式用例与静态扫描双向固化。上报语义 at-least-once；**任何文档/注释/测试名不得声称 exactly-once**。

## Scope

- REST（act/01）：`openapi/openapi.yaml`（W17/R11、4 Schema、错误与限流行）；`test/community_openapi_contract_test.dart`（末尾追加 4 测试、`expectedCatalog` 追加 2 行、twenty 断言改 `greaterThanOrEqualTo(20)`）；`test/fixtures/openapi/examples/`（2 示例 + manifest 2 项）。
- SERVER act/02（Schema 与信封）：`xuan/community/schemas/community_behavior_event.schema.json`（逐字节复制契约 §9.1 的规格侧文件）、`tests/test_community_validation.py`（仅改该文件的一项 SHA 字面量）、`xuan/community/command_service.py`（仅 §3.1 一处补六个外层字段）、`tests/test_behavior_events.py`（前 10 测试）。
- SERVER act/03（端点与假名）：`xuan/community/pseudonyms.py`、`xuan/community/behavior_events.py`、`xuan/handlers/analytics_events.py`、`xuan/config.py`（+1 集合键）、`main.py`（+1 导出）、`tests/conftest.py`（+1 清理键）、`tests/test_behavior_events.py`（后 16 测试）。
- CLIENT（act/04）：`lib/src/analytics/private_note_metrics.dart`（新增）、`test/analytics/private_note_metrics_test.dart`（新增 18 测试）。
- RULES（act/05）：`server/functions/test/community_rules.test.ts`（仅追加 `describe`，4 用例，153 → 157）。
- 禁止：上表以外任何文件。特别地 `xuan/community/content_service.py`、`discussion_service.py`、`interaction_service.py`、`access.py`、`errors.py`、`ids.py`、`community_hash.py`、`push.py`、`identity.py`、`xuan/handlers/community_*.py`（`analytics_events.py` 除外）与 `tests/test_community_interactions.py`、`tests/test_community_comments.py`、`tests/test_registration.py`、`tests/test_main_exports.py`、`tests/community_helpers.py`、`server/firestore.rules`、`lib/src/persistence/note_database.dart`、`lib/src/persistence/note_repository.dart`、`lib/src/editor/*` 一律零改动；learn_system 写入（交付报告除外）；新依赖；`skip`；新增 `xfail`；永真断言；测试内计算参考值；先实现后补测试；`git push`；删除文件。

## Dependencies / Baseline

| 线 | HEAD 基线 | 既有基线 |
|---|---|---|
| REST | `b60bfbd` | `dart test` `+81: All tests passed!`（Windows 需 `PYTHON`/`OPENAPI_VALIDATOR`，守卫已内置） |
| SERVER | `992088e` | pytest `5 failed, 568 passed, 3 xfailed`，FAILED 恰为五个既有 ID（既有缺口不修，D-NC013-13 口径） |
| CLIENT | `19afe37` | `flutter analyze` No issues found!；`flutter test` `+314` |
| RULES | `a354463` | `npm test -- community_rules` `Tests: 153 passed, 153 total` |

共享守卫：`bash docs/blackbox-spec-rework/reviews/nc026_guard.sh --require-impl rest|server|client|rules|all`（在 learn_system 根执行）。

## 注销子项（DEFERRED，不派发）

TASKS NC-026 的「**注销**」条（删 PseudonymMapping、业务数据去标识化、事件保留）**不进入本次派发**：其事件来源取自 NC-001 登记的第⑩项（宿主账号注销与本人彻底删除账号事件的来源、送达语义、测试方式），该证据至今缺失（`SUBAGENT_TODO.md` NC-001 总项仍 `PREPARING`）。登记为 D-NC026-13；解锁条件 = NC-001 第⑩项登记完成。其余子项不受影响。

## Stop Conditions

- 参考值（3 组 `bev_` 字面量、`note_ref` 字面量、Schema SHA）对不上。
- 既有测试变红（SERVER 五个既有 FAILED 之外新增任何失败；CLIENT 296 之外新增失败；REST 81、RULES 153 之外新增失败）。
- 需要修改白名单外文件、或契约存在歧义。
- Emulator（192.168.0.165:8080/9099）不可达。
- 处置：在本线交付报告追加「## 待裁决」小节并附原始输出，同时单独输出一行 `NC-026-<A|B|C|D|E> 停手待裁决`；不改契约与既有测试，等主 Agent 裁定（裁定以 `D-NC026-<编号>` 登记于契约 §15 并同步六件套与守卫）。

## 执行顺序

REST（act/01）∥ SERVER（act/02 → act/03，同仓严格串行）∥ CLIENT（act/04）∥ RULES（act/05）；跨线无先后。每 act 一个独立提交；完成一个 act 即写本线 `DELIVERY_REPORT_<线>.md`（不入库）。

## 阅读顺序

1 本 README → 2 契约 `community_behavior.md` 全文 → 3 `community_api.md` §2、§3.1、§4.1、§5.3、§6、§14 → 4 BDD/TDD → 5 ACT.yaml 与所属 act/*.yaml → 6 ACCEPTANCE.md → 7 PROMPT.md。
