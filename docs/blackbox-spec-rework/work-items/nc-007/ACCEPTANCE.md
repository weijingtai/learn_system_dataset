# NC-007 验收规格与记录

当前状态：`ACCEPTED`（2026-09-11 验收通过）

---

## 1. 提交与范围核对
- 仓库：`reading-notes` 独立仓库四步四个独立提交：
  1. `29f6065`: `feat: 纯本地长文差异算法与段落折叠导航（NC-007-A）`
  2. `033392d`: `feat: 历史修订列表与不可变恢复旧版（NC-007-B）`
  3. `5e970f8`: `feat: 多分支冲突检测与四选项决策控制器（NC-007-C）`
  4. `8a910a2`: `feat: 冲突顶部横幅、对照视图与手动合并编辑（NC-007-D）`
- 范围：只包含 `lib/src/history/` 下四个新建文件、`test/history/` 下三个测试文件，以及 `lib/reading_notes.dart` 追加导出；
- 保护文件：`git diff 00f6fc9 HEAD --stat -- pubspec.yaml pubspec.lock lib/src/domain lib/src/persistence lib/src/editor test/persistence test/contracts test/editor` 经检验严格为空；
- 外部调用：`grep -rn 'http' lib/src/history/` 经检验严格无输出。

---

## 2. 自动化验证命令全量执行
1. `flutter analyze` 输出：`No issues found!`（0 issues）；
2. `flutter test test/history/revision_compare_test.dart` 8 个测试全过；
3. `flutter test test/history/revision_history_test.dart` 8 个测试全过；
4. `flutter test test/history/revision_conflict_test.dart` 16 个测试全过；
5. 全量 `flutter test`：`+145: All tests passed!`；
6. 专项目门禁：`bash docs/blackbox-spec-rework/reviews/nc007_guard.sh --require-impl` 退出码 0，失败条数 0（K01～K05 全部 PASS）。

---

## 3. 语义与合规核对
- 恢复旧版调用 `restoreRevision` 生成新修订并携带 `restoredFrom`，不破坏既有历史；
- 冲突四选项严格按文案「保留本机」「采用对方」「手动合并」「稍后处理」执行；
- 选稍后处理后横幅在本次会话关闭，输入与自动保存正常进行，不阻断常规编辑；
- 手动合并工作区接入撤销/重做栈支持；
- 0 处 `skip`，0 处永真断言；
- 完整执行证据见 `xuan-migration/reading-notes/DELIVERY_REPORT.md`。

