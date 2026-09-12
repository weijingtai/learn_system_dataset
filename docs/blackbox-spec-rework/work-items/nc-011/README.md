# NC-011：两级评论、排序分页、修改历史与收回并发

状态：`DISPATCHED`（2026-09-12：agy 四查 R1 返工 4 项、R2 READY，见 `reviews/NC-011-REVIEW-R1.md`；tmux 会话 nc011s = REST+SERVER、nc011c = CLIENT 并行）。派发前置：NC-003、NC-009、NC-010 均 `ACCEPTED`（已满足）。task_id：`NC-011`。权威需求来源：TASKS NC-011 与 NC-009「R2-05 提交顺序」原文；PRD §5.1、§6.3、§6.4；DESIGN §4.3、§4.4、§6、§7.1、§7.3；契约 `contracts/community_discussion.md`（本任务专属）与 `community_api.md` §11。

## Goal

在三个仓库交付评论能力：REST 契约补齐楼内分页、回复预览与计数、评论创建冲突组件；服务端实现 W7～W9 与 R2（事务写 comment/revision/thread 计数/outbox/账本，墓碑、编辑留痕、403/404 边界、稳定游标与 ETag），并以受控屏障证明 R2-05 两种提交顺序、回调重跑与三方竞争；客户端接入命令队列（RW-5 三项断言与离线重启）、讨论区控制器与面板、七状态、评论计数端口。执行者不做设计：集合字段、判定顺序、参考值、文案、测试名全部来自契约。

## Scope

- REST：`openapi/openapi.yaml`、`test/community_openapi_contract_test.dart`（只追加）、`test/fixtures/openapi/examples/` 三个新文件与 `manifest.json`（只追加）。
- SERVER：契约 §2.1 表内文件；RULES 仓只改 `server/functions/test/community_rules.test.ts` 的集合数组。
- CLIENT：契约 §2.2 表内文件。
- 禁止：写入 learn_system（交付报告除外）；表外任何文件；新依赖；`skip`/`xfail`；永真断言；测试内计算参考值；先实现后补测试；`git push`；删除文件。

## Dependencies / Baseline（2026-09-12 Haiku 实测）

| 线 | HEAD | 基线 |
|---|---|---|
| REST | `5730ed9` | `dart test` `+69` |
| SERVER | `df5c3da` | `5 failed, 459 passed, 9 xfailed`（五个既有失败逐名见契约 §1） |
| RULES | `ea8c9b8` | `Tests: 65 passed` |
| CLIENT | `4588f78` | `flutter test` `+214`；`flutter analyze` 0 |

共享守卫：`bash docs/blackbox-spec-rework/reviews/nc011_guard.sh [--require-impl rest|server|client|all]`（learn_system 内运行，只读）。

## Stop Conditions

契约有两种以上解释；需要改白名单外文件或既有测试期望；参考值按契约实现后仍对不上；并发屏障 `wait(10)` 超时或提交顺序与契约不符（契约 §8）；全量 pytest 的失败集合不再恰为五个既有 ID；`flutter pub get` 改动锁文件。遇到即停：在本线交付报告追加「## 待裁决」（现象、命令、原文、你看到的选项），对话最后单独输出一行 `NC-011-<字母> 停手待裁决`。

## 执行顺序（三线并行，同仓库串行）

- REST：`act/01`（NC-011-A，dart test 69 → 73）。
- SERVER：`act/02`（NC-011-B，W7，pytest 459 → 479 passed）→ `act/03`（NC-011-C，W8/W9/R2，→ 491）→ `act/04`（NC-011-D，并发屏障、日志、规则，→ 496；rules 65 → 89）。T14 参数化 3 例，35 个测试名共 37 例。
- CLIENT：`act/05`（NC-011-E，模型/API/队列/计数端口，flutter test 214 → 224）→ `act/06`（NC-011-F，控制器/面板/七状态，→ 239）。

每步一个提交（act/04 在 SERVER 与 RULES 各一个）。交付报告分三份，写入本目录且不入库：`DELIVERY_REPORT_REST.md`、`DELIVERY_REPORT_SERVER.md`、`DELIVERY_REPORT_CLIENT.md`。

## 一次性交付与阅读顺序

1. 本 README；2. `openspec/annotation-community/contracts/community_discussion.md`；3. `community_api.md` §4.1、§7、§10、§11；4. [BDD](BDD.md)、[TDD](TDD.md)；5. [ACT](ACT.yaml) 与本线 act/*.yaml；6. [ACCEPTANCE](ACCEPTANCE.md)；7. [PROMPT](PROMPT.md) 中本线一节。
