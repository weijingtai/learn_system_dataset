# NC-017：口令加密导出文件格式与本机原子写入

状态：`ACCEPTED`（2026-09-12 主 Agent 验收 R1：reading-notes `e913b14`、`4a0d70a`，flutter test +253，Python 独立解码与 5 项盲测全部通过，见 ACCEPTANCE.md）。曾为 `DISPATCHED`（2026-09-12：agy 四查 R1 READY、返工 0 项，见 `reviews/NC-017-REVIEW-R1.md`；NC-011 CLIENT 线 `463835e` 提交后经 tmux + cmd（deepseek/deepseek-v4.1-flash）派发，会话 nc017）。派发前置：NC-004、NC-015 `ACCEPTED`（已满足）；**NC-011 CLIENT 线（act/06）已提交**（同一 reading-notes 工作树，D-NC017-11）。task_id：`NC-017`。权威需求来源：TASKS NC-017；PRD R-13、旅程 7；DESIGN 第 50 行 BackupManifest、§5（S6）、§7.4；契约 `contracts/private_export.md`（本任务专属）。

## Goal

在 reading-notes 内交付 v1.6 S6 模型下唯一的恢复依据：口令加密导出文件。格式层写死容器、清单、Argon2id 参数、带 AAD 的分块 AES-256-GCM 与统一失败语义，并以 OpenSSL/Python 计算的参考值做跨实现核对；写入器从本地仓库收集 active 与 trashed 笔记的完整修订链与附件，经 `.partial` 临时文件、重读校验摘要后原子改名。执行者不做设计：字节布局、参数、异常、测试名全部来自契约。

## Scope

- 允许写：reading-notes 的 `pubspec.yaml`（仅追加 `cryptography: 2.9.0`）、`pubspec.lock`、`lib/src/export/export_bundle_format.dart`、`lib/src/export/export_writer.dart`、`lib/reading_notes.dart`（追加两行导出）、`test/export/export_bundle_test.dart`。
- 禁止：其他任何文件；新增 cryptography 以外的依赖；真实网络；`skip`；永真断言；测试内调用被测函数生成参考值；先实现后补测试；`git push`；删除文件。

## Dependencies / Baseline

- reading-notes：NC-011 act/06 提交（`flutter test` `+239`、`flutter analyze` 0）。开工前以 `git log --oneline -1` 核对提交信息含 `NC-011-F`，否则停手。
- 本机：`~/.pub-cache/hosted/pub.dev/cryptography-2.9.0` 已存在；`flutter pub get --offline` 实测只新增该包。
- 共享守卫：`bash docs/blackbox-spec-rework/reviews/nc017_guard.sh [--require-impl]`（learn_system 内，只读）。

## Stop Conditions

契约有两种解释；参考值 K、D、头部字节、明文摘要、nonce、块摘要或文件摘要按契约实现后对不上；`flutter pub get --offline` 改动 cryptography 以外的锁定版本；需要改白名单外文件（例如 `NoteRepository` 没有契约假定的只读查询途径）；既有测试变红。遇到即停：在 `DELIVERY_REPORT.md` 追加「## 待裁决」，对话最后单独输出 `NC-017-<A|B> 停手待裁决`。

## 执行顺序

`act/01`（NC-017-A，格式层，E01～E08，flutter test +239 → +247）→ `act/02`（NC-017-B，写入器，E09～E14，→ +253）。每步一个提交。交付报告写入本目录 `DELIVERY_REPORT.md`，不入库。

## 一次性交付与阅读顺序

1. 本 README；2. `openspec/annotation-community/contracts/private_export.md`；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～02；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)。
