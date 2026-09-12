# NC-003 独立验收

当前：NOT_EXECUTED。派发前置：NC-002 ACCEPTED；验证器已安装。

1. ACT 审查：未参与编写者做 wjt-react 四查；本文不自签 READY。
2. 范围：REST 仓库新增恰 5 个提交（在 `0f8bf52` 之后），`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；`git diff 0f8bf52 HEAD --stat -- lib pubspec.yaml pubspec.lock` 为空；`test/openapi_validation_test.dart` 的 diff 只涉及 14 行断言所在的 10 个测试块与辅助函数（`test(` 计数仍 19；第 50 行 `components['headers']` 未改）。
3. 重跑 TDD §1 全部命令并记录退出码：验证器对 `openapi/openapi.yaml` 0、对两个红文档非 0；`dart test +65`；`check_examples.py` 0；`nc003_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时文件，不入库）：① 用 PyYAML 按 `paths.*.<method>` 解析，独立复算：operation 级 `headers` 计数 0（改前为 22/22）、社区路径恰 20、每个写操作 `IdempotencyKey` 必填、`If-Match` 集合恰为 W2～W6/W8～W11；② 对 `PublishRequest` 构造 `markdown` 恰 262144 字节与 262145 字节的示例，用 jsonschema 校验（注意 `maxLength` 按 code point，字节上限如用 `maxLength` 表达须说明取值），结果与契约一致或记录偏差；③ 把 `CommandResult.operation` 枚举与 DESIGN §2.1.1 列表逐字 diff；④ 检查 22 个既有 operation 的 `parameters` 中头参数名集合与迁移前该 operation 的 `headers` 键集合逐一相等（22 对 22）；⑤ 随机抽 3 个错误响应，确认 `code` 值在契约 §4.1 目录内且 `type` 按 §4.2 映射。
5. 作弊扫描：测试无 `skip`、`expect(true`；`tool/validate_openapi` 确实调用 `openapi-spec-validator`（脚本内含该字符串且无自写校验逻辑）；`check_examples.py` 使用 `jsonschema` 库。
6. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文（含改前文档的验证器失败原文）。
7. 通过后只验收 NC-003；服务端实现归 NC-009 起。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。


---

## 验收记录 R1（主 Agent，2026-09-11）：act/01～05 REWORK，追加 act/06

- 提交：REST 仓 `67910c3`（A）、`943c608`（B）、`fffbeb9`（C）、`1520688`（D）、`89cc68d`（E），恰 5 个；各提交只含对应 WRITE_NEW；`lib/`、`pubspec.*`、`rest_contract_suite_test.dart`、`wire_test.dart` diff 为空；`openapi_validation_test.dart` 仍 19 个 `test(`。提交 B 的消息沿用拆分前措辞「社区组件、错误目录与内容端点」，属主 Agent act/02.yaml 遗留文字，实际未加任何路径，不计执行方问题。
- 守卫 `nc003_guard.sh --require-impl` K01～K05 全 PASS（验证器 0、红文档非 0、`dart test ≥65`）。
- 交付报告：REST 仓与 learn_system 均无报告文件，Red 原文无法核对（待用户转交执行方报告后补记）。
- 盲测（PyYAML + jsonschema 原样，临时脚本不入库）：① operation 级 `headers` 22 → 0，社区操作恰 20；② 必填 `Idempotency-Key` 的写操作集合恰为 W1～W14，`If-Match` 集合恰为 W2～W6/W8～W11；③ `CommandResult.operation` 与 DESIGN §2.1.1 逐字相等（17）；④ 22 个遗留 operation 迁移前后头集合逐一相等（22/22）；⑤ 错误响应组件抽样引用正确。
- **缺陷 1**：社区 Schema 18 处用 `nullable: true`（3.0 关键字）；原样 3.1 校验下 `ContentAccessPublic.current_publication_id = null` 与 `ReactionState.value = null` 均被拒收；`check_examples.py` 的 `handle_nullable` 在校验前改写文档，掩盖了该缺陷。
- **缺陷 2**：共享 `ProblemDetails` 的 `required` 由 `[type,title,status,detail]` 改为 `[type,title,status,code]`，遗留 playground/record 端点契约随之要求 `code` 而服务端 `make_problem_details` 不产出——根因是主 Agent 契约 §4.1 把社区要求写在共享 Schema 上。
- **缺陷 3**：`PublicSnapshot.markdown` 的 256 KiB 字节上限以 `maxLength` 表达（按 code point 计），多字节文本可超字节上限而通过 Schema。
- 另：`ProblemDetails.type` enum 保留遗留 10 值而非契约写的 6 值——契约要求与共享 Schema 冲突，执行方选择保留正确，契约 §10.2 已改。
- 处理：契约新增 §10（D-NC003-13～15）并把 NC-009 前置补丁 P1/P2 合入 `act/06.yaml`（全量 +69）。判定 **REWORK**；act/06 通过后复跑本记录盲测与 null 原样校验、遗留组件与基线逐项比较，再关闭 NC-003。
