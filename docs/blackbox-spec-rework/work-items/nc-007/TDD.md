# NC-007 测试驱动与验证计划（TDD）

所有命令运行于 `export PATH=/Users/jingtaiwei/flutter/bin:$PATH`；工作目录为 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`。

---

## 1. 验证命令清单

| # | 命令 | 期望结果 |
|---|---|---|
| 1 | `flutter analyze` | 0 issues |
| 2 | `flutter test test/history/revision_compare_test.dart` | act/01 完成后 `+8: All tests passed!` |
| 3 | `flutter test test/history/revision_history_test.dart` | act/02 完成后 `+8: All tests passed!` |
| 4 | `flutter test test/history/revision_conflict_test.dart` | act/03 完成后 `+8`，act/04 完成后 `+16: All tests passed!` |
| 5 | `flutter test` | 全量测试 `+145: All tests passed!` |
| 6 | `git diff <基线提交> HEAD --stat -- pubspec.yaml pubspec.lock` | 空（无依赖改动） |
| 7 | `grep -rn 'http' lib/src/history/` | 无输出（零外部 HTTP API 调用） |
| 8 | `bash docs/blackbox-spec-rework/reviews/nc007_guard.sh --require-impl` | 退出码 0，0 失败 |

---

## 2. 步骤详情与 Red 原文规划

### 2.1 act/01：纯本地差异算法与长文折叠（NC-007-A）
- 目标文件：`lib/src/history/revision_compare.dart`、`test/history/revision_compare_test.dart`
- 8 个测试用例：
  1. `diff computes inserted and deleted line blocks`（B01）
  2. `diff preserves line ranges for multi-line edits`（B02）
  3. `diff collapses unchanged lines over threshold of 3`（B03）
  4. `diff expands collapsed chunk on demand`（B04）
  5. `diff navigates next and previous change blocks`（B05）
  6. `diff handles edge insertions and deletions without out-of-bounds`（B06）
  7. `diff handles 1 MiB markdown document without stack overflow`（B07）
  8. `diff executes purely locally without network`（B08）
- Red 捕获：先写 8 个测试与抛出 `UnimplementedError` 的空壳类，运行命令 2 记录失败原文。

### 2.2 act/02：历史修订列表展示与恢复旧版（NC-007-B）
- 目标文件：`lib/src/history/revision_history_page.dart`、`test/history/revision_history_test.dart`
- 8 个测试用例：
  1. `history list displays all revisions sorted by date`（B09）
  2. `history list marks head branches and preferred head`（B10）
  3. `history list shows full snapshot content in preview mode`（B11）
  4. `restore revision creates new revision with restoredFrom field`（B12）
  5. `restore revision does not delete or mutate prior history`（B13）
  6. `history page renders correctly with single initial revision`（B14）
  7. `history page handles missing revision gracefully`（B15）
  8. `history page listRevisions matches repository contents`（B09/B10）
- Red 捕获：先写 8 个测试，运行命令 3 记录失败原文。

### 2.3 act/03：多分支冲突控制器与状态机（NC-007-C）
- 目标文件：`lib/src/history/revision_conflict_controller.dart`、`test/history/revision_conflict_test.dart`
- 8 个测试用例：
  1. `conflict controller is clean when single head exists`（B16）
  2. `conflict controller enters conflict state on two or more heads`（B17）
  3. `keep local action merges heads with local preferred content`（B18）
  4. `adopt remote action merges heads with remote content`（B19）
  5. `resolve later action dismisses banner without blocking edits`（B20）
  6. `editing continues and autosaves to preferred head after dismiss`（B21）
  7. `new incoming head does not overwrite draft in progress`（B22）
  8. `conflict controller operations only call public repository API`（B23）
- Red 捕获：先写 8 个测试，运行命令 4 记录失败原文。

### 2.4 act/04：冲突横幅、对照视图与手动合并（NC-007-D）
- 目标文件：`lib/src/history/conflict_banner.dart`、`lib/src/history/revision_conflict_controller.dart`、追加到 `test/history/revision_conflict_test.dart`、`lib/reading_notes.dart` 导出
- 8 个测试用例：
  1. `conflict banner shows on multi-head and hides on single-head`（B24）
  2. `typing in editor is not blocked by conflict banner`（B25）
  3. `tapping view compare opens compare view with side-by-side diff`（B26）
  4. `compare view displays four option buttons verbatim`（B27）
  5. `tapping resolve later in compare view dismisses banner`（B28）
  6. `tapping keep local in compare view resolves conflict`（B29）
  7. `tapping adopt remote in compare view updates content and resolves`（B30）
  8. `manual merge workflow supports undo redo and commits merged head`（B31/B32）
- Red 捕获：追加 8 个测试，运行命令 4 记录后 8 个测试的失败原文。
- Green 验证：全量命令 1～8 必须全绿，全量测试达到 `+145: All tests passed!`。
