# 注解社区（NC 任务）跨机器交接

更新时间：2026-09-12。本文件随 learn_system 推送到 Gitea，是其他机器接手 NC 任务的唯一入口。下方「接手提示词」一节全文可直接交给新机器上的 AI。

## 1. 当前进度（截至 2026-09-12）

| 状态 | 任务 |
|---|---|
| ACCEPTED | NC-002、NC-003、NC-004、NC-005、NC-006、NC-007、NC-009、NC-010、NC-011、NC-012a、NC-015、NC-016a、NC-017；NC-001 的子项 NC-001-01 |
| BLOCKED | NC-001-02（设备/后端/Emulator 联调取证，Firebase 去留待用户决定）；NC-012b、NC-016b（等 NC-001-02）；NC-020b、NC-021、NC-022、NC-023（等上游书籍交付）；NC-024（等全部） |
| BACKLOG | NC-008、NC-013、NC-014、NC-018、NC-019、NC-020a、NC-025、NC-026 |

权威状态以 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 的 NC 各行为准。

## 2. 仓库与本机路径（规格、守卫与 act 中的路径全部是绝对路径，接手机器必须一致或建软链接）

| 仓库（Gitea `http://192.168.0.165:3000/xuan/…`） | 分支 | 本机路径 | 作用 |
|---|---|---|---|
| `learn_system.git` | `codex/docs/knowledge-compilation` | `/Users/jingtaiwei/Git/Public/learn_system` | 契约、六件套、守卫、验收记录、任务总表（与 Dataset 线共用同一分支） |
| `reading-notes.git` | `main` | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes` | CLIENT：笔记、编辑、历史、社区、私人同步、导出 |
| `functions-py.git` | `master` | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（注意不在 xuan-migration 下） | SERVER：社区命令、评论、互动事务（Firestore） |
| `repository_rest_adapter.git` | `main` | `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`（本地目录名是连字符） | REST：OpenAPI 3.1 契约与结构测试 |
| `xuan-server.git` | `main` | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server` | RULES：Firestore 安全规则测试（`server/functions/`） |
| `xuan-storage.git` | `main`；功能分支 `fix/nc016-guard-aad` | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage`，分支检出到 `.worktrees/nc016-guard-aad` | STORAGE：同账号会话 guard 与 AAD 补丁（未合并，合并由仓库所有者决定；agent 禁止改 main） |
| `social.git`、`notification.git` | `main` | `/Users/jingtaiwei/Git/Public/xuan-migration/{social,notification}` | 只读参考（NC-012b、NC-014 注入点） |
| `xuan-handbook.git` | `main` | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-handbook` | 能力台账与接入手册（必须遵守其 PROTOCOL.md） |

`/Users/jingtaiwei/Git/Public/xuan-migration` 是容器目录，不是 git 仓库，绝不在其根目录执行 git。

**Windows 布局（2026-09-12 起并行有效，用户裁定，登记为 D-NC012-23）**：仓库改放 `D:\Programme`——`learn_system → D:\Programme\learn_system`；客户端 `reading-notes、repository-rest-adapter、social、notification、xuan-storage（含 .worktrees/nc016-guard-aad）、xuan-handbook、repository-contract-kernel → D:\Programme\xuan\`；服务端 `functions-py → D:\Programme\xuan-server\functions-py`、`xuan-server → D:\Programme\xuan-server\xuan-server`。Flutter 3.44.6 位于 `D:\apps\apps\flutter\bin`。所有仓检出后执行 `git config core.autocrlf false` 并重建工作区（哈希断言与 bash 脚本都依赖 LF）；venv 解释器在 Windows 是 `.venv/Scripts/python.exe`；守卫内 flutter/dart/npm 经 `shutil.which` 解析。`repository-rest-adapter` 依赖同源兄弟目录 `repository-contract-kernel`（Gitea `xuan/repository_contract_kernel.git`），必须克隆到同级目录。

## 3. 环境

- Flutter `3.44.6`，位于 `/Users/jingtaiwei/flutter/bin`（命令一律带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`）。
- Python 3.14：`functions-py/.venv`（按 `requirements.txt` 安装）；`learn_system/.venv`（守卫与 REST 示例校验使用，需 `jsonschema==4.26.0`、`referencing`、`PyYAML`、`ruamel.yaml`、`check-jsonschema`）。
- Node/npm：`xuan-server/server/functions` 执行 `npm ci`。
- 局域网：Gitea `192.168.0.165:3000`；Firestore Emulator `192.168.0.165:8080`、Auth Emulator `192.168.0.165:9099`（服务端与规则测试必须可达）。
- STORAGE worktree 内 `core`、`drift`、`p2p` 三包各执行一次 `flutter pub get`（依赖经 Gitea git url 拉取）。

## 4. 基线（接手后先复现，对不上即停手报告用户）

