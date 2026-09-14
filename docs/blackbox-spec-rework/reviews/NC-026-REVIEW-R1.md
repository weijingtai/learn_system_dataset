# NC-026 四查记录 R1（行为事件数据源、假名化与私人笔记元数据上报）

评审日期：2026-09-13
评审对象：`openspec/annotation-community/contracts/community_behavior.md`、`community_api.md` §14、
`docs/blackbox-spec-rework/work-items/nc-026/`（六件套 11 文件）、`reviews/nc026_guard.sh`。

## 0. 独立性声明（重要，先读）

按 `HANDOFF_ANNOTATION_COMMUNITY.md` §7.2，审查者须「未参与编写」。**本记录不满足该条**：

- 本记录的署名作者即 NC-026 契约与六件套的**作者**（起草期作为规格作者会话完成，见 `SUBAGENT_TODO.md` NC-026 行与 `546b287`）。
- 用户随后明确授权同一会话**全权接任主 Agent**并对 NC-026 做**端到端实现**（含 act/01～act/05）。
- 因此不存在「未参与编写且异厂商」的第三方审查者。

处理方式（登记为 **D-NC026-28**）：本文件如实降级为**作者自查记录 + 冲突利益披露**，不等价于 §7.2 的独立四查；
其效力来源是**用户显式授权**，而非独立性。任何后续环节若需要真正的四查，须由另一会话补做。

为降低「自查无效」的风险，本记录采取两条补偿措施：
1. **机械取证优先**：每条结论都给出 `仓/文件:行`、命令与原文输出，不采信作者记忆。
2. **落地后复核**：act 实现完成后，以 `nc026_guard.sh --require-impl all`（K01～K09）与独立盲测探针复核，
   而不是复用起草期的结论。

## 1. 忠实性（契约与上游规范是否一致）

| 抽查点 | 上游原文 | 契约落点 | 判定 |
|---|---|---|---|
| 行为事件集合与前缀 | `DESIGN.md` §11（`bev_`）；`TASKS.md` NC-026 行 | §2 集合 `community_behavior_events`、前缀 `bev_` | 一致 |
| 假名前缀 | `DESIGN.md` §11.3（`psn_`，禁止由账号 ID 推导） | §9.2、D-NC026-17 | 一致（沿用既有 `ids.new_id("psn_")`＝`uuid4().hex`，`os.urandom` 播种） |
| 私人笔记元数据 | `DESIGN.md` §11.4（`char_count`/`revision_count`/`duration_ms`/`dropped_before`） | §5.1、§8.3 C01～C18 | 一致 |
| 只追加 | `DESIGN.md` §11.5；`TASKS.md`「禁止 update/delete」 | §4.4、§10.1、D-NC026-10 | 一致（`server/firestore.rules` 零改动 + 4 条显式用例） |
| 上报语义 | `DESIGN.md` §11.4「服务端按 event_id 去重」 | §5.1、D-NC026-12 | 一致且**未夸大**：契约只承诺 at-least-once + 服务端 create-if-absent，全文无 exactly-once 声称 |
| REST 串行链 | `PLANS.md` §1.2（`openapi.yaml` 串行写入） | D-NC026-23（NC-013 → NC-021 → NC-026） | 一致；NC-021 `BLOCKED`，取下一棒 |
| 注销子项 | `TASKS.md` NC-026 行「缺证时 BLOCKED、其余继续」；NC-001 第⑩项未登记 | §13、D-NC026-13 `DEFERRED` | 一致，且**未派发** |

上游引用的行号抽查（`D:/Programme/learn_system/openspec/annotation-community/`）：
`TASKS.md` NC-026 行、`DESIGN.md` §11 各小节、`PRD.md` 相关需求行、`PLANS.md` §1.2 均逐条命中，
未发现「引用存在但不支持结论」的情形。

**现有代码取证（起草期，不采信自述）**：
- `xuan-server/functions-py/xuan/community/command_service.py:177-197`：NC-009 命令账本事务内已写 `community_behavior_events` 与 `community_pseudonym_mappings`，但事件文档**只有 6 个字段**，缺 `received_at`/`object_type`/`object_id`/`note_ref`/`platform`/`app_version` → 契约 §3.1 的补字段要求成立。
- `xuan/community/content_service.py:288`：唯一非空 `attributes` 为 `{is_republish}` → §3.2 允许集需覆盖该形态，否则既有链路会写出允许集外键。
- 客户端（`reading-notes`）起草期**无任何上报链路** → §6 新增端口的必要性成立。

判定：**忠实性 PASS**。

## 2. 覆盖性（BDD/ACT/测试名是否覆盖契约全部可测断言）

