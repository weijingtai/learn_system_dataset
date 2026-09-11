# NC-005 执行提示

发送前提：wjt-react 四查判定 READY；**NC-004 已 ACCEPTED**；主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-005：在已存在的 Flutter 包 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git 仓库，NC-004 已建立）内实现编辑器控制器、三态保存指示、Markdown 预览与编辑页。`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 仓库只读。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-005/` 下的 README.md、BDD.md、TDD.md、ACT.yaml、act/01～04.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/editor.md`（全文）、`local-persistence.md` §3/§5、`state-machines.md` SM-1；`reading-notes/lib/src/domain/` 与 `lib/src/persistence/`（NC-004 产物，只读）。可查看 `~/.pub-cache/hosted/pub.dev/flutter_markdown_plus-1.0.12/lib/src/widget.dart` 核对参数名，但不得复制其代码。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。先实现后补测试即违反流程，须如实写明。

**只允许写**：各 ACT 的 WRITE_NEW 清单（全部在 `reading-notes/lib/src/editor/`、`test/editor/`、`test/support/`，加 `pubspec.yaml` 一行、`pubspec.lock`、`lib/reading_notes.dart` 导出）。禁止：learn_system 任何写入；修改 NC-004 的 domain/persistence 文件与其测试；契约外依赖；注册 `Shortcuts`/快捷键；实现 undo 栈；真实网络；`skip`、永真断言。

**判据来源**：状态、边、文案、阈值、参数名只来自 `editor.md`；期望值只来自 TDD。契约有两种以上解释、`flutter_markdown_plus` 1.0.12 实际参数与契约 §5.1 不符、`markdown` 传递依赖与 NC-004 锁定冲突、需要改 NC-004 文件或新增依赖：立即停止并原样报告，不自行裁定。

**提交**：四步各一个提交，在 `reading-notes` 仓库内，只 `git add` 本步文件，不 push。提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败原文；
3. Green：该 ACT VERIFICATION 每条命令的退出码与输出末 20 行；
4. act/01 另附 `pubspec.lock` 中 `flutter_markdown_plus` 与 `markdown` 的 version 行；act/04 另附 `flutter test` 全量末 5 行（应 `+74: All tests passed!`）与 `nc005_guard.sh --require-impl` 退出码；
5. 跳过项、未运行项与剩余风险。

不要把本任务说成 NC-005 之外的任何任务完成：撤销栈、快捷键、历史旅程、同步与备份的真实状态都在后续任务。
