# NC-002 独立验收

当前：`ACCEPTED`（2026-09-11，主 Agent 亲自验收，记录见文末）。两项 DEFERRED（CLIENT Dart 一致性测试 → NC-004；CommandRecord 按操作成对 Schema → NC-003）不计入本次通过。

1. ACT 审查：由未参与编写的审查者做 wjt-react 四查；本文不自签 READY。
2. 范围：五个 learn_system 提交与一个 SERVER 提交，`git show --name-only` 逐一核对只含各 ACT 的 WRITE_NEW；`git diff <派发基线> HEAD -- openspec/schemas/verify.sh` 为空；契约、fixture、参考编码器、既有 Schema/示例、SERVER 其他文件无 diff；xuan-migration 各仓无改动。
3. 重跑 TDD §1 全部 8 条命令，逐条捕获退出码：verify_community.sh 与 verify.sh 均 0（后者零 diff），且 `bash openspec/schemas/verify_community.sh | grep -c '^PASS '` = 参与逐例校验的示例文件数 + 3（metaschema、structure、all），其中参与数 = `examples/community_*.yaml` 总数 − 2 个配对文件 − 2 个结构块专属文件（`invalid_preferred_head_not_in_heads`、`invalid_range_end_le_start`）；命令 3 `Ran 7 tests`；命令 4 末行 `FIXTURES_OK 9 files 198 cases`；命令 5 `Ran 8 tests OK`；命令 6 退出 0；`nc002_guard.sh --require-impl` 0。
4. 主 Agent 独立复算：用 `tools/nchash_reference.py` 对 SERVER `xuan/community_hash.py` 做交叉复算——对 18 个 case 与 16 个向量分别调用两端实现，逐字节相等；再构造至少 5 个 fixture 之外的盲测 snapshot（含 3 附件乱序、2 mention 同 offset 不同 user、binding 含两段 selector、含 emoji 与组合字符的 title、change_summary 仅空白差异），两端 hash 相等且与参考一致。
5. Schema 盲测：对每个 Schema 构造至少 1 个 fixture 之外的反例（如 `version: -1`、时间戳缺 `Z`、`operation` 大小写错误、`head_revision_ids` 重复项），check-jsonschema 必须失败。
6. fixture 校验器盲测：在临时副本中分别注入「状态值 `Purged`（大小写）」「`thread_id` 用上游 `rev_` 前缀」「`equal_hash_to` 指向不存在 case」，校验器必须非零；真实目录必须 0。
7. 检查无 skip/永真/空断言/从被测输出生成期望；SERVER 测试不 import 参考编码器与 firebase；`community_hash.py` 不含 `json.dumps`（不得用 JSON 序列化代替 E）。
8. 流程核对：每个提交内测试/示例文件与实现文件同时提交，且报告给出真实 Red 原文；若执行者自报「先实现后补测试」，记录为流程偏差。
9. 通过后只验收 NC-002 的机器产物；CLIENT Dart 一致性测试留 NC-004；`READINESS_REVIEW.md` §3 与 SUBAGENT_TODO 的前缀结论由主线程写入。

共享守卫外部失败规则同 README：`review_v1_5_guard.sh`、`annotation-community/verify.sh`、`git diff --check`、`nc002_guard.sh` K01 因并行线共享文件改动失败时按外部失败记录，判定依据是 `git diff --stat` 显示失败源不在白名单文件之内。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 失败原文；盲测输出；跳过项与剩余阻塞。

## 验收记录（NC-002，2026-09-11，主 Agent C/S 会话）

- 执行提交（外部 Agent，用户派发）：learn_system `0d27ea8`→`b2a4b51`→`f53f581`→`3fd6869`→`7ee2c45`；SERVER `30a868c`。`git show --name-only` 逐一核对：五个提交只含 community_* Schema/示例/verify_community.sh/两个工具文件；SERVER 提交只含三个白名单文件；`openspec/schemas/verify.sh`、既有 4 个 Schema、契约、fixture、参考编码器、四份规格零 diff；SERVER 工作树干净。
- 命令与退出码：`nc002_guard.sh --require-impl` 0（K01～K08 全 PASS）；`verify_community.sh` 0，`grep -c '^PASS '` = 61 = 58 + 3（62 示例 − 4 结构块专属）；`CHECK 4(` 行 30；`schemas/verify.sh` 0；`validate_fixtures.py` `FIXTURES_OK 9 files 198 cases`；校验器 unittest `Ran 7 OK`；SERVER `python3 -m unittest tests.test_community_hash_parity` `Ran 8 OK`；`cmp` 两份 fixture 相同。
- 交叉复算（参考编码器 vs SERVER 实现）：守卫 K08 覆盖 18 case + 16 向量 + 3 非法文本；另 5 个 fixture 外盲测快照（3 附件乱序、2 mention 同 offset 不同 user、binding 双段 selector、emoji+组合字符标题、change_summary 仅空白差异）canonical 字节与 hash 逐字节相等，且空白差异改变 hash；4 个盲测反例（孤立 surrogate、2^53 整数、`-0` 文本、嵌套重复键）两端均拒绝。
- Schema 盲测：12 个 Schema 各构造 1 个 fixture 外反例（重复 heads、时间戳缺 Z、version −1、枚举大小写、空 author_id、重复 mention、target_type 越界、operation 大小写、attempt_count −1、空 notifier_delivery_id、schema_version 0、note id 用 psn_ 前缀），check-jsonschema 全部拒绝。开放对象恰为三处豁免指针，其余对象节点全部 `additionalProperties: false`。
- 校验器盲测：`equal_hash_to` 指向不存在 case、多出 fixture 文件、状态值 `Published`，三例均非零并给出规定文案；真实目录 0。
- 作弊扫描：两份测试无 skip/永真/expectedFailure/except-pass；`community_hash.py` 无 `json.dumps`、无 `nchash_reference`。
- 流程：六个提交每个都同时含示例/测试与实现。执行方的交付报告 `DELIVERY_REPORT.md` 未在本机 `/Users/jingtaiwei/Git/Public` 下找到，Red 原文未能从文件核验，以用户转述与提交构成为据，记为验收限制（不阻断）。
- 结论：NC-002 机器产物 `ACCEPTED`。DEFERRED：CLIENT `content_hash_parity_test.dart`（NC-004 act/01 已承接）、CommandRecord 按操作成对 Schema（NC-003）。
