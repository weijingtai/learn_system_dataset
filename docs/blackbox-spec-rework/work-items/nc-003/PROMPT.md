# NC-003 执行提示

发送前提：wjt-react 四查判定 READY；主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-003：在 REST 仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`（独立 Git 仓库；`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 与 functions-py 只读）内修正并扩展 `openapi/openapi.yaml`：把 22 个 operation 的非法 operation 级 `headers:` 迁移为 `in: header` 参数，追加注解社区 20 个端点与错误目录，接入真实 OpenAPI 3.1 验证器和 JSON Schema 示例校验，并写契约测试。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-003/` 下的 README.md、BDD.md、TDD.md、ACT.yaml、act/01～05.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/community_api.md`（全文，逐字照抄其端点、头、字段、错误码、枚举）、`community-models.md` §0.1/§2/§5；REST 仓库既有 `openapi/openapi.yaml` 与 `test/openapi_validation_test.dart`。

**验证器与 Python**（只读调用，不安装、不升级）：`tool/validate_openapi` 内部调用 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/.venv-openapi/bin/openapi-spec-validator`（可用 `$OPENAPI_VALIDATOR` 覆盖）；`tool/check_examples.py` 用 `/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python`（含 jsonschema）运行。任何一个不可用：停止并报告，不要自己写字段检查器代替。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告，act/01 须含改前文档的验证器失败原文），再实现。先实现后补测试即违反流程，须如实写明。

**只允许写**：各 ACT 的 WRITE_NEW 清单（`openapi/openapi.yaml` 原地修改；`test/openapi_validation_test.dart` 仅 14 行断言所在的 10 个测试块与辅助函数；新建 `test/community_openapi_contract_test.dart`、`tool/validate_openapi`、`tool/check_examples.py`、`test/fixtures/openapi/**`）。禁止：`lib/`、`pubspec.yaml`、`pubspec.lock`、其他测试；新增依赖；改 playground 字段语义；写 backup.* 路径；`skip`、永真断言。

**判据来源**：只来自 `community_api.md` 与 TDD。契约有两种以上解释、验证器运行报错、迁移后出现契约未覆盖的验证错误、既有 7 个非迁移测试变红、需要改 `pubspec`：立即停止并原样报告，不自行裁定。

**提交**：五步各一个提交，在 REST 仓库内，只 `git add` 本步文件，不 push。提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败原文；
3. Green：该 ACT VERIFICATION 每条命令的退出码与输出末 20 行；
4. act/01 另附迁移前后 operation 级 `headers` 键计数（按 `paths.*.<method>` 解析，应 22 → 0）；act/05 另附 `dart test` 全量末 5 行（应 `+65: All tests passed!`）、`check_examples.py` 翻转一项后的退出码与原文、`nc003_guard.sh --require-impl` 退出码；
5. 跳过项、未运行项与剩余风险。

不要把本任务说成 NC-003 之外的任何任务完成：服务端实现、ACL 真实 HTTP 测试、限流开启、备份端点、通知补拉都在后续任务。


# NC-003 act/06 返工执行提示（2026-09-11 验收后追加）

发送前提：act/01～05 已在 REST 仓提交（`67910c3`…`89cc68d`）。把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-003 的返工步 act/06：在 REST 仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`（独立 Git 仓库；`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 只读）以 `89cc68d` 为基线修三处缺陷并加两个小补丁。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读**：`docs/blackbox-spec-rework/work-items/nc-003/act/06.yaml`、`TDD.md` §5c、`BDD.md` B28～B32、`ACCEPTANCE.md` 末尾「验收记录 R1」；契约 `openspec/annotation-community/contracts/community_api.md` §10 全文（逐字照做）。

**要改的五件事**：① 社区 Schema 的可空字段从 `nullable: true` 改为 `type: [<类型>, "null"]`（带 enum 的把 `null` 加进 enum），社区 Schema 内不得再有 `nullable` 键；`tool/check_examples.py` 删除一切对 `nullable` 的改写，按文档原样校验。② `ProblemDetails` 与 8 个遗留响应组件（400BadRequest、401Unauthorized、403Forbidden、404NotFound、409Conflict、500Internal、503Unavailable、504DeadlineExceeded）恢复为与 `0f8bf52` 逐项相等；新增 `CommunityProblemDetails`（required 为 type/title/status/code），全部社区 `Problem*` 改为 allOf 它，社区端点只引用社区响应组件。③ `PublicSnapshot.markdown` 加 `x-max-utf8-bytes: 262144` 与描述。④ 新增参数组件 `IfMatchOptional`（required false）并挂到 `POST /v1/community/contents`。⑤ 新增响应组件 `500StateCorrupted`（code const `internal.state_corrupted`，type const `internal`），R1 的 500 引用它。

**先写测试再改实现**：先加 4 个新测试（名称逐字取 TDD §5c）、改 2 个既有测试的断言对象（测试名不变）、加 2 个 null 示例并入 manifest，对 `89cc68d` 取得 Red 原文，再改 yaml 与工具。

**只允许写**：`openapi/openapi.yaml`、`tool/check_examples.py`、`test/fixtures/openapi/examples/`（两个新文件 + manifest）、`test/community_openapi_contract_test.dart`。禁止：`lib/`、`pubspec.*`、`test/openapi_validation_test.dart` 及其他测试；遗留 Schema 的 `nullable`；新增依赖；`skip`、永真断言。

**判据**：契约 §10 与 TDD §5c。遗留组件恢复原样后既有 19 个 `openapi_validation_test` 变红、或验证器报出本任务未引入的错误：立即停止并原样报告。

**提交**：一个提交，只 `git add` 上述文件，不 push；提交消息按 act/06 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：commit 哈希与 `git show --stat`；Red 命令/退出码/原文；VERIFICATION 每条命令的退出码与末 20 行（`dart test` 应 `+69: All tests passed!`，`check_examples.py` 10 项全过）；`nc003_guard.sh --require-impl` 退出码；另请把 act/01～05 的交付报告原文一并附上（此前未收到）。
