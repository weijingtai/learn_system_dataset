# NC-010 执行提示

发送前提：wjt-react 四查判定 READY；SUBAGENT_TODO 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-010：在 Flutter 包 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git 仓库；`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 只读）内实现注解社区客户端：公共 API 客户端、持久命令队列、发布状态与控制器、四个页面、三个确认层与七状态矩阵。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-010/` 下 README.md、BDD.md、TDD.md、ACT.yaml、act/01～05.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/community_client.md`（全文逐字照做）与 `community_api.md` §2～§7、§10；reading-notes 的 `lib/src/domain/`、`lib/src/persistence/note_repository.dart`、`lib/src/editor/markdown_preview.dart`、`lib/src/history/`（只读）。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。act/05 若有用例一开始即绿，逐个列名并说明原因。

**只允许写**：`pubspec.yaml`（仅追加 `http: 1.6.0`）、`pubspec.lock`、`lib/reading_notes.dart`（追加导出）、`lib/src/community/**`、`test/community/**`。禁止：修改 NC-004～NC-007 的 `lib/src/{domain,persistence,editor,history}` 与既有测试（`notes.pending_op` 只经 `NoteRepository.db` 的 Drift API 写入）；`firebase_auth`/`cloud_firestore` 或其他新依赖；真实网络（测试一律 `package:http/testing.dart` 的 `MockClient`）；在测试内计算 payload_hash 期望值（用契约 §8 字面量）；`skip`、永真断言。

**判据**：只来自两份契约与 TDD/BDD。契约两种解释、`http 1.6.0` 改变既有锁定版本、需要改 NC-004～NC-007 文件、`build_runner` 改动 `note_database.g.dart`：立即停止并原样报告。

**提交**：五步各一个提交，只 `git add` 本步文件，不 push；提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：写入 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-010/DELIVERY_REPORT.md`（不 git add）。每步：commit 哈希与 `git show --stat` 原文；Red 命令/退出码/原文；VERIFICATION 每条命令的退出码与末 20 行；act/01 另附 `pubspec.lock` 中 `http` 与既有九个包的 version 行；act/05 另附 `flutter test` 全量末 5 行（应 `+212: All tests passed!`）与 `nc010_guard.sh --require-impl` 退出码；跳过项与剩余风险。不要把真实宿主端到端、图片上传、评论计数说成完成。

# NC-010 act/06 返工执行提示（2026-09-11 验收 R1 后追加）

发送前提：act/01～05 已提交（reading-notes `bd894b4`…`46a5ebf`）。主 Agent 经 `~/tmux-agents` 派给 agy；分隔线以下全文即提示词。

---

你执行 NC-010 的返工步 act/06：在 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，不要在那里执行 git）以 `46a5ebf` 为基线修 payload_hash 的两处规范化缺陷。Flutter：`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`（每条命令都带上）。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-010/act/06.yaml`、同目录 `TDD.md` §6b、`BDD.md` B39～B40、`ACCEPTANCE.md` 末尾「验收记录 R1」；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_client.md` §4 表 `payload_hash` 行、§8、§10（逐字照做）。

**要做的事**：① `lib/src/community/command_queue.dart` 的 `computePayloadHash`：`payload` 恒含 `'if_match'` 键，`ifMatch` 为 null 时值为 null（不要用 `?ifMatch` 省略）；② `_canonicalJson`：对象键按 Unicode 码点升序排序（逐个比较 `String.runes`），不再用 `List<String>.sort()`；③ `test/community/command_queue_test.dart` 追加 TDD §6b 的 2 个测试，名称逐字，期望哈希写字面量，U+FF41 与 U+1F600 在 Dart 源码中写成 `'\uFF41'` 与 `'\u{1F600}'` 转义。

**基线**：`46a5ebf` 上 `flutter test` 为 `+212: All tests passed!`、`flutter analyze` 0 issues；最终应为 `+214` 与 0 issues。

**先写测试再改实现**：先追加 2 个测试，运行 `flutter test test/community/command_queue_test.dart` 取得 Red 原文（期望 `+14 -2`），再改实现。

**只允许写**：act/06.yaml 的 WRITE_NEW 清单。禁止：清单外任何文件；新依赖；`skip`；永真断言；测试内计算期望哈希；改既有测试期望；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：既有测试（尤其 `payload_hash_matches_python_reference`）变红；需要改清单外文件或既有期望；按契约实现后参考值仍对不上；任何拿不准的取舍。停止时先在交付报告追加「## act/06 待裁决」段（现象、命令、原文、你看到的选项），然后在对话最后单独输出一行 `NC-010-F 停手待裁决`，不再继续。

**提交**：一个提交，只 `git add` 本步两个文件，不 push；提交消息 `fix(community): payload_hash 恒含 if_match 并按码点排序键（NC-010-F）`，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：追加到 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-010/DELIVERY_REPORT.md`（不 git add），标题「### 3.6 act/06（NC-010-F）」：commit 哈希与 `git show --stat`；Red 命令、退出码、原文；act/06.yaml VERIFICATION 每条命令的退出码与末 20 行。全部完成后在对话最后单独输出一行 `NC-010-F 完成`。
