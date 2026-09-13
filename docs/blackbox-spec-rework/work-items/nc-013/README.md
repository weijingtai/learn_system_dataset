# NC-013：事务事件消费、通知投递、正文拉取与补拉端点

状态：`PREPARING`（六件套与守卫就绪，待 wjt-react 四查后转 `READY`）。task_id：`NC-013`。各仓 HEAD：SERVER（functions-py master）`8d22451`、RULES（xuan-server main）`4b81d8d`、REST（repository-rest-adapter main）`cb686d0`。派发前置：NC-003、NC-009、NC-010、NC-011、NC-012a 均 `ACCEPTED`。

权威需求来源：`TASKS.md` NC-013（§214-228）；专属契约 `openspec/annotation-community/contracts/community_deliveries.md`；API 补丁 `community_api.md` §13。**执行者不做设计：集合字段、收件人矩阵、状态机转移、退避推导、参考值、测试名、文案全部来自契约。**

## Goal

functions-py 新增 `xuan/community/notification_dispatch.py` 与 `xuan/handlers/community_deliveries.py`，消费 outbox 事件（`comment.created`、`reaction.liked`产通知；`comment.edited/deleted`、`content.*`、旧广场事件幂等 no-op），以确定性 `ntf_` ID create-if-absent 创建 `community_notifications` 记录，按 SM-7 五态推进投递（赞站内零绑定 delivered；评论/回复/@ FCM 无正文唤醒，退避 1/2/4/8s 上限 5 次），提供 R9 通知正文拉取、R10 业务通知补拉（读时窗口聚合）与 W15/W16 按内容静音；ACL 扫描 E6 三例转真；REST 3.1 契约补 §13；RULES 三新集合默认拒绝用例。at-least-once语义，「原子」仅指记录终态单事务写入一次；**任何文档/注释/测试名不得声称 exactly-once**。

## Scope

- REST（act/01）：`openapi/openapi.yaml`（R9/R10/W15/W16、`NotificationBody/NotificationEntry/NotificationPage/NotificationMuteState`、错误与限流行）；`test/community_openapi_contract_test.dart`（末尾追加 4 测试；`expectedCatalog` 追加 3 行；seventeen 测试改 ≥17）；`test/fixtures/openapi/examples/`（3 示例 + manifest 3 项）。
- SERVER（act/02→03）：`xuan/config.py`（追加 3 集合键）、`xuan/community/notification_dispatch.py`（新增）、`xuan/handlers/community_deliveries.py`（新增）、`main.py`（追加注册）、`tests/conftest.py`（追加清理键）、`tests/test_community_deliveries.py`（新增 30 测试）、`tests/test_community_acl_sweep.py`（仅 E6 转真：删 3 xfail、E6 分支改调新 handler、docstring 两行）。
- RULES（act/04）：`server/functions/test/community_rules.test.ts`（追加 3 集合 × 8 用例，129 → 153）。
- 禁止：上表以外任何文件（含 `xuan/handlers/notifications.py`、`tests/test_registration.py`、`tests/test_main_exports.py`、`tests/community_helpers.py`、`xuan/community/` 既有文件、`openspec/schemas/`、NOTIFIER 仓全部）；learn_system 写入（交付报告除外）；新依赖；`skip`；新增 `xfail`（E6 三条删除除外）；永真断言；测试内计算参考值；先实现后补测试；`git push`；删除文件。

## Dependencies / Baseline

| 线 | HEAD 基线 | 既有基线 |
|---|---|---|
| REST | `cb686d0` | `dart test` +77 All tests passed!（Windows 需 `PYTHON`/`OPENAPI_VALIDATOR` 环境变量，守卫已内置） |
| SERVER | `8d22451` | pytest `5 failed, 535 passed, 6 xfailed`，FAILED 恰为 `test_config::test_集合名与_ts_逐项一致` + `test_registration` 四项（既有缺口不修，D-NC013-13） |
| RULES | `4b81d8d` | `npm test -- community_rules` `Tests: 129 passed` |

共享守卫：`bash docs/blackbox-spec-rework/reviews/nc013_guard.sh --require-impl rest|server|rules|all`（在 learn_system 根执行）。

## Stop Conditions

- 参考值（3 组 `ntf_` 字面量、共享 404 体、退避表）对不上。
- 既有测试变红（5 个既有 FAILED 之外新增任何失败）。
- 需要修改白名单外文件、或契约存在歧义。
- Emulator（192.168.0.165:8080/9099）不可达。
- 处置：在本线交付报告追加「## 待裁决」小节说明原始输出，并单独输出一行 `NC-013-<A|B|C|D> 停手待裁决`；不改契约与既有测试，等主 Agent 裁定（裁定以 `D-NC013-<编号>` 登记于契约 §15 并同步六件套与守卫）。

## 执行顺序

REST（act/01）∥ SERVER（act/02 → act/03，同仓严格串行）∥ RULES（act/04）；跨线无先后。每 act 一个独立提交；完成一个 act 即写本线 `DELIVERY_REPORT_<线>.md`（不入库）。

## 阅读顺序

1 本 README → 2 契约 `community_deliveries.md` 全文 → 3 `community_api.md` §2、§3、§4、§5、§6、§13 → 4 BDD/TDD → 5 ACT.yaml 与所属 act/*.yaml → 6 ACCEPTANCE.md → 7 PROMPT.md。
