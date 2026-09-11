# NC-002 工作包审查 R1（wjt-react 四查）与返工落实

日期：2026-09-11。审查对象：提交 `437571b`。审查人：独立只读 Agent（Opus，未参与编写）；返工裁定与落实：主 Agent（C/S 会话）。守卫：`bash docs/blackbox-spec-rework/reviews/nc002_guard.sh`。

## 0. 结论

判定 **REWORK**：6 项阻断（R1～R6）、6 项高（R7～R12）、8 项中低（R13～R20）、8 条建议（S1～S8）。忠实性除本地错误类名与 CommandRecord 终态外 PASS；参考编码器逐句符合 §7.2，另发现 `-0`/重复键在 `json.loads` 后不可见（R16）。

## 1. 返工项与落实

| # | 问题（摘要） | 落实 |
|---|---|---|
| R1 | `test_unknown_state_red` 注入值 `deleted` 在枚举并集内，红测恒不红 | 注入值改 `Purged`；V3 放行集缩为 `{"new"}`（S7） |
| R2 | 结构块「所有对象 additionalProperties: false」与三处开放对象冲突 | §2.3 4(a) 与 B01 写明豁免 `resource_ids` / `result_fields` / `attributes` |
| R3 | reaction「required 8」与契约 7 字段矛盾 | 改 required 7 并列出字段 |
| R4 | 配对正例会被步 2 推断到不存在的 Schema | 排除规则：`community_pair_*` 与两个结构块专属文件不参与步 2/3 |
| R5 | ACCEPTANCE PASS 行数公式不可达 | 改为「参与逐例校验示例数 + 3」，并写明参与数的算法 |
| R6 | 结构块「遍历 12 个 Schema」在 act/01～02 不可达 | 改为 glob 不断言数量；数量断言留守卫 K08 |
| R7 | B05 引用了不存在的示例文件名 | B05 改用配对 invalid 与 `invalid_quotes_without_anchor` |
| R8 | act/02 WORKLOAD 示例数错 | 重排后各 ACT 的 WORKLOAD 与 WRITE_NEW 数量一致 |
| R9 | selector `end > start` 无处落实 | 结构块新增 4(d) + `invalid_range_end_le_start.yaml`（B22） |
| R10 | CommandRecord 完整/精简/拒绝终态无承接 | act/04 增 `valid_rejected` / `valid_compacted` 与两条 if/then；按 operation 成对白名单登记推迟 NC-003（ACT.yaml DEFERRED，契约 §3.2） |
| R11 | DEPENDENCY_ALLOWLIST 缺 jsonschema/PyYAML | 补「.venv 既有 jsonschema 4.26.0、PyYAML 6.0.3，仅结构块 import」 |
| R12 | act/01 55 分钟与工作量不相称 | 拆为 act/01（common+note+前三步）与 act/02（note_revision+配对+结构块）；总步数 5 → 6 |
| R13 | 多条 Schema 约束无反例 | 增 `invalid_duplicate_heads`、`invalid_duplicate_parent_ids`、`invalid_title_201`、`valid_4000_emoji`（code point 语义） |
| R14 | 六个本地错误类名无来源 | 契约新增 D-NC002-10 冻结八个类名（含 R15 的 `TombstoneRejected`） |
| R15 | SM-3 本地映射不完整 | SM-3 抬头增 HTTP→本地映射表 |
| R16 | `-0` 与重复键在解析后不可见 | 裁定：解析层职责。参考编码器增 `load_snapshot_json`；fixture 增 `invalid_json_texts` 3 例；TDD §4 增 `load_snapshot_json` API 与第 8 个测试；契约 §1.2 写明 |
| R17 | 字节/code point 口径混用；target_ref 无长度约束 | 契约 §0 与 §1.2 改口径；common 增 `targetRef` $def |
| R18 | C17「同步进度」名义覆盖 | C17 记录增 `sync_state`/`backup_state`/`created_on_device`；`project_revision` 忽略未知键写入契约与 TDD |
| R19 | act/05（现 06）路径缺绝对前缀 | 全部绝对路径 |
| R20 | READ 列出 pytest 风格文件与 unittest 要求矛盾 | 删除该条 |

