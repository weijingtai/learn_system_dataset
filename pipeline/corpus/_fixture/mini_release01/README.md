# mini_release01 fixture（M7 增量汇编比对基准，act/impl-07/20）

本目录是 M7 **完整增量汇编**的规范验收宿主：两个版次（`ed01` 真实金标 span 锚定 +
`ed99` 合成保留号）以及由脚本确定性生成的**多版本 `canonical_snapshot` 金标**。

它存在的唯一目的是让后续每一波（A 输入解析 / B 提案生成 / C 应用裁定 / D 增量编排 /
E 独立 Gate / G 验收接线）都有一份**可重复、可进库、逐字节可比**的输入与期望产物基准。
本波（F 波）**不要求增量汇编跑通**：本目录只提供基准与真书差异报告。

立项依据：`docs/blackbox-spec-rework/work-items/impl-07-assembly/CHARTER-INCREMENTAL.md`
（D-10 采纳 A、D-02 A、D-03 A、D-17）。与 `README.md` §1–§8 冲突处以 CHARTER 为准。

## 1. 内容不作知识来源

两版次视图全部是**结构验收宿主**（`synthetic: true`、`content_status: machine_extracted`），
**不得**作为知识来源、证据来源或发布输入引用。`ed99` 是**合成保留版次号**，
不代表任何真实第二版次；`candidate_set` / `reviewed_edition` 中的审核结论均标
`decisions[].synthetic_fixture: true`，不计 `expert_verified`。

## 2. 锚定：mini_ed01 金标 span，一字不动

- 锚定文件：`../mini_ed01/spans.yaml`
- 冻结 sha256：`ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef`
  （与 `impl-07-assembly/README.md` §1.2 记录的金标一致；也写在本目录 `manifest.yaml`
  的 `span_anchor.sha256`）
- 两版次**全部**证据链（`assertions[].evidence` 与 `reviewed_edition.evidence_links`）
  的 `source_span_id` / `start_offset` / `end_offset` / `quote_sha256` 逐字取自该金标 span：
  `quote_sha256 = sha256(span.text)`。本目录**不复制、不改写 mini_ed01 任何文件**。
- 本目录**不含任何页图**（无 `png/jpg/jpeg/pdf`），`verify.sh` 也不读 `FIXTURE_ASSET_ROOT`：
  缺页素材不会让本夹具 BLOCKED。

用到的四个真实 span（`mini_ed01` 前 3 页）：

| span_id | 文本 | 偏移 |
|---|---|---|
| `ss_sanche_ed01_p0001_s01` | 三辰通載 | [0, 4) |
| `ss_sanche_ed01_p0001_s02` | （宋）錢如璧撰 | [5, 12) |
| `ss_sanche_ed01_p0003_s03` | 三辰通載目錄 | [9, 15) |
| `ss_sanche_ed01_p0003_s05` | 貴格之圗 | [20, 24) |

## 3. 目录结构

```text
mini_release01/
├── README.md                             本文件（人工维护，不参与重放比对）
├── manifest.yaml                         生成物：版次登记、锚定哈希、约定、上游假定、文件哈希
├── ed01/{candidate_set,reviewed_edition,reviewed_edition_package}.json
├── ed99/{candidate_set,reviewed_edition,reviewed_edition_package}.json
├── expected/snapshot_r1.json             创世轮金标（= 已验收创世引擎现算输出）
├── expected/snapshot_r2.json             增量轮金标（场景表逐项字面量）
├── expected/snapshot_revisions.yaml      D-03 身份计划：一个 Snapshot Artifact、每轮新 rev_
├── tools/build_fixture.py                确定性生成器（唯一输入路径）
├── tools/probe_real_m6.py                真书 m6 实跑探针（只读正本，跑在副本上）
└── verify.sh                             自校验（V1–V6）
```

## 4. 两版次与场景

`ed01`（`src_sanche_ed01`，版次一）是"基准轮"；`ed99`（`src_sanche_ed99`，合成保留号）
是"第二版次/新修订轮"。第二轮要覆盖的增量语义：

| 场景 | ed99 视图里的载体 | r2 金标里的期望 |
|---|---|---|
| `attach`（保号并入，只增证据） | `as_qizheng_900001`（命题与对齐单元与 ed01 逐字相同，另添一条证据 span） | `as_qizheng_900001` 保号，`evidence[]` 增为 2 条，`source_id` 仍为首见版次 `src_sanche_ed01` |
| `admit_new`（新主张入账） | `as_qizheng_900004`（命题 `三辰通載目錄`，新的对齐单元） | 新 `assertion`，`source_id=src_sanche_ed99`，挂到既有 `pat_qizheng_900001` |
| 别名并入 | `concept_mentions[].surface = 通載`（同一 `co_qizheng_900001`） | `concepts[0].aliases = ["通載"]`，`provenance[]` 增至 2 条 |
| 格局关联增长 | `pat_qizheng_900001`（**携带基底已正式的 pat_ 号**，断言集含新主张） | `patterns[0].assertion_ids` 增为 3 个，`provenance[]` 增至 2 条 |
| 未静默折叠 | `as_qizheng_900004` 与 `as_qizheng_900001` 文本近乎相同（`三辰通載目錄` vs `三辰通載`） | `relations[]` 记一条 `distinct_from`（`make_key("distinct_from", …)`），二者**不得**合并 |
| 冲突组增长 | `sv_…0002`（`sch_qizheng_002`，同 `cg_…0001`） | `conflict_groups[0].member_school_view_ids` 增为 2 个，`first_layer_display = true` |
| 版次并入 | `editions[]` 两个条目 | 按 `source_id` 升序，两条 `editions` |

