# 历史、差异、恢复与冲突处理契约（NC-007）

状态：`FROZEN_FOR_NC-007`（2026-09-11）。权威来源：[DESIGN](../DESIGN.md) §3、§3.2、§7.2；[PRD](../PRD.md) §6.1、§6.2、旅程 6、R-04、R-12；[TASKS](../TASKS.md) NC-007；[local-persistence](local-persistence.md) §5。本文将已定设计冻结为历史与冲突处理接口、长文差异规格、四选项处理规则与测试判据，供执行者照做。

---

## 1. 包内位置与依赖

- 目标仓库：`/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git 仓库）。
- 新建文件：
  - `lib/src/history/revision_compare.dart`（长文差异计算、段落折叠与跳跃导航）
  - `lib/src/history/revision_history_page.dart`（历史修订列表展示、快照预览与恢复旧版）
  - `lib/src/history/revision_conflict_controller.dart`（多分支冲突状态机与四选项决策驱动）
  - `lib/src/history/conflict_banner.dart`（编辑页顶部非阻断冲突横幅与对照入口）
  - 测试：
    - `test/history/revision_compare_test.dart`
    - `test/history/revision_history_test.dart`
    - `test/history/revision_conflict_test.dart`
- 追加导出：`lib/reading_notes.dart` 导出 history 关键公开类型。
- 零新依赖：使用 Dart/Flutter 标准库，严禁修改 `pubspec.yaml` 与 `pubspec.lock`。
- 零外部调用：差异比较纯在本地计算，严禁任何形式调用远端服务器明文 diff API。
- 保护文件：严禁修改 NC-004、NC-005、NC-006 既有产物及测试。测试使用已有 `FakeNoteRepository` 或同等接口替身。

---

## 2. 差异算法与长文可读性规格（`revision_compare.dart`）

### 2.1 差异模型
- 比较单元：支持按行（Line-based）或段落块对比。
- 块类型枚举 `DiffBlockType`：
  - `unchanged`（未变更）
  - `inserted`（新增）
  - `deleted`（删除）
- 差异条目 `DiffBlock`：
  - `DiffBlockType type`
  - `String text`
  - `int oldStartLine`
  - `int oldLineCount`
  - `int newStartLine`
  - `int newLineCount`
  - `bool isCollapsed`（是否被折叠）

### 2.2 折叠与导航规则
- **段落折叠阈值**：连续未变更行数超过 `collapseThreshold = 3` 行时，默认折叠中间段落，两端各保留 1 行作为上下文；UI 呈现「展开 N 行未变更」按钮。
- **变更跳跃导航**：提供快速定位到「上一处变更 / 下一处变更」方法，返回对应变更块在列表中的索引。
- **长文本极限验证**：支持 1 MiB 大小的 Markdown 文档输入，差异算法在单线程内稳定完成，不发生堆栈溢出或内存泄漏。

---

## 3. 历史链遍历与恢复旧版（`revision_history_page.dart`）

### 3.1 历史列表
- 数据来源：调用 `NoteRepository.listRevisions(noteId)` 与 `NoteRepository.getNote(noteId)`。
- 修订信息项呈现：
  - 修订 ID（`id`）
  - 创建时间（`createdAt`）
  - 创作设备（`createdOnDevice`）
  - 修改说明（`changeSummary`）
  - 恢复来源（`restoredFrom`，若非空展示「恢复自 <原ID>」）
  - 分支标记：若修订属于 `note.headRevisionIds`，标记为 Head 分支；若等于 `preferredHeadId`，标记为当前活跃首选版本。

### 3.2 恢复旧版语义（DESIGN §3、TASKS NC-007）
- 用户在历史列表中选中任意旧修订点击「恢复此版本」：
- 调用 `NoteRepository.restoreRevision(noteId: noteId, sourceRevisionId: revId)`；
- 仓储以原修订六字段建立全新修订，`restored_from=sourceRevisionId`，`parent_ids=[preferredHeadId]`；
- 完整保留历史链条，严禁物理删除或覆盖既有历史修订。

---

## 4. PRD 旅程 6 多分支冲突处理（`revision_conflict_controller.dart` 与 UI）

### 4.1 冲突判定与非阻断横幅
- **进入冲突态**：当 `headRevisionIds.length >= 2` 时判定存在多 head 分支冲突；
- **非阻断顶部横幅**：
  - 正文默认加载当前本机首选版本（`preferredHeadId`）；
  - 编辑器顶部展示冲突提示横幅「检测到多设备版本冲突，当前展示本机版本」；
  - 正文**完全保持可读、可编辑、可输入并正常触发 2000 ms 自动保存**，横幅绝不阻断任何常规编辑；
  - 横幅提供「查看对照」主操作按钮与「稍后处理」关闭按钮。

### 4.2 四选项决策规格（PRD 旅程 6）
用户点击「查看对照」进入多分支对照视图，提供明确的四选项：
1. **选项一：保留本机（Keep Local）**：
   - 以当前本机 preferredHead 的快照内容，调用 `repository.mergeHeads(noteId: noteId, headIds: currentHeads, merged: localSnapshot)`；
   - 合并后清除冲突 head，保留完整 `parent_ids` 追溯，关闭冲突态。
2. **选项二：采用对方（Adopt Remote）**：
   - 读取冲突的另一分支 head 快照内容，调用 `repository.mergeHeads(noteId: noteId, headIds: currentHeads, merged: remoteSnapshot)`；
   - 采用后正文更新为对方内容，关闭冲突态。
3. **选项三：手动合并（Manual Merge）**：
   - 打开合并编辑工作区，允许用户自由编辑合并文本；
   - 接入 NC-006 撤销/重做栈支持；
   - 用户确认合并后，以合并结果调用 `repository.mergeHeads(noteId: noteId, headIds: currentHeads, merged: manualMergedSnapshot)`。
4. **选项四：稍后处理（Resolve Later）**：
   - 会话标记置为 dismissed，横幅在此次编辑会话中不再自动弹出打扰；
   - 用户可继续自由输入并自动保存至本地 preferred head；
   - 列表项仍保留待处理状态标记，用户后续可随时从历史页面重新唤起合并。

### 4.3 并发保护（TASKS NC-007）
- 在用户正在编辑手动合并稿期间，若检测到第三条分支到达（`headRevisionIds` 增多），严禁自动覆盖用户正在编辑的合并稿；
- 提示用户「有新的分支到达，当前合并稿已保护」，需在提交合并时带上当时最新的全部 heads。

---

## 5. 决定登记（D-NC007）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC007-01 | 差异比较算法完全使用本地纯 Dart 实现，零服务端依赖 | 私人笔记必须端到端隐私保护，严禁调用外部接口发送明文进行对比 |
| D-NC007-02 | 连续未变更行超过 3 行默认折叠 | 保障长文对比时的屏幕阅读效率，避免用户翻页耗费大量时间 |
| D-NC007-03 | 恢复旧版必须走 `restoreRevision` 产生新修订 | 恪守不可变历史原则，防止历史数据被篡改或丢失 |
| D-NC007-04 | 冲突横幅不以 Modal 弹窗阻断编辑 | 恪守 PRD 旅程 6 体验要求，离线或急需记笔记时用户随时可输入保存 |
| D-NC007-05 | 四选项文案闭集固定为「保留本机」「采用对方」「手动合并」「稍后处理」 | 保持与 PRD 逐字一致，便于自动化测试与多语言对齐 |