- BDD 编号连续：A01～A04、S01～S26、C01～C18、R01～R03（K03 断言逐项命中）。
- 测试名逐字表：SERVER 26、REST 4、CLIENT 18 全部在契约内逐字出现，且与各仓测试文件实测一致（K02/K07/K08/K06）。
- 四线依赖链：REST(act/01) 无依赖 → RULES(act/05) 无依赖 → SERVER act/02 无依赖 → act/03 依赖 act/02 → CLIENT act/04 无依赖；`act/*.yaml` 的 `DEPENDS_ON` 与该链一致（K03 断言 `["[]","[]","[NC-026-B]","[]","[]"]`）。
- 错误行覆盖：`invalid_argument.events`、`invalid_argument.event_type`、`too_large.events`、401、413、503 均落到契约 §4.1 表格与 REST 契约测试（K06 断言 openapi 增量与 4 个测试名）。

判定：**覆盖性 PASS**。

## 3. 可执行性（参考值、Schema、命令是否可机械复现）

- 参考值**字面量写死**且经真实代码复算：3 组 `bev_`（`bev_7238cb94…`、`bev_35a1484f…`、`bev_0cf02e53…`）与 `note_ref`（`2be56a40…80673`）由契约 §9.3 给出，实现期在 functions-py 内以独立进程复算比对 **MATCH**（见 `scratchpad/nc026/` 执行报告）。
- 冻结 Schema SHA 字面量 `f3467224ddafa5ff3ac2a43011521a5cc0b8acf6293244d632fa291c97451e42`：
  - 规格侧实算一致（K05）；
  - SERVER 副本**逐字节相同**（`cmp` 通过；K07 断言 `schema_copy_identical`）。
- 23 个示例（2 正 21 负）由 `check-jsonschema.exe` 真校验判定（K05），非文本比对。
- Windows 适配沿用 D-NC012-23 风格：venv 走 `Scripts/python.exe`、flutter/dart/npm 经 `shutil.which`、`os.pathsep`、`file:///D:/` base-uri。
- 计数推导可复算：SERVER `568+26=594`；REST `81+4=85`；CLIENT `314+18=332`；RULES `153+4=157`（RULES 实测 `157 passed, 157 total`）。

判定：**可执行性 PASS**。

## 4. 独立性

**不满足**（见 §0）。D-NC026-28 登记：本记录为作者自查 + 用户授权的替代物；真正的 §7.2 四查须由另一会话补做。

## 5. 起草期发现的偏差与处置

| 编号 | 偏差 | 处置 |
|---|---|---|
| D-NC026-26 | NC-026 起草早于 NC-014 落地，CLIENT 基线由 `+296` 升至 `+314` | 契约/六件套/守卫同步：保护路径 diff 基准 `107ec90` → `19afe37`，期望计数 `+314` → `+332`（K08 阈值同步），否则 K08 的 `pubspec.yaml` 保护断言会被 NC-014 的**合法** pubspec 改动误判——与 `nc014_guard.sh` K06 同类修严 |
| D-NC026-24/25 | act/02 的 10 个测试需要 `pseudonyms.py`/`behavior_events.py` 两个纯层，而两文件原列在 act/03 | 纯层归属改列 act/02（act/03 只消费）；`act/02.yaml`/`act/03.yaml` 的 GOAL/WRITE_NEW/WORKLOAD 同步 |
| D-NC026-27 | 同一会话实现 act/02 与 act/03 | 合并单提交；范围证据取 `992088e..HEAD` 恰 10 文件（ACCEPTANCE §2 本就是区间口径，非按 act 切分提交） |

## 6. 待裁决（延续起草期清单，供用户裁定）

| 编号 | 事项 | 状态 |
|---|---|---|
| P1 | 是否由本任务填充 `content.publish.image_count` 与 `reaction.set.{value, previous_value}`（需改 NC-009/NC-012a 已验收文件与 `tests/test_community_interactions.py:149`） | **未采纳**：动已验收文件与断言，成本与回归面不成比例；契约 §3.2 以兼容形态覆盖（允许集含这些键，但不要求填充），登记为后续扩展候选 |
| P2 | 上报默认开关 UI 与隐私政策文本归属 | **未采纳**：属 PRD 产品决策与宿主 UI 范围，本任务只落数据链路 |
| P3 | `GET /v1/analytics/pseudonym`（DESIGN 未定义的新增补口） | **已采纳**（D-NC026-07）：客户端无法自行生成合规假名（不得由账号 ID 推导），必须由服务端交付 |
| P4 | DESIGN §11.2 客户端 `event_id` 措辞歧义 | **已采纳解读**（D-NC026-06）：统一 `bev_` + UUIDv4 hex（36 字符），服务端与客户端同构 |
| W1 | `xuan-handbook` 的 `core.autocrlf=true` 与任务书不符 | 未改动（避免影响在手册中工作的其他会话）；已登记 |
| W2 | `openspec/schemas/verify_community.sh` 的 Windows 适配缺口 | 不动 NC-002 已验收脚本（D-NC026-21）；守卫改用 `check-jsonschema.exe` + `file:///D:/` 直校验 |

## 7. 结论

| 维度 | 判定 |
|---|---|
| 忠实性 | PASS |
| 覆盖性 | PASS |
| 可执行性 | PASS |
| 独立性 | **不满足**（D-NC026-28，用户授权替代） |

**R1 判定：READY（带独立性保留）**。实现与验收证据见 `work-items/nc-026/ACCEPTANCE.md` 的「验收记录 R1」。