约定：**可比单元 = `(work_key, collation_key)`**（D-07），`work_key = sanche`，
对齐键形态为 `sanche-000N`（连字符形态，**不是**任何 ID 前缀）。

## 5. 期望产物与生成命令

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python pipeline/corpus/_fixture/mini_release01/tools/build_fixture.py
```

生成物 sha256（本文件改动会同时改 `manifest.yaml` 的 `files[]`，由 `verify.sh` V2 钉死）：

| 文件 | sha256 |
|---|---|
| `ed01/candidate_set.json` | `1b3bb28f3a34a44b80d67c928b939ac098117eca98e63000f8c7734779222c09` |
| `ed01/reviewed_edition.json` | `8bdeefced37e138cac17ce4b8317b2f15eb0637512ceaa1748706707266da25a` |
| `ed01/reviewed_edition_package.json` | `b0abcca36792e8765cac1a793f649a0dff96219ca808f9b4fa969047566a41f6` |
| `ed99/candidate_set.json` | `2021edbea64da7e785c4a36a66c1b2f530a025854e2bb2e110792311e69271b6` |
| `ed99/reviewed_edition.json` | `7b905a768e8282af719dec7769bfaaeb14cc92d07268eae7c253c0e9a194ce78` |
| `ed99/reviewed_edition_package.json` | `34ce249c736412900e26d93234b1dc34adbc1136303776a8a9e24ad4d25dfaa7` |
| `expected/snapshot_r1.json` | `c20c5148d046452fc00f83b3d1633cd81012170fd60c41ebda35c8e3cdfc891c` |
| `expected/snapshot_r2.json` | `66a1e2f7534de0b57cb6c7debbfabd32f593f41fd895ef4350ed14f88c8fad25` |
| `expected/snapshot_revisions.yaml` | `c1251a486f4ed070d2076b7606c0e70f8fed6184c60e2aa2976416c5a449f9b0` |
| `manifest.yaml` | `69f248a9f1483cafeb802fb9406e25f302f9a05706932bb56a1f733ff82f1b6c` |

- `snapshot_r1.json`（`knowledge_sha256 = c20c5148…c891c`）由**已验收创世引擎**
  （`pipeline.assembly.genesis.propose_genesis` + `assemble_genesis`）在 `ed01` 视图上现算，
  生成器还会先跑一遍创世独立 Gate，**Gate 不过就拒绝生成**。它逐字节等于
  `run_m7` 在写入该夹具的临时 Ledger 上封存的 Snapshot（见 `test_release_fixture_seeds_into_temp_ledger_and_runs_genesis`）。
- `snapshot_r2.json`（`knowledge_sha256 = 66a1e2f7…8fad25`）由生成器内的**场景表逐项字面量**写出
  （D-10 采纳 A：不得实现通用增量汇编算法），只用 `canonical_json` / `sha256` 现算哈希；
  写入即过 `validate_snapshot_knowledge`。

**重放比对**（生成器无时间戳/绝对路径/随机值）：

```bash
.venv/bin/python pipeline/corpus/_fixture/mini_release01/tools/build_fixture.py --out /tmp/mini_release01_rebuild
diff -r --exclude=tools --exclude=README.md --exclude=verify.sh \
  /tmp/mini_release01_rebuild pipeline/corpus/_fixture/mini_release01   # 期望无输出
