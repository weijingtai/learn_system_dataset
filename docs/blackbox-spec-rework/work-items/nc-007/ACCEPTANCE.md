# NC-007 验收规格

当前状态：`READY_FOR_EXECUTION`

---

## 1. 提交与范围核对
- 仓库：`reading-notes` 独立仓库四步四个独立提交；
- 范围：只包含 `lib/src/history/` 下四个新建文件、`test/history/` 下三个测试文件，以及 `lib/reading_notes.dart` 追加导出；
- 保护文件：`git diff <基线提交> HEAD --stat -- pubspec.yaml pubspec.lock lib/src/domain lib/src/persistence lib/src/editor test/persistence test/contracts test/editor` 必须为空；
- 外部调用：`grep -rn 'http' lib/src/history/` 必须无输出。

---

## 2. 自动化验证命令全量执行
1. `flutter analyze` 输出必须为 `0 issues`；
2. `flutter test test/history/revision_compare_test.dart` 8 个测试全过；
3. `flutter test test/history/revision_history_test.dart` 8 个测试全过；
4. `flutter test test/history/revision_conflict_test.dart` 16 个测试全过；
5. 全量 `flutter test` 必须报告 `+145: All tests passed!`；
6. 专项目门禁：`bash docs/blackbox-spec-rework/reviews/nc007_guard.sh --require-impl` 必须退出码 0，失败条数 0。

---

## 3. 语义与合规核对
- 恢复旧版调用 `restoreRevision` 生成新修订并携带 `restoredFrom`，不破坏既有历史；
- 冲突四选项严格按文案「保留本机」「采用对方」「手动合并」「稍后处理」执行；
- 选稍后处理后横幅在本次会话关闭，输入与自动保存正常进行，不阻断常规编辑；
- 手动合并工作区接入撤销/重做栈支持；
- 0 处 `skip`，0 处永真断言。
