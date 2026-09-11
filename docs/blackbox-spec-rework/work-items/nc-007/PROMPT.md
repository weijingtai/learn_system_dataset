# NC-007 执行提示

发送前提：NC-006 已 ACCEPTED，且主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你在 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git 仓库，NC-004/NC-005/NC-006 已建立）执行 NC-007：实现历史修订列表、纯本地长文差异对比、多分支冲突检测与 PRD 旅程 6 四选项冲突处理完整路径。`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 仓库只读。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-007/` 下的 README.md、BDD.md、TDD.md、ACT.yaml、act/01～04.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/revision_history.md`（全文）、`local-persistence.md` §5、`editor.md`、`editor_history.md`；`reading-notes/lib/src/domain/`、`lib/src/persistence/` 与 `lib/src/editor/`（只读）。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。先实现后补测试即违反流程，须如实写明。

**只允许写**：各 ACT 的 WRITE_NEW 清单（全部在 `reading-notes/lib/src/history/`、`test/history/`，加 `lib/reading_notes.dart` 导出）。禁止：learn_system 任何写入；修改 NC-004、NC-005、NC-006 保护文件与测试；改 `pubspec.yaml`/`pubspec.lock`；调用任何服务端明文 diff 接口；`skip`、永真断言；直接物理删除旧修订。

**判据来源**：算法规则、四选项文案、无障碍标签、状态机只来自 `revision_history.md`；期望值只来自 TDD。契约有两种以上解释、需要改保护文件或新增依赖：立即停止并原样报告，不自行裁定。

**提交**：四步各一个提交，在 `reading-notes` 仓库内，只 `git add` 本步文件，不 push。提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败原文；
3. Green：该 ACT VERIFICATION 每条命令的退出码与输出末 20 行；
4. act/04 另附 `flutter test` 全量末 5 行（应 `+145: All tests passed!`）与 `nc007_guard.sh --require-impl` 退出码；
5. 跳过项、未运行项与剩余风险。

不要把本任务说成 NC-007 之外的任何任务完成：图片清理、发布 UI、回收站与同步备份都在后续任务。