```

`manifest.yaml` 的 `files[]` 只登记上表 9 个生成物，**不含**自身、本文件与 `verify.sh`
（避免 mini_ed01 README §6 第 2 条记录过的哈希环）。

## 6. 约定标识不是新前缀

`ed99`（合成保留版次号）与 `9000NN`（合成对象号段 `[900001, 900099]`）是**约定标识**：

- 不进 `openspec/id-prefix-registry.md`，也不在 `openspec/` 任何文件中登记；
- 它们不是前缀形态（`ed99` 无下划线，号段只是 6 位数字段）；
- 夹具声明的前缀家族见 `manifest.yaml` 的 `id_families_used`，全部取自登记册 §3.1–§3.4
  的 M7 上游合法集合，**不含** `ent_`/`rel_`（属 M8）、`ku_`（旧管线）、`hg_`（Contract Registry）。

护栏用例：`test_fixture_uses_no_registered_id_prefix` 扫描 manifest / 两版次视图 / 两份金标
中全部 ID 语义字段，要求每个值都命中已登记前缀家族、且落在声明集合内。

## 7. 上游假定（本波已与真书 m6 实测逐条对照）

`manifest.yaml` 的 `upstream_assumptions` 声明了夹具对上游的假定，**每条都附真书实测值**。
真书实测由 `tools/probe_real_m6.py` 复算（只读正本、跑在 `cp -R` 副本上）：

| 假定 | 夹具假定 | 真书 m6 实测（2026-09-22，`var/ledgers/qianyuan_w8`） |
|---|---|---|
| A1 | M4 视图可携带基底已正式 `pat_` 号；M6 审核结论含 `assertion`/`pattern`/`school_view`/`concept` 四类 | 审核结论 **26/26 全为 `assertion`**；`candidate_set.patterns=2`、`school_views=0`、`concept_mentions=0` |
| A2 | 视图声明 `collation_units` 与 `assertion.collation_key`（D-07 前提） | **无 `collation_units` 键**，26 条 `collation_key` 全为 `null` |
| A3 | 两版次共享同一 `corpus_spans` 修订 | 每版次各有自己的 `corpus_spans` 修订 |
| A4 | 对象号取 `9000NN` 保留段（合成约定） | 取 `000001` 起的常规号段 |

⚠️ 真书 m6 的**可解析性**没问题（`resolve_m7_inputs` 通过、M7 三个 model 校验函数全部通过），
但**现有创世引擎在真书 m6 上过不了自己的 Gate**：

```text
run_m7(status=failed)  Gate FAIL allocation_monotonic: id_allocation[pat_qizheng]=2 != expected max 0
```

原因：真书只有 assertion 获批，`knowledge.patterns` 为空，而 `id_allocation` 仍按
*候选集*（2 个未获批 pattern）取最大号。差异清单见 F 波回报文件
（`/Users/jingtaiwei/tmux-agents/runs/fb-m7-f.report.md`）。本波**不修**该差异，
也不许为好看放宽 Gate。

## 8. 本波为增量轮选取的表示（B/C/D 波可改，但须同步重建金标）

1. **`attach` 的落点**：断言无 `provenance` 列表，故 `attach` 对断言表现为
   `evidence[]` 增长 + 保持首见 `source_id`；对 `concept`/`pattern` 表现为
   `provenance[]` 增长 + `aliases[]`/`assertion_ids` 合并。**保号**（不换 `entity_id`）。
2. **未静默折叠**：本轮只用 `relations[].distinct_from` 记录"近同文本未合并"；
   `Alignment` / `VariantReading` / `Addition` / `Omission` 属 `edition_collation_set`
   （D-07、B/D 波），本波**不预置**。`relations[].resolution` 只写 `{"mode": "auto"}`，
   `proposal_key` 属 `assembly_proposal_set`（B 波），本波不预置键格式。
3. **`editions[].edition_complete` 恒 `false`**：单 Part 输入（D-17 采纳 A）。
4. **r1 金标的包身份是占位值**：现有引擎在 `assemble_genesis` 未收到包身份参数时写入
   `rev_00000000000000000000000000000000` / `pkg_m6_00000000000000000000000000000000`。
   这是已验收引擎的当前行为（不是本夹具的假定）；B 波接线真实包身份后，**必须按
   §5 命令重建 r1 并同步哈希**。r2 金标按 `manifest.editions[].ledger_constants`
   写入真实约定常量。

## 9. 自校验

```bash
bash pipeline/corpus/_fixture/mini_release01/verify.sh; echo "exit=$?"
```

| 检查 | 内容 |
|---|---|
| `V1 host_files` | 宿主文件齐备 |
| `V2 manifest_sha256` | `manifest.files[]` 每项 sha256 与实际逐字节一致 |
| `V3 span_anchor` | 两版次全部证据链锚定 mini_ed01 金标 span（id / 偏移 / quote_sha256），锚定哈希一致，版次数 ≥ 2 |
| `V4 views_validate` | 两版次视图过 M7 的 `validate_candidate_set` / `validate_reviewed_edition` / `validate_reviewed_package` |
| `V5 expected_goldens` | r1 逐字节等于创世引擎现算输出且过创世 Gate；r2 过 `validate_snapshot_knowledge`；`knowledge_sha256` 与文件一致 |
| `V6 no_page_assets` | 本目录无图像/PDF，不依赖任何页素材 |

退出码：任一 `FAIL` → 1；无 `FAIL` 但有 `BLOCKED` → 3（`.venv` 缺失即 `BLOCKED_ENV`）；否则 0。
末行 `FIXTURE OK`。本机实跑六项全 `PASS`，`exit=0`。

## 10. 真书 m6 探针

```bash
.venv/bin/python pipeline/corpus/_fixture/mini_release01/tools/probe_real_m6.py [--json]
```

只读 `var/ledgers/qianyuan_w8`（**正本绝不写入**），把整份账本 `cp -R` 到临时目录后：
列出 m3–m6 StagePackage、跑 `resolve_m7_inputs`、过三个 model 校验、逐条打印真实字段形状、
干跑 propose/assemble/gate、实跑 `run_m7`（在副本上）、并按 D-02 在一份 ReleaseRun 上落
Checkpoint 链验证 scope 键可行。退出码 0 = 探针跑完（"接不上"是结论不是失败）。
