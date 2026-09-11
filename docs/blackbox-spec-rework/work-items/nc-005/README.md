# NC-005：Markdown 编辑、预览与保存状态

状态：`READY`（2026-09-11 两轮 wjt-react 四查：R1 REWORK 3 项 + 3 建议、R2 READY；记录见 `reviews/NC-005-REVIEW-R1.md`）。派发前置 NC-004 ACCEPTED 已于 2026-09-11 满足（reading-notes `957536c`）。执行由用户交外部 Agent，PROMPT.md 原样发送。task_id：`NC-005`。权威需求来源：TASKS NC-005；DESIGN §3、§3.1、§5；PRD §4、§4.1（A11Y-04/05/07）、§6.1、§6.2；契约 `openspec/annotation-community/contracts/editor.md`（本任务专属，主 Agent 编写）、`local-persistence.md`、`state-machines.md` SM-1。

## 撤销栈归属裁定（TASKS NC-005 第 2 条，供 NC-006 直接消费）

**方案 b**：`editor_history_adapter`（NC-006 新建）是唯一真源；`TextField` 的 `undoController` 参数交给 adapter 的控制器，平台 `UndoHistory` 不再维护第二个栈；NC-005 只在控制器上预留 `onHistoryStep` 回调与 `applySnapshot` 入口，不注册快捷键。细则见契约 §4。

## Goal

在 NC-004 建立的 `reading_notes` 包内实现：编辑态状态机控制器（SM-1 全部边，含非法边）、2 秒去抖自动保存与失焦/返回 flush、三态保存指示（PRD §6.1 文案闭集、400 ms 抑制、semantics）、Markdown 预览（`flutter_markdown_plus 1.0.12`，HTML 不执行、外部图片默认不加载、`attachment://` 经解析器渲染）、编辑页与 A11Y-04/05/07 断言。执行者不做设计：状态、文案、阈值、参数名全部来自契约。

## Scope

- 允许写：仅 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/` 内：`lib/src/editor/{note_editor_controller.dart,save_status.dart,markdown_preview.dart,note_editor_page.dart}`、`test/editor/{save_status_test.dart,note_editor_test.dart,markdown_preview_test.dart,note_editor_page_test.dart}`、`test/support/{fake_repository.dart,fake_clock.dart,counting_image_resolver.dart}`、`pubspec.yaml`（仅追加 `flutter_markdown_plus: 1.0.12` 一行）、`pubspec.lock`（随 pub get 更新）、`lib/reading_notes.dart`（追加导出）。
- 只读：NC-004 的全部文件（不改）、三份契约、DESIGN/PRD/TASKS、`~/.pub-cache/hosted/pub.dev/flutter_markdown_plus-1.0.12/`（只看不复制）。
- 禁止：写入 learn_system；改 NC-004 的 domain/persistence 文件；新增契约 §1 之外的依赖；注册任何快捷键或 `Shortcuts`（NC-006）；实现 undo 栈（NC-006）；网络请求；`skip`、永真断言；先实现后补测试。

## Inputs

契约 `editor.md` §2（控制器接口与 SM-1 边）、§3（三态文案闭集与 400 ms）、§4（undo 归属）、§5/§5.1（预览与 1.0.12 参数）、§6（A11Y）、§7（决定）。

## Dependencies / Baseline

- **NC-004 ACCEPTED**（`reading-notes` 五个提交、`flutter test +35`）；本任务开工基线记录 NC-004 最后提交 hash 与 `flutter test` 计数。
- `flutter_markdown_plus-1.0.12` 与 `markdown-7.3.1` 在 pub-cache；`flutter pub get` 允许解析传递依赖，不得改变 NC-004 已锁定的九个版本。
- 共享守卫：唯一 learn_system 侧命令 `bash docs/blackbox-spec-rework/reviews/nc005_guard.sh --require-impl`（只读）；K01 失败判外部失败，K02 及以后按本任务失败停工。

## Stop Conditions

契约有两种以上解释；`flutter pub get` 引入的 `markdown` 传递依赖与 NC-004 锁定版本冲突；`flutter_markdown_plus` 1.0.12 的实际参数名与契约 §5.1 不符；需要写白名单外文件；需要新依赖；NC-004 未 ACCEPTED。遇到即停，原样报告。

## 执行顺序

`act/01`（三态文案与 semantics）→ `act/02`（控制器 SM-1 与自动保存）→ `act/03`（Markdown 预览与安全）→ `act/04`（编辑页整合与 A11Y）。每步一个提交在 `reading-notes` 仓库。

## 一次性交付与阅读顺序

1. 本 README；2. `contracts/editor.md`；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～04；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)。
