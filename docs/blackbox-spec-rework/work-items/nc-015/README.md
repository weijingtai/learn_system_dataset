# NC-015：接入 S6——设备授权、传输一次一密与中转删除协议（v1.6 接入型）

状态：`ACCEPTED`（2026-09-11，验收 R1：learn_system `2d3a366`、`b39d4f6`；samples=18、unittest 16 OK、守卫 0、盲测全 PASS；契约 §5 第 95 行 TTL 文案冲突已由主 Agent 修正；记录见 [ACCEPTANCE](ACCEPTANCE.md)）。历次状态：`READY`（2026-09-11：R1 四查 + 十二场景审查返工 5 项、R2 返工 1 项，均已落实；记录见 `reviews/NC-015-REVIEW-R1.md`）。派发前置：无（规格仓内产物；不依赖 Firebase 去留）。执行由用户交外部 Agent，PROMPT.md 原样发送。task_id：`NC-015`。权威需求来源：TASKS v1.6 NC-015；PRD v1.6 R-12/R-13/R-14、§8 E-CRYPTO；DESIGN v1.6 §5；xuan-storage S6 设计稿裁决；契约 `openspec/annotation-community/contracts/private_sync.md`（本任务专属，主 Agent 编写）。

## 用户指示（2026-09-11，两次强调）

私人数据保护走 xuan-storage S6 已生效方案（「绕过保存密钥」：同步时才加密、同步完即删、中转不超过数分钟、无长期密钥），**接入现成能力，不重写**。主 Agent 已盘点：可复用设备身份/配对/传输/AES-GCM/会话 guard；需补 X25519/HKDF 一次一密、会话公钥签名绑定、guard 过期与设备 ID/指纹比较、AAD；无恢复材料。R1 审查后：密文一律走 Storage，notifier 只做信令（D-NC015-01 修订）。

## Goal

在规格仓内交付：契约 §7 的 18 个正反样例（每项含 `expected`）与检查器 `tools/check_private_sync_protocol.py`（红条件按契约 §8）及其 unittest。执行者不做设计：字段、闭集、判定顺序全部来自契约。实现（guard 补丁、一次一密包装、中转配置、验收流水）归 NC-016。

## Scope

- 允许写：仅 `openspec/annotation-community/fixtures/private_sync/*.json`（18 个，文件名逐字按契约 §7）、`openspec/annotation-community/tools/check_private_sync_protocol.py`、`openspec/annotation-community/tools/test_check_private_sync_protocol.py`。
- 只读：契约 `private_sync.md`、`fixtures/community/content_hash_cases.json`（取第一个 case 的 `expected_hash`）、`tools/validate_fixtures.py`（风格参考）；xuan-storage、reading-notes、xuan-server 全部只读。
- 禁止：改契约；改任何其他文件；新增 Python 依赖（只用标准库 + 本仓 `.venv` 已有 jsonschema）；用 `pytest`（本机无，用 unittest）；签名/密文用真实密码学库生成（D-NC015-07：格式级）；`skip`、永真断言；先实现后补测试。

## Inputs

契约 `private_sync.md` §2（身份）、§3（授权记录字段与判定顺序）、§4.4（信封字段）、§6（验收原因码）、§7（样例表）、§8（检查器红条件与 `expected` 闭集）、§9（决定）。

## Dependencies / Baseline

- 规格仓守卫基线：`bash openspec/annotation-community/review_v1_6_guard.sh` 0；`bash openspec/annotation-community/verify.sh` 0。
- Python：`/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python`（3.14，jsonschema 4.26.0）。
- 共享守卫：`bash docs/blackbox-spec-rework/reviews/nc015_guard.sh --require-impl`（只读）；K01 失败判外部失败，K02 及以后按本任务失败停工。

## Stop Conditions

契约有两种以上解释；`content_hash_cases.json` 第一个 case 无 `expected_hash` 字段；检查器需要读取契约以外的文档才能判定；需要写白名单外文件。遇到即停，原样报告。

## 执行顺序

`act/01`（18 个样例）→ `act/02`（检查器 + unittest）。每步一个提交在 learn_system 仓库（只 `git add` 本步文件）。

## 一次性交付与阅读顺序

1. 本 README；2. `contracts/private_sync.md`；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～02；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)。