建议：S1 删除 `list_limit_0`（DESIGN 未定义，fixture 16 例）；S2 引用改为可解析路径（文件在仓库根，审查者「不存在」的说法不成立）；S3 守卫补 K07（verify.sh 零改动）；S4 见下；S5 删模板噪音规则；S6 B11 写死 198；S7 已并入 R1；S8 守卫改 `== 41`。

## 2. 追加裁定：不修改 `openspec/schemas/verify.sh`（D-NC002-11）

黑箱线（Dataset 会话）2026-09-11 提出：verify.sh 是 D-02 已验收的 L0 唯一验证命令，其 `set -e` 会把社区 fixture 的红误报成黑箱线阻断。采纳：社区校验由 `verify_community.sh` 独立承担，全任务不触碰 verify.sh；守卫 K01 依次运行两者，K07 核对 verify.sh 与 `437571b` 版本字节相同。S4 的红窗口担忧随之消失。

## 3. 同步事实

- 黑箱规格 §16 `AnchorContractPack` 已落地（e474ae4）：可锚定白名单与 `target_kind` 四值一致，AnchorRef 三要素一致；D-NC002-02 已注明。
- `openspec/id-prefix-registry.md`（38d44f3）尚无社区 17 个前缀；已向黑箱线提出追加 §3.5，待其回复后落实。

## 4. 完成标准

`bash docs/blackbox-spec-rework/reviews/nc002_guard.sh` 与 `git diff --check` 均为 0；第二轮审查由另一位未参与者执行。

## 5. 第二轮审查（R2，2026-09-11）与落实

审查人：另一独立只读 Agent（Opus）。R1 的 28 项中 25 项 CLOSED；未闭合 R8（act/04 示例数）、R15（SM-3 映射引用了不存在的 fixture 事实）、S5（模板噪音）。新报 9 项（1 阻断）+ 4 建议，全部落实：

| # | 问题 | 落实 |
|---|---|---|
| 1（阻断） | act/04 漏 R10 新增的 `valid_rejected`/`valid_compacted`，示例 7→9、16→18 | 改正；守卫 K08 增 command_record 示例 = 9、B23 四文件存在、示例总数 = 62 |
| 2 | 结构块 4(b) glob 命中 note_revision | 改精确 glob `community_note.*.yaml`（7 个） |
| 3 | SM-3 映射表引用「local: true 只取 409 分支」空集 | 改为只按 HTTP 状态码映射，不引用 fixture 标记 |
| 4 | act/02 结构块 Red 无可观察原文 | 结构块打印 `CHECK 4(x) <文件> <PASS/FAIL>`；Red 原文为三行错误放行；守卫 K05 断言 TDD 含该形态 |
| 5 | §2.2 正反例拆分 14+44 错 | 改 16+42；守卫断言 |
| 6 | act/01 残留「verify.sh 追加行」 | 删除；守卫模式加 `verify.sh 追加` |
| 7 | command_record required 13 未列字段 | 逐字列出 |
| 8 | 4(a) 豁免表达不可机械判定 | 改为 JSON Pointer 前缀豁免，`then`/`allOf` 内一律 false |
| 9 | 契约 §1.2 解析层句漏 NaN/Infinity | 补齐 |
| 建议 | S5 收尾、K07 改判据、D-NC002-10 理由措辞、$defs 29 | 全部落实（K07 改为「最近触碰 verify.sh 的提交不属于 nc-002 且无未提交改动且不含 verify_community」） |

第三轮审查缩小为：复核本节 9 项 + 对 `4205a03..HEAD` 的 diff 做回归；仍不 READY 则停止并上报用户。
