# NC-003：公共 REST/OpenAPI 契约、错误目录与幂等命令面

状态：`REWORK_ACT06`（2026-09-11 主 Agent 验收：act/01～05 形式门禁与五项盲测通过，发现可空字段 3.0 写法、遗留错误体被改、字节上限不可表达三处缺陷，追加 act/06 并合入 NC-009 前置补丁 P1/P2；记录见 ACCEPTANCE.md R1）。原状态 `READY`（R1 返工 6 项、R2 返工 1 根因；`reviews/NC-003-REVIEW-R1.md`）。派发前置：无（NC-002 已 ACCEPTED；契约不依赖 Firebase 去留决定——身份策略见 D-NC003-02）。执行由用户交外部 Agent，PROMPT.md 原样发送。task_id：`NC-003`。权威需求来源：TASKS NC-003；DESIGN §2.1.1、§4、§7.3、§7.4；PRD R-05/R-18/R-20；契约 `openspec/annotation-community/contracts/community_api.md`（本任务专属，主 Agent 编写，含 SERVER functions-py 现状盘点结论）。

## 用户指示（2026-09-11）

按 Firebase 方向写，与 `xuan-server/functions-py` 现有 Functions 约定统一。主 Agent 已盘点 functions-py（HTTP `on_request` REST、Bearer ID token、RFC 9457、`Idempotency-Key`、不透明游标、MD5 ETag、限流默认关闭、软删字段不一致），沿用方式逐条写在契约 §1.2。

## Goal

在 REST 仓库 `repository-rest-adapter` 内：① 把既有 `openapi/openapi.yaml` 全部 22 个 operation 的非法 operation 级 `headers:` 迁移为 `in: header` 参数，并迁移既有测试的 14 行断言（10 个测试块）；② 追加注解社区 20 个端点（14 写命令 + 6 读）、Schema、错误目录、命令账本结果与限流实值；③ 接入真实 OpenAPI 3.1 验证器与 JSON Schema 示例校验工具；④ 新增社区契约测试。执行者不做设计：路径、方法、头、字段、错误码、枚举全部来自契约。

## Scope

- 允许写：仅 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/` 内：`openapi/openapi.yaml`（原地修改）、`test/openapi_validation_test.dart`（仅 14 行断言所在的 10 个测试块与一个辅助函数）、新建 `test/community_openapi_contract_test.dart`、`tool/validate_openapi`、`tool/check_examples.py`、`test/fixtures/openapi/**`。
- 只读：REST 仓库 `lib/`、`pubspec.yaml`、`pubspec.lock`、其他测试；learn_system 全部；`xuan-server/notifier/api/openapi.yaml`；functions-py。
- 禁止：写入 learn_system；改 `lib/`、`pubspec.*`；新增 Dart 依赖（`yaml` 已是 dev 依赖）；再写 yaml 字段检查器代替真实验证器；改 playground 既有字段名或语义（只改头的表达形式）；`skip`、永真断言；先实现后补测试。

## Inputs

契约 `community_api.md` §1（位置、Firebase 方向沿用表）、§2（端点目录）、§3（头、ETag）、§4（错误目录与映射）、§5（Schema 字段表）、§6（分页与限流实值）、§7（命令账本）、§8（产物与判据）、§9（决定）。

## Dependencies / Baseline

- REST 仓库改前基线（主 Agent 2026-09-11 实测）：HEAD `0f8bf52`，`dart test` 退出 0、`+50`（19 + 14 + 17）；`openapi-spec-validator openapi/openapi.yaml` **失败**（`'headers' was unexpected`）。
- 验证器：`/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/.venv-openapi/bin/openapi-spec-validator`（0.9.0，已安装）；JSON Schema：`/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python`（含 `jsonschema 4.26.0`）。两者只读调用。
- 共享守卫：唯一 learn_system 侧命令 `bash docs/blackbox-spec-rework/reviews/nc003_guard.sh --require-impl`（只读）；K01 失败判外部失败，K02 及以后按本任务失败停工。

## Stop Conditions

契约有两种以上解释；验证器不在上述路径或运行报错（非验证失败）；迁移 22 个 operation 的 headers 后验证器仍报非 `headers` 类错误且无法按契约 §3.1 解决；`pubspec` 需要改动；既有 7 个非迁移测试变红；需要写白名单外文件。遇到即停，原样报告。

## 执行顺序

`act/01`（验证器工具 + 红文档 + 22 处迁移 + 14 行断言迁移）→ `act/02`（社区参数/Schema/错误组件/CommandResult）→ `act/03`（内容端点 W1～W6、R1、R6）→ `act/04`（评论/互动/分享/举报/命令端点）→ `act/05`（示例校验工具与 fixture、版本号、全量）。每步一个提交在 REST 仓库。

## 一次性交付与阅读顺序

1. 本 README；2. `contracts/community_api.md`；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～05；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)。
