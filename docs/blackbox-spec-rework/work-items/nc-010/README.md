# NC-010：客户端命令队列、公共 API 客户端、发布状态与页面

状态：`READY`（2026-09-11：R1 返工 7 项 + 2 建议、R2 返工 2 项均落实；记录见 `reviews/NC-010-REVIEW-R1.md`）。派发前置：**NC-003 ACCEPTED**（2026-09-11 已满足，REST 仓 `5730ed9`）；NC-009 不是前置（本任务全部用 `MockClient`，真实端到端归 NC-024，D-NC010-06）。执行由用户交外部 Agent，PROMPT.md 原样发送。task_id：`NC-010`。权威需求来源：TASKS NC-010；PRD 旅程 1/3/5/9、§5.1、§6.2、§6.4；DESIGN §4.2、§7.4；state-machines SM-2a/SM-3/SM-5；契约 `contracts/community_client.md`（本任务专属）与 `community_api.md`（含 §10）。

## Goal

在 reading-notes 包内实现：公共 API 类型化客户端（W1～W6、R1、R5、R6，`http 1.6.0`）、独立 `CommunityDatabase` 持久命令队列（重启同键恢复、R5 对账、退避、取消规则）、发布状态缓存与作者视角八档文案、发布控制器（预览切换修订、就绪判定、首次发布后果说明、服务器确认前不报成功、版本冲突保留私人稿）、四个页面（笔记列表、公开详情、发布预览、待处理队列）与三个确认层、四屏七状态矩阵。执行者不做设计：表、状态、文案、判定顺序全部来自契约。

## Scope

- 允许写：仅 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/` 内：`pubspec.yaml`（仅追加 `http: 1.6.0` 一行）、`pubspec.lock`、`lib/reading_notes.dart`（追加导出）、`lib/src/community/**`（含 Drift 生成的 `community_database.g.dart`）、`test/community/**`。
- 只读：NC-004～NC-007 的 `lib/src/{domain,persistence,editor,history}` 与全部既有测试（`notes.pending_op` 只经 `NoteRepository.db` 的 Drift API 写入，不改这些文件，D-NC010-03）；learn_system 契约。
- 禁止：写入 learn_system；改 NC-004～NC-007 文件；引入 `firebase_auth`/`cloud_firestore` 或契约外依赖；真实网络；`skip`、永真断言；在测试内调用被测函数生成期望值（payload_hash 用契约 §8 字面量）；先实现后补测试。

## Inputs

契约 `community_client.md` §1（包与存储）、§2（端口）、§3（API 客户端）、§4（命令队列表与状态机）、§5（缓存、作者文案、发布流程）、§6（页面七状态与确认层）、§7（测试名）、§8（payload_hash 参考值）、§9（决定）；`community_api.md` §2～§7、§10（请求/响应 Schema、错误码、可空写法）。

## Dependencies / Baseline

- reading-notes HEAD `9b35e97`（NC-007 ACCEPTED），`flutter test +150`，`flutter analyze` 0；pub-cache 含 `http-1.6.0`、`http_parser-4.1.2`。
- 共享守卫：`bash docs/blackbox-spec-rework/reviews/nc010_guard.sh --require-impl`（只读）；K01 失败判外部失败，K02 及以后按本任务失败停工。

## Stop Conditions

契约有两种以上解释；`flutter pub get` 引入 `http 1.6.0` 改变 NC-004 锁定的九个版本；需要改 NC-004～NC-007 文件（例如想往 `NoteDatabase` 加表或读写 `notes.pending_op`）；`build_runner` 为新库生成代码时改动既有 `note_database.g.dart`；需要契约外依赖。遇到即停，原样报告。

## 执行顺序

`act/01`（端口、模型、API 客户端，6 测试）→ `act/02`（CommunityDatabase 与命令队列，14 测试）→ `act/03`（缓存、作者文案、发布控制器、pending_op 回写，9 测试）→ `act/04`（页面、确认层、申诉入口与 paused 重试，8 测试）→ `act/05`（四屏七状态参数化，25 测试）。每步一个提交，全量 `+150 → +156 → +170 → +179 → +187 → +212`。

## 一次性交付与阅读顺序

1. 本 README；2. `contracts/community_client.md`；3. `contracts/community_api.md` §5、§10；4. [BDD](BDD.md)、[TDD](TDD.md)；5. [ACT](ACT.yaml) 与 act/01～05；6. [ACCEPTANCE](ACCEPTANCE.md)；7. [PROMPT](PROMPT.md)。
