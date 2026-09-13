# NC-012a：赞踩、收藏、分享、举报与 mention 文本校验

状态：`ACCEPTED`（2026-09-12 R1，见 [ACCEPTANCE](ACCEPTANCE.md) 验收记录；REST `cb686d0`、SERVER `db52847`→`8d22451`、RULES `4b81d8d`、CLIENT `e1655a4`→`107ec90`。此前 `READY`（2026-09-12：agy 四查 R1 READY、返工 0 项，见 `reviews/NC-012a-REVIEW-R1.md`；主 Agent 采纳建议 1～3 写死三处实现细节）。派发前置：NC-003、NC-009、NC-010、NC-011、NC-016a 均 `ACCEPTED`（已满足）。task_id：`NC-012a`。NC-012b（宿主社交注入、mention 候选与编辑器接线、三类依赖关系数据的无效 mention）`BLOCKED`，等 NC-001-02（D-NC012-01）。权威需求来源：TASKS NC-012；契约 `contracts/community_interactions.md`（本任务专属）与 `community_api.md` §12。

## Goal

在三个仓库交付互动能力：REST 契约补齐 W10/W11 响应包装、R7 我的分享链接、R8 收藏读取与错误目录增补；服务端实现 W10～W14 与 R3、R4、R7、R8（确定性文档 ID、计数投影、If-Match、同值不写、分享仅作者、R4 统一 404、举报以 command_id 为键），规则测试纳入五个新集合，ACL 扫描 E4 转为真实断言；客户端统一 `MentionRef`、实现 mention 文本校验纯函数、九个 API 方法与五个队列操作、互动控制器（合并快速切换、迟到防回滚、412 不自动重发、举报本地折叠）、分享链接管理与落地页、互动条与举报面板。执行者不做设计：集合字段、判定顺序、参考值、文案、测试名全部来自契约。

## Scope

- REST：`openapi/openapi.yaml`、`test/community_openapi_contract_test.dart`（只追加）、`test/fixtures/openapi/examples/` 四个新文件与 `manifest.json`（只追加）。
- SERVER：契约 §2.1 表内文件；RULES 仓只改 `server/functions/test/community_rules.test.ts` 的集合数组。
- CLIENT：契约 §2.2 表内文件。
- 禁止：写入 learn_system（交付报告除外）；表外任何文件；新依赖；`skip`；新增 `xfail`；永真断言；测试内计算参考值；先实现后补测试；`git push`；删除文件。

## Dependencies / Baseline（2026-09-12，派发前执行器复测）

| 线 | HEAD | 基线 |
|---|---|---|
| REST | `4671c92` | `dart test` `+73` |
| SERVER | `0fad16e` | `5 failed, 496 passed, 9 xfailed`（五个既有失败逐名同 NC-011） |
| RULES | `dd3445f` | `Tests: 89 passed` |
| CLIENT | `d80703b` | `flutter test` `+270`；`flutter analyze` 0 |

共享守卫：`bash docs/blackbox-spec-rework/reviews/nc012a_guard.sh [--require-impl rest|server|client|all]`（learn_system 内运行，只读）。

## Stop Conditions

契约有两种以上解释；需要改白名单外文件或既有测试期望；参考值按契约实现后仍对不上（含 mention 向量）；全量 pytest 的失败集合不再恰为五个既有 ID；10 并发测试重试 5 次仍 503；`check_examples.py` 拒收契约示例；需要新增文案；`flutter pub get` 改动锁文件。遇到即停：在本线交付报告追加「## 待裁决」（现象、命令、原文、你看到的选项），对话最后单独输出一行 `NC-012a-<字母> 停手待裁决`。

## 执行顺序（三线并行，同仓库串行）

- REST：`act/01`（NC-012a-A，dart test 73 → 77）。
- SERVER：`act/02`（NC-012a-B，赞踩与收藏、集合、规则，pytest 496 → 515 passed；rules 89 → 129）→ `act/03`（NC-012a-C，分享、举报、R7、ACL E4，→ 535 passed、6 xfailed）。
- CLIENT：`act/04`（NC-012a-D，MentionRef 单一化、mention 校验、模型/API/队列/待处理页，flutter test 270 → 281）→ `act/05`（NC-012a-E，互动与分享控制器，→ 289）→ `act/06`（NC-012a-F，界面与挂载，→ 296）。

每步一个提交（act/02 在 SERVER 与 RULES 各一个）。交付报告写入本目录且不入库：`DELIVERY_REPORT_REST.md`、`DELIVERY_REPORT_SERVER.md`、`DELIVERY_REPORT_CLIENT.md`。

## 阅读顺序

1. 本 README；2. `openspec/annotation-community/contracts/community_interactions.md`；3. `community_api.md` §4.1、§7、§12；4. [BDD](BDD.md)、[TDD](TDD.md)；5. [ACT](ACT.yaml) 与本线 act/*.yaml；6. [ACCEPTANCE](ACCEPTANCE.md)；7. [PROMPT](PROMPT.md) 中本线一节。
