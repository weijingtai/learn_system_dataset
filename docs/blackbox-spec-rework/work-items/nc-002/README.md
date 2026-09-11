# NC-002：非书籍模型、ID 前缀、状态机、限额、canonical 编码与 fixture

状态：`PREPARING`（六件套已产出，待 wjt-react 四查）。task_id：`NC-002`。权威需求来源：`openspec/annotation-community/TASKS.md` NC-002 条目；DESIGN §2、§2.1、§2.1.1、§2.2、§3、§4、§6、§7、§11。分支：`codex/docs/knowledge-compilation`。

## 规格侧已交付（主 Agent 编写，执行者只读）

| 产物 | 路径 | 内容 |
|---|---|---|
| 模型契约 | `openspec/annotation-community/contracts/community-models.md` | 字段级模型、ID 前缀冻结表、限额常量、决定 D-NC002-01～06 |
| 状态机契约 | `openspec/annotation-community/contracts/state-machines.md` | 九台状态机完整转移表、枚举总表、组合白名单、D-NC002-07～09 |
| 参考编码器 | `openspec/annotation-community/tools/nchash_reference.py` | nchash/v2 规格侧预言机 |
| fixture | `openspec/annotation-community/fixtures/community/*.json`（9 个，共 198 项） | content_hash 18 例 + 16 向量 + 7 非法对象 + 3 非法 JSON 文本；ID 格式 33；command_id 10；限额 16；mention 13；状态组合 24；转移 35；评论回复 12；修订 11 |

ID 前缀：DESIGN §2.1 十七项由用户托管主 Agent于 2026-09-10 整表采用（见 SUBAGENT_TODO G6 节与 `READINESS_REVIEW.md` §3 增补）。

## Goal

把上述契约落为机器可执行物：JSON Schema（含成对正反例与校验脚本）、fixture 校验器、SERVER 侧 nchash/v2 实现与跨端一致性测试。执行者不做任何设计：字段、枚举、正则、期望值全部来自契约与 fixture。

## Scope

- 允许写（learn_system）：`openspec/schemas/community_*.schema.json`（新建）、`openspec/schemas/examples/community_*.yaml`（新建）、`openspec/schemas/verify_community.sh`（新建）、**不修改** `openspec/schemas/verify.sh`（决定 D-NC002-11：它是 D-02 已验收的 L0 唯一验证命令，且 `set -e` 会把社区 fixture 的红误报成黑箱线阻断；社区校验由 `verify_community.sh` 独立承担，主 Agent 守卫依次运行两者）、`openspec/annotation-community/tools/validate_fixtures.py`（新建）、`openspec/annotation-community/tools/test_validate_fixtures.py`（新建）。
- 允许写（SERVER `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`）：`xuan/community_hash.py`（新建）、`tests/test_community_hash_parity.py`（新建）、`tests/fixtures/community_content_hash_cases.json`（新建，字节等同于 SPEC 的 `content_hash_cases.json`）。
- 只读：两份契约、9 个 fixture、参考编码器、DESIGN/PRD/TASKS、既有 `openspec/schemas/*`、SERVER 既有代码。
- 禁止：修改契约、fixture、参考编码器、本工作包、其他工作包、四份规格、既有守卫、PLAN/HANDOFF/SUBAGENT_TODO；修改 `openspec/schemas/verify.sh` 的任何内容；写入 xuan-migration 任何仓库；安装依赖（含 pytest；`.venv` 内既有 jsonschema 4.26.0 与 PyYAML 6.0.3 只在 `verify_community.sh` 结构块使用）；在 SERVER 运行需要 Emulator 的测试。

## Forbidden（补充）

1. 从 fixture 或参考编码器反推期望后再写回 fixture；期望只读。
2. 用参考编码器充当 SERVER 实现（`xuan/community_hash.py` 必须独立编写，不 import 参考编码器，不复制其文件）。
3. 用 `sort` 递归排序全部数组、用 JSON 序列化代替 E 编码、用浮点。
4. Schema 放开 `additionalProperties`、用 `pattern` 以外的方式「宽松匹配」ID。
5. 跳过、永真断言、`expectedFailure`、捕获异常放行。

## Inputs

- `contracts/community-models.md` §0～§5：全部字段、类型、枚举、正则、限额。
- `contracts/state-machines.md` 枚举总表：`validate_fixtures.py` 的唯一状态值来源（解析该表，不硬编码）。
- `fixtures/community/*.json`：每条 case 均有 `expected`。
- 参考编码器只供主 Agent 验收复算；执行者可读其注释理解 §7.2，但实现须独立。

## Dependencies / Baseline

- NC-001-01 已 ACCEPTED；CLIENT 尚不存在（`reading-notes` 由 NC-004 建立），因此 **CLIENT 的 `content_hash_parity_test.dart` 推迟到 NC-004**，在其工作包中作为第一条 ACT；本任务不创建 CLIENT 目录。**CommandRecord 按 operation 的完整/精简成对 Schema 推迟到 NC-003**（与 OpenAPI 响应体同源），本任务只冻结通用 Schema 与 rejected/compacted 终态约束；两项均登记于 ACT.yaml `DEFERRED`。
- 本机无可用 pytest（系统 Python 无 pytest；homebrew pytest 解释器失效；SERVER 无 venv）。SERVER 测试用 `unittest.TestCase` 编写（pytest 日后照样收集），运行方式 `cd <SERVER> && python3 -m unittest tests.test_community_hash_parity -v`。SERVER 既有 `tests/conftest.py` 只在 pytest 下生效，unittest 不加载，故本测试不得依赖它。
- SERVER 基线：HEAD `866ea13`，工作树干净；`xuan/hashing.py` 是 JS-JSON 兼容哈希，与 nchash/v2 无关，不改动。
- learn_system 基线（HEAD 见派发时 SUBAGENT_TODO）：`bash openspec/schemas/verify.sh`=0（`.venv/bin/check-jsonschema` 可用）、`LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`=0、`bash openspec/annotation-community/verify.sh`=0、`git diff --check`=0、`bash docs/blackbox-spec-rework/reviews/nc002_guard.sh`=0（K08 SKIP）。
- 共享守卫外部失败规则：`review_v1_5_guard.sh`、`openspec/annotation-community/verify.sh`、`git diff --check`、`nc002_guard.sh` 的 K01 读取共享工作树，并行 G3/G4 线可能让它们失败；失败时先 `git diff --stat`，失败来源不在本任务白名单文件之内的判为外部失败，只记录、不返工、不停工。`nc002_guard.sh` 的 K02～K08 失败仍按本任务失败停工。反向提示：并行黑箱线把 `openspec/schemas/verify.sh` 当基线门禁，本任务全程不触碰它；所有步骤只运行 `verify_community.sh` 自身。

## Stop Conditions

契约存在两种以上解释；fixture 的 `expected` 与契约矛盾；需要写白名单之外的文件；需要改动 `openspec/schemas/verify.sh`；check-jsonschema 不可用；SERVER 测试需要网络/Emulator/依赖。遇到即停，报告原文，不自行裁定。

## 执行顺序

`act/01`（公共 $defs、Note、verify_community.sh 前三步）→ `act/02`（NoteRevision、配对示例、结构块）→ `act/03`（公共域五个 Schema）→ `act/04`（命令/通知/事件四个 Schema）→ `act/05`（fixture 校验器）→ `act/06`（SERVER nchash/v2 与一致性测试，独立仓库单独提交）。前五步各一个 learn_system 提交，第六步一个 SERVER 提交。

## 一次性交付与阅读顺序

1. 本 README；2. 两份契约；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～06；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)（READY 后原样发送）。
