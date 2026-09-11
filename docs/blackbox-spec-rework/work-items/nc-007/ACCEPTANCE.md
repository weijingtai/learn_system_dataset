# NC-007 验收规格与记录

当前状态：`REWORK`（2026-09-11 主 Agent 独立验收：形式门禁通过，盲测发现两处实质缺陷；此前 `4ea5105` 的 ACCEPTED 标记未做盲测与源码审阅，作废）

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



---

## 验收记录 R1（主 Agent，2026-09-11）：REWORK 2 项

- 提交与范围：reading-notes `29f6065`、`033392d`、`5e970f8`、`8a910a2` 恰 4 个；保护路径 diff 为空；`lib/src/history/` 无 http；`nc007_guard.sh --require-impl` K01～K05 全 PASS（analyze 0，`flutter test +145`）。报告四步 Red 原文齐全（`UnimplementedError` 起步）。
- 源码审阅：`DiffBlock`/折叠/导航按契约；历史页经 `listRevisions/getNote/restoreRevision`；冲突控制器四选项经 `mergeHeads`，`commitManualMerge` 带当时最新 heads；横幅非阻断、四选项文案逐字。
- 盲测（临时文件，已删除）：
  - ② 400 组随机多行文本：差异块按顺序拼回与 old/new 逐字相等、行号连续（小规模 Myers 正确）。
  - ③ 折叠边界：4 行未变更折叠为 1+2(折叠)+1，3 行不折叠。
  - ⑤ 真实 Drift 库：`restoreRevision` 生成 `restored_from` 指向源修订、`parent_ids=[当前 head]` 的新修订，旧修订原样保留；两 head 下 `adoptRemote`/`commitManualMerge` 成功，heads 收敛为一个且 `parent_ids` 含原两 head。
  - **① 缺陷**：20 000 行文档只改第 10 行与第 19 990 行，变更行数 39 962（整篇删插，耗时 20 ms）。原因：`_myersDiff` 在中间区 `n+m > 2000` 时无条件返回全删全插。折叠与导航在长文上失效。→ D-NC007-06，act/05。
  - **④ 缺陷**：`ManualMergePage` 用真实 `Timer` 与真实仓储构造 `NoteEditorController`，打字后 2.5 s 内 `saveSnapshot` 被调用；在真实库上复现：自动保存替换首选 head 后 `commitManualMerge` 抛 `HeadConflictError: Head not in current heads`，手动合并无法提交。既有测试的替身在 `mergeHeads` 中不校验 heads，所以未暴露。→ D-NC007-07，act/06。
- 判定：**REWORK**。act/05、act/06 通过后复跑本记录 ①④ 与 ⑤，再关闭 NC-007。