| 仓库 | 命令 | 期望 |
|---|---|---|
| reading-notes | `flutter analyze`；`flutter test` | `No issues found!`；`+296: All tests passed!` |
| functions-py | `PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099 .venv/bin/python -m pytest tests -q -rf -p no:cacheprovider` | `5 failed, 535 passed, 6 xfailed`；FAILED 恰为 `tests/test_config.py::test_集合名与_ts_逐项一致` 与 `tests/test_registration.py` 的四个既有失败 |
| xuan-server | `npm test -- community_rules`（`server/functions`，带 Emulator 变量） | `Tests: 129 passed` |
| repository-rest-adapter | `dart test` | `+77: All tests passed!` |
| learn_system | `bash docs/blackbox-spec-rework/reviews/nc012a_guard.sh --require-impl all`（另有 nc011、nc016a、nc017 守卫） | 退出 0 |

## 5. NC-012a 验收收尾

已于 2026-09-12 验收 `ACCEPTED`（`work-items/nc-012a/ACCEPTANCE.md` 文末验收记录 R1）。两件遗留事项已闭环（2026-09-12，zcode 复核）：① `functions-py/tests/test_community_acl_sweep.py` 文档字符串经核对已在主线提交 `8d22451` 中修正（Implemented/Unimplemented 两行已含 E4），无需再改；② xuan-handbook 条目 `social.community-interactions` 的接入手册已按 PROTOCOL §9 补写并推送（xuan-handbook `f88e70b`），条目已按 §5 判定 `done`。

## 6. 后续顺序建议

1. **NC-013**（事务事件、投递、通知正文与补拉端点）：可立即写契约，消费 `comment.created/edited/deleted` 与 `reaction.liked` outbox 事件；mention 事件与拉黑过滤依赖 NC-012b 的部分拆出。
2. **NC-026**（行为事件与假名化）：前置 NC-002/003/005/009 已满足；「注销」子项等 NC-001 第⑩项证据，其余可做。
3. **NC-020a**（消费端书籍契约核对清单）：无前置，纯文档。
4. **NC-014**（通知宿主适配）：NC-013 之后；回跳挂哪一套通知中心由 NC-001 决定，缺证时停手问用户。
5. **NC-018 / NC-019**：NC-018 依赖 NC-016（16a 已交付、16b 阻塞），开工前先请用户裁定能否按 16a 交付解锁。
6. **NC-025 / NC-008**：依赖 NC-001-02 与 Firebase 去留决定，先向用户确认。

## 7. 工作方法（沿用本仓 G0 准出制度，`openspec/subagent-delivery-gate.md`）

