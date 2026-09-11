# NC-004：可靠保存与不可变修订（CLIENT 建仓 + Drift 修订库）

状态：`PREPARING`（六件套已产出，待 wjt-react 四查）。task_id：`NC-004`。权威需求来源：`openspec/annotation-community/TASKS.md` NC-004；DESIGN §3、§3.1、§3.2、§4.4、§5、§7.1、§7.2；契约 `openspec/annotation-community/contracts/local-persistence.md`（本任务专属，主 Agent 编写）、`community-models.md` §1、`state-machines.md` SM-1/3/5；fixture `fixtures/community/content_hash_cases.json`。分支（learn_system）：`codex/docs/knowledge-compilation`。

## Goal

建立独立 Flutter 包 `reading_notes`（新 Git 仓库），实现 Dart 侧 nchash/v2 与跨端一致性测试、Drift 修订库、事务保存仓储与 outbox 外层信封，全部以真文件数据库测试通过。执行者不做设计：表、接口、规则、错误类名、常量全部来自 `local-persistence.md`。

## Scope

- 允许写：仅 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/` 目录内（新建；在其中 `git init`，四个 ACT 各一个提交，不 push）。
- 只读：本工作包、三份契约、`fixtures/community/content_hash_cases.json`（复制为 `reading-notes/test/fixtures/community_content_hash_cases.json`，字节相同）、`xuan-storage/drift/`（只看写法，不 import、不复制代码）、DESIGN/TASKS。
- 禁止：写入 learn_system 任何文件、写入 xuan-migration 其他子目录或父目录、在父目录执行 git；引入契约 §1 之外的依赖（含 `persistence_drift`、`persistence_core`、`flutter_markdown_plus`）；`^` 版本范围；用 `NativeDatabase.memory()` 充当持久化测试；`skip`、永真断言；先实现后补测试。

## Inputs

`local-persistence.md` §1（工程）、§2（表）、§3（模型/错误/常量）、§4（信封）、§5（仓储接口与八条保存规则）、§5.2（失败注入点）、§6（nchash Dart）、§7（决定 D-NC004-01～07）。

## Dependencies / Baseline

- NC-002 fixture `content_hash_cases.json`（198 项中的 44 项属 content_hash）已冻结；NC-002 的 SERVER 实现是否完成不影响本任务（两端各自对同一 fixture）。
- Flutter 3.44.6 / Dart 3.12.2 位于 `/Users/jingtaiwei/flutter/bin`；执行者用 `export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。
- pub-cache 已有 drift 2.31.0、drift_dev 2.31.0、drift_flutter 0.2.8、sqlite3 2.9.4、sqlite3_flutter_libs 0.5.42、path_provider 2.1.6、build_runner 2.15.1、crypto 3.0.7、flutter_lints 6.0.0（主 Agent 2026-09-11 核对 `~/.pub-cache/hosted/pub.dev`）；`flutter pub get` 允许联网解析传递依赖，但不得改变上述精确版本。
- `reading-notes` 目录当前不存在（NC-001 基线 `client.state=PLANNED_NEW`）；父目录 `xuan-migration` 存在且不是 Git 仓库。
- 宿主机 macOS 自带 `libsqlite3`，`persistence_drift` 的 131 个测试即以此运行；若 `flutter test` 报无法加载 sqlite3 → 停止上报。
- 共享守卫：本任务不触碰 learn_system，唯一的 learn_system 侧命令是 `bash docs/blackbox-spec-rework/reviews/nc004_guard.sh --require-impl`（只读）；其 K01 因并行线改动失败判外部失败，K02 及以后按本任务失败停工。

## Stop Conditions

契约存在两种以上解释；`flutter pub get` 无法在精确版本下解析（含 crypto 3.0.6）；`build_runner` 生成失败且原因不在本任务代码；sqlite3 无法加载；需要写目录之外的文件；需要新增依赖。遇到即停，原样报告。

## 执行顺序

`act/01`（建仓 + nchash Dart + 一致性测试）→ `act/02`（模型、错误、Drift 库与生成文件）→ `act/03`（仓储保存规则）→ `act/04`（恢复/合并、失败回滚、重开、会话隔离、outbox）。每步一个提交在 `reading-notes` 仓库。

## 一次性交付与阅读顺序

1. 本 README；2. `local-persistence.md`；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～04；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)（READY 后原样发送）。
