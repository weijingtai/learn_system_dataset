# NC-004 执行提示

发送前提：wjt-react 四查判定 READY，且主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-004：在 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（当前不存在，由你创建并 `git init`）建立 Flutter 包 `reading_notes`。`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 仓库只读。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-004/` 下的 README.md、BDD.md、TDD.md、ACT.yaml、act/01～05.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/local-persistence.md`（全文）、`community-models.md` §1/§5/§6、`state-machines.md` SM-1/SM-3/SM-5；`fixtures/community/content_hash_cases.json`。可参考 `xuan-migration/xuan-storage/drift/` 的 Drift 写法与测试风格，但不得 import 或复制其代码。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。先实现后补测试即违反流程，须如实写明。

**只允许写**：`reading-notes/` 内各 ACT 的 WRITE_NEW 清单。禁止：learn_system 任何写入；xuan-migration 其他目录；契约 §1 之外的依赖（含 `^` 范围、persistence_drift、persistence_core、flutter_markdown_plus）；`NativeDatabase.memory()` 用于持久化断言；skip、永真断言。

**判据来源**：表、接口、规则、错误类名、常量、依赖版本只来自 `local-persistence.md`；期望值只来自 fixture 与 TDD。契约有两种以上解释、`flutter pub get` 无法按精确版本解析、sqlite3 无法加载、build_runner 因环境失败、需要新依赖：立即停止并原样报告，不自行裁定。

**提交**：五步各一个提交，在 `reading-notes` 仓库内，只 `git add` 本步文件（含生成的 `.g.dart` 与 `pubspec.lock`），不 push。提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败原文；
3. Green：该 ACT VERIFICATION 每条命令的退出码与输出末 20 行；
4. act/01 另附 `pubspec.lock` 中九个包的 version 行；act/05 另附 `flutter test` 全量末 5 行（应 `+35: All tests passed!`）与 `nc004_guard.sh --require-impl` 退出码；
5. 跳过项、未运行项与剩余风险。

不要把本任务说成 NC-004 之外的任何任务完成：编辑器、Undo、回收站、同步与备份都在后续任务。