1. 主 Agent 为每个任务写专属契约（`openspec/annotation-community/contracts/`）与六件套（`docs/blackbox-spec-rework/work-items/<task>/`：README、BDD、TDD、ACT.yaml + act/*.yaml、ACCEPTANCE、PROMPT）和守卫脚本（`docs/blackbox-spec-rework/reviews/<task>_guard.sh`），范式照抄 `nc-011`、`nc-012a`。
2. 未参与编写、且不同厂商的审查者按 wjt-react 四查（忠实性、覆盖性、可执行性、独立性）判定 READY；返工不超过 2 轮。
3. 派发执行者：同时运行不超过 2～3 个；同一仓库严格串行；提示词写明白名单、禁止项、停手条件、进度文件与交付报告路径。
4. 执行者遇到歧义、参考值对不上、既有测试变红、需改白名单外文件时**停手上报**；主 Agent 裁定后以 `D-<任务>-<编号>` 登记在契约决定表并同步六件套与守卫。
5. 主 Agent 独立验收，不采信执行方自述：`git diff-tree` 核范围、`<task>_guard.sh --require-impl all`、盲测（临时文件，结束删除并以 `git status --short` 为空证明）、作弊扫描（skip、永真断言、测试内算参考值、真实网络）。
6. 验收通过后更新 `SUBAGENT_TODO.md`、提交，并把相关仓库推送到 Gitea；分叉时用合并，不变基（验收记录引用提交哈希）；禁止 force push。
7. 交付时按 xuan-handbook `PROTOCOL.md` §4 回写能力条目与接入手册。

## 8. 约束与已知坑

- 与用户交流、文档、代码注释以中文为主。
- learn_system 分支与 Dataset 线共用：只暂存本线文件，不暂存他人改动（必要时按 hunk 暂存）；`DELIVERY_REPORT*.md` 不入库。
- 提交信息末尾空一行加 `Co-Authored-By: <执行模型> <noreply@anthropic.com>` 或对应厂商署名。
- 禁止永久删除数据；半成品目录改名保留，由用户决定是否删除（例：`xuan-storage/.worktrees/nc016-guard-aad.partial-20260912`）。
- S6 私人加密模型没有长期密钥、没有云端备份、没有恢复材料，不要评估出「缺恢复材料」。
- 磁盘不主动检查，遇到 ENOSPC 直接告诉用户清理。
- Firestore Emulator 事务锁语义是「写者等待读者」，并发测试用确定性 `Aborted` 注入（见 `community_discussion.md` §8.1），503 以同一 command_id 重试。
- 命令行工具若有默认短超时，pytest/flutter/npm 一律显式设置不少于 600 秒或后台运行后轮询。
- 原机器上的 `rtk` 会改写 `git diff/ls/grep` 输出，核对时用 `/usr/bin/git diff-tree`、`/bin/ls`、`/usr/bin/grep`；新机器若无 rtk 可忽略。
- Windows 机器：检出后先把 `core.autocrlf` 关掉并重建工作区（否则 JSON 哈希断言、bash 守卫与工具脚本全部变红）；REST 契约测试的 `tool/validate_openapi` 在 Windows 经 bash 转发，`dart test` 需要 `PYTHON`（learn_system venv，含 jsonschema）与 `OPENAPI_VALIDATOR`（learn_system `.venv-openapi/Scripts/openapi-spec-validator.exe`）两个环境变量，守卫已内置注入。
- xuan-handbook 中 reading-notes 尚无模块领域；已登记 `social.community-interactions`（状态 `landed`，claim 已删除，接入手册待补）。回填其余已交付的注解社区能力前，先请用户决定领域。

## 9. 接手提示词

---

你将在这台机器上接手「注解社区」（NC 系列任务）的后续开发，担任主 Agent：负责规格、派发、裁定与独立验收，遇到需要用户决定的事项停下来问用户。请严格按以下步骤开始，不要跳步。

**第 1 步：准备路径与环境。** 所有规格、守卫与 act 文件使用绝对路径 `/Users/jingtaiwei/Git/Public/...` 和 `/Users/jingtaiwei/flutter/bin`。若本机用户名或目录不同，先建立同名目录或软链接，使这些路径可用；确认 Flutter 3.44.6、Python 3.14、Node/npm 可用，且能访问 `192.168.0.165:3000`（Gitea）、`192.168.0.165:8080`（Firestore Emulator）、`192.168.0.165:9099`（Auth Emulator）。任一条件不满足，停下来告诉用户缺什么。

**第 2 步：拉取仓库。** `/Users/jingtaiwei/Git/Public/xuan-migration` 只是容器目录，不要在其中 `git init`。从 `http://192.168.0.165:3000/xuan/` 克隆：
- `learn_system.git` → `/Users/jingtaiwei/Git/Public/learn_system`，检出分支 `codex/docs/knowledge-compilation`
- `reading-notes.git` → `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（`main`）
- `functions-py.git` → `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（`master`）
- `repository_rest_adapter.git` → `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`（`main`）
- `xuan-server.git` → `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server`（`main`）
- `xuan-storage.git` → `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage`（`main`），再执行 `git worktree add .worktrees/nc016-guard-aad fix/nc016-guard-aad`（远端分支同名）
- `social.git`、`notification.git`、`xuan-handbook.git` → `/Users/jingtaiwei/Git/Public/xuan-migration/` 下同名目录（`main`）
已存在的仓库改为 `git pull`（分叉时合并，不变基，禁止 force push）。

**第 3 步：读交接文档。** 完整阅读 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/HANDOFF_ANNOTATION_COMMUNITY.md`，然后读：`openspec/subagent-delivery-gate.md`；`docs/blackbox-spec-rework/SUBAGENT_TODO.md` 中所有 NC 行；`openspec/annotation-community/` 下 `TASKS.md`、`DESIGN.md`、`PRD.md`、`INTEGRATION_BASELINE.md`；`contracts/` 目录清单；`work-items/nc-011/` 与 `work-items/nc-012a/` 两套六件套（作为范式）；`reviews/nc012a_guard.sh`。

**第 4 步：遵守能力台账。** 执行 `git -C /Users/jingtaiwei/Git/Public/xuan-migration/xuan-handbook pull --rebase`，读 `README.md` 与 `PROTOCOL.md`，每个任务开工前按 §1 查台账、按 §2 登记在建（claim 推送成功前不得改代码），交付时按 §4 回写。发现别人已登记同一能力，停手告诉用户。

**第 5 步：复现基线。** 按交接文档 §3 安装依赖，按 §4 运行基线命令并逐条对照期望；任何一条对不上，停手把原始输出报告用户，不要修复。

**第 6 步：收尾 NC-012a 遗留。** NC-012a 已验收。按交接文档 §5：按 handbook PROTOCOL §9 铁律为 `social.community-interactions` 编写接入手册 `integration/social.community-interactions.md`（签名、调用链、示例全部摘自 Gitea 主干真实代码并标 `仓/文件:起-止`），更新条目证据后按 §5 判定 `landed`/`done`，提交推送 handbook。

**第 7 步：继续后续任务。** 按交接文档 §6 的顺序（先 NC-013），按 §7 的工作方法推进：写契约与六件套和守卫 → 异厂商四查 READY → 派发执行者（同时不超过 2～3 个）→ 停手裁定 → 独立验收 → 更新 TODO、提交、推送 Gitea → handbook 回写。每完成一个任务，用一句话告诉用户结果与下一步。

**始终遵守**：交接文档 §8 全部约束（中文为主、只暂存本线文件、不删除数据、执行者不推送、S6 无恢复材料、ENOSPC 告诉用户等）；执行方自述不可信，一律用 git 与原始输出核对；需要用户决定的事项（领域新增、Firebase 去留、NC-018 解锁、合并 xuan-storage 分支）停下来问用户。
