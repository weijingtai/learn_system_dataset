# M7 完整增量汇编 · 立项文档

> 主 Agent 2026-09-22 立项。本文件解除 `README.md` §1–§8 的 `DEFERRED` 状态，
> 逐条裁定 §4 的 D-01～D-18，并把既有 `act/02–10` 重新校准为可派发的波次。
> **本文件是派发依据；与 README §1–§8 冲突处以本文件为准。**

---

## 1. 这件事是什么

M6 审完一本书，产出的是**这一本**的断言、概念、格局。
M7 把它们**并入一份总账**（`canonical_knowledge_snapshot`）——"到目前为止所有书加起来我们知道什么"。

**创世（第一本书、空基底）已经实现并验收**（G0 组，`assembly` 107 用例全绿）。
**增量（第二本书、或同一本书的新修订）一行没写。**

为什么现在做：不做增量，这条链**只能处理第一本书的第一版**。
第二本书接不上、同一本书改一版也接不上——**一个只能用一次的流水线不算流水线**。
这是当前距离投产最大的一块缺口（其余缺口见 `tasks/dataset-blackbox-line.md` 当前状态段）。

---

## 2. 原草稿的三处前提已经变了（立项的主要价值）

README §1–§8 起草于 2026-09 上旬，当时 M4/M5/M6 都不存在。今天事实不同：

| # | 草稿假定 | 今天的事实（主 Agent 2026-09-22 实测） | 影响 |
|---|---|---|---|
| P1 | 「输入不是真实 M4–M6 产物（尚不存在）」（§1.1） | 真书账本 `var/ledgers/qianyuan_w8` 有 **m3/m4/m5/m6 四个 stage package**；M6 已 `close` 封存、26 条审核决定已导入 | **真实上游存在**，不必只靠金标 fixture |
| P2 | 「`m7-assembler.sh` 固定保留一行 `BLOCKED upstream_m6_real`，只能返回 2」（§1.2） | 该项**当前显示 PASS，但跑的不是真书** | **见下方「P2 更正」** |
| P3 | ACT 02「包骨架 + 规范化 + ReviewedEdition 视图」待建 | **g0-01 已建**（`canonical.py` / `model.py` / `genesis.py` / `gate.py` / `inputs.py` 均在库），W8 8.5（act/11）又补了 `evidence_level` / `corpus_spans_revision_id` | ACT 02 **不能照原样派发**，须改为「在既有骨架上扩增量」 |

### P2 更正（主 Agent 2026-09-22，F 波实测后）

**立项时我把 `upstream_m6_real` 的 PASS 当成了「真实上游已接通」，这是错的。**

实测（`pipeline/assembly/acceptance.py:61` `_prepare_with_real_m6`）：该判据用的是
`pipeline/review/testing/upstream_stub` 的桩数据 + `mini_ed01` 夹具，
**不是** `var/ledgers/qianyuan_w8` 的真书 m6。**名字叫 real，跑的是桩。**

这与 W8 的 `patch_reversible` 是同一形状的缺陷：**一个判据名声称它在验什么，实际验的是别的东西**。
判据名不能当证据，必须看它实际跑什么——这是 R14 的直接应用，而我这次又犯了。

**后果与处置**：
- P2 不成立。真书路径至今**没有**被任何验收判据覆盖
- **G 波必须新增一条独立判据**，明确以 `var/ledgers/qianyuan_w8` 真书 m6 为输入（副本上跑），
  与现有 `upstream_m6_real`（桩）**并列而非替换**
- 现有 `upstream_m6_real` **不得改名或删除**（它验的桩路径本身有价值），
  但 G 波须在其 detail 里写明「输入为合成桩」，消除名实不符

**结论**：既有 `act/02–10` 是有价值的草稿，但**必须按上述三点重新校准后才能派发**，
照原样丢给执行器会让它去重建已经存在的东西。校准方式见 §5。

---

## 3. 裁定：D-01 ～ D-18

除特别注明外，**采纳 README §4 的推荐项**（其推荐均有规格行号支撑，主 Agent 已逐条复核）。

| 条目 | 裁定 | 备注 |
|---|---|---|
| D-01 首纵切 M8 的 Snapshot 从哪来 | **已被 W8 覆盖，作废** | ACT 13（`ae15eca`）已让 M8 读真实 M7 Snapshot；本条不再是未决点 |
| D-02 ReleaseRun 的 scope 键 | **采纳 A** | 零 Ledger 改动；键有真实 Artifact 行支撑 |
| D-03 Snapshot 粒度与身份 | **采纳 A** | 每 technique 一个 Snapshot Artifact，每次汇编写新 `rev_` |
| D-04 Pattern 身份谁发号 | **采纳 A** | M7 在 `admit_new` 获批时发号；`as_`/`co_` 由 M4 发，M7 只做碰撞检测 fail-closed |
| D-05 attach vs merge 两种语义 | **采纳 A** | 闭集 `{attach, admit_new, merge_entities}`；**禁止静默并入** |
| D-06 自动/人工边界 | **采纳 A** | 名称相等**不得**自动 attach（保留同名异义） |
| D-07 「可比内容」如何判定 | **采纳 A，并追加硬约束** | 见下方 §3.1 —— **这是本次最要紧的一条** |
| D-08 对象级所见修订粒度 | **采纳 A** | 对象不单独入 Ledger |
| D-09 人工决定 `decision_type` | **采纳 A** | 复用既有闭集，不改规格 |
| D-10 新规范 fixture | **改判，见 §3.2** | 不再是「唯一输入路径」 |
| D-11 新 artifact_type | **采纳 A** | 四类新 artifact_type |
| D-12 提案与对勘标识 | **采纳 A** | 不发登记 ID，用内容哈希键 |
| D-13 §20.5 何时 PASS | **改判为 A′，见 §3.3** | P2 前提已变 |
| D-14 M6 返工进入 ReleaseRun | **采纳 A** | 以 (source_id, edition_part_ids 集合) 识别替换 |
| D-15 基底修订状态与并发 | **采纳 A** | 封存后 `supersede_revision`；并发第二个 Run 在 begin 前拒绝 |
| D-16 Checkpoint 落盘粒度 | **采纳 A** | 视同人工阶段，人工决定即时落盘 |
| D-17 Part 级能否汇编 | **采纳 A** | 允许；完整性由 M8 按消费级别卡 |
| D-18 Work 标识 | **采纳推荐** | 随 §5 波次 A 一并确认，若草稿无推荐则停手上报 |

### 3.1 D-07 追加硬约束：语义配对必须关在可替换的盒子里

README 推荐 A（可比单元 = `(work_key, collation_key)`，精确匹配，转人工兜底），主 Agent **采纳**，
并追加三条**不可协商**的约束：

1. **M7 不调用任何模型**——这是规格约束不是偏好：
   `openspec/learn-system-blackbox-architecture.md:40`（§2.10）「模型输出只能成为候选；M7 不调用模型」，
   README §3 禁止项亦明文写「调用任何模型 API；做模糊文本相似度匹配」。
2. **配对层必须是一个独立函数、独立文件**，签名固定为
   `propose_pairs(left_units, right_units) -> list[PairCandidate]`，
   本波次内**只允许确定性实现**（精确键相等、共享证据片段、同一已正式对象）。
3. **该函数之外的任何代码不得直接做配对判断**。
   将来若要接入模型建议，只换这一个文件，且模型结论只能落在
   `PairCandidate.suggestion` 旁路字段——**不得进入 Gate 判定、不得影响 ID 发号、不得改变自动裁定结果**。

理由：合并的难点是语义判断，确实是模型擅长的形状；但 M7 的产出带 `canonical_hash`、要被引用被审计，
**同样输入必须产出同样字节**。把不确定性放在写入端，错误会永久固化进总账，
而读取端的错误只影响那一次查询。此外 2026-09-19 的实测已证明：
「找出哪些是同一件事」本质是**比对任务**而非判断任务（Jev 在同类任务上真实召回 0/5），
所以**候选必须由代码检索，模型至多在候选上做判断**。

> RAG 的位置在 M8 之后：M7 建库 → M8 出可检索数据集（`SearchIndexPack`）→ RAG 在其上查询。
> RAG 是 M7 的下游消费者，不是替代品。

### 3.2 D-10 改判：fixture 保留，但真书是第一等公民

原推荐 A（新建 `mini_release01` 金标 fixture）**采纳其形式，改判其定位**：

- fixture **仍要建**——单元测试与验收脚本不得依赖 `var/`（运行时账本，且被 `.gitignore` 忽略）
- 但它**不再是唯一输入路径**。本波次的完成判据**增加一条**：
  必须用**真书 `var/ledgers/qianyuan_w8` 的真实 m6 产物**跑通一次汇编（只读正本，实跑在副本上），
  并把结果与 fixture 路径的结果一并写入回报
- 理由：P1。真实上游已经存在，只用合成金标就验证不了「真实产物能不能接上」——
  W8 全程反复出现「夹具绿、真书红」（M8 输入解析、gate 适用性、patch_reversible 三次），
  这个教训必须写进 M7 的判据

### 3.3 D-13 改判为 A′

原推荐 A：`m7-assembler.sh` 固定保留 `BLOCKED upstream_m6_real`，`run_all.sh 20.5` 只能 BLOCKED。
**P2 前提已变**（g0-06 已做成可转判路径）。改判：

- `20.5` 的判定**由 `m7-assembler.sh` 的真实退出码决定**：0 → PASS，2 → BLOCKED，1 → FAIL
- **不得写死任何一种结果**（与 W8 ACT 17 同一原则：适用性声明必须与实现一致）
- 真书路径跑通后 `20.5` 自然转 PASS；跑不通就如实 BLOCKED/FAIL，**不许为了好看而硬判**

---

## 4. 不许做的事（沿用 README §3，加两条）

沿用 README §3 全部禁止项，其中最要紧的：

- **不调用任何模型 API、不做模糊文本相似度匹配**（§2.10）
- 不改规格正文、`openspec/schemas/**`、`pipeline/corpus/_fixture/mini_ed01/**`、`pipeline/ledger/**`
- 不新增依赖（只用标准库 + PyYAML + jsonschema）；不新增 ID 前缀
- 生产代码不读 fixture 路径或工作目录文件（只读 Ledger 冻结修订）
- M7 不发 `ent_`/`rel_`（属 M8）；不合成或升级内容成熟度状态

主 Agent 追加两条：

- **不许写 `var/ledgers/qianyuan_w8/` 真书正本**（只读；实跑在 `cp -R` 的副本上）
- **不许为了让判据好看而放宽 Gate 或写死判定结果**（W8 ACT 17/18 的教训：
  `patch_reversible` 曾因参数从未传入而恒返回 ok，一个不检查任何东西的「绿」比红更危险）

---

## 5. 波次与既有 ACT 的校准

既有 `act/02–10` 保留，但**派发前须按 §2 的三点校准**。校准责任在主 Agent，执行器不得自行改 ACT。

| 波 | 内容 | 既有 ACT | 校准动作 |
|---|---|---|---|
| **A** | ReleaseRun 输入解析与冻结、基底 Snapshot 读取、Work 标识 | act/02 | **重写**：骨架已由 g0-01 建成，本波只加「多输入 + 基底读取」，不得重建 `canonical.py`/`model.py` |
| **B** | 四类提案确定性生成（Merge/Alias/Conflict/EvidenceRelation），含 §3.1 的独立配对函数 | act/03 | 校准：明确 `propose_pairs` 独立文件与签名；R01–R10 规则表沿用 |
| **C** | 应用裁定：发号、对勘集、IdentityDelta | act/04 | 校准：发号规则按 D-04 裁定；`as_`/`co_` 只做碰撞检测 |
| **D** | 增量编排：affected_closure、替换继承、人审回流只重算受影响提案 | act/05 | 校准：替换识别按 D-14 |
| **E** | 独立 Gate（不 import 汇编逻辑，自行重算）四项判定 | act/06 | 校准：沿用 W8 ACT 18 的原则——**独立重算才是独立验证**，不得照搬被验对象实现 |
| **F** | fixture `mini_release01` + 真书路径 | act/00–01 | 校准：按 §3.2，真书路径为必跑项 |
| **G** | `m7-assembler.sh` 十四项判定 + `run_all.sh 20.5` 接线 | act/09、act/10 | 校准：按 §3.3 的 A′，判定由真实退出码决定 |

**建议派发顺序**：F → A → B → C → D → E → G。
F 先行是因为后面每一波都要拿它当比对基准；G 最后是因为它要断言前面全部的产出。

**并行可能**：F 与 A 可并行（不同文件）；B/C/D 必须串行（同一批状态机）；E 可在 D 之后与 G 并行起草。

---

## 6. 完成定义

```bash
export LC_ALL=en_US.UTF-8
bash openspec/acceptance/m7-assembler.sh; echo exit=$?
# 期望：十四项判定全部给出真实结论；exit 由真实结果决定，不写死
bash openspec/acceptance/run_all.sh 20.5
# 期望：判定来自 m7-assembler.sh 的退出码（A′）
.venv/bin/python -m unittest discover -s pipeline/assembly/tests -t . 2>&1 | tail -1   # OK
```

加上 §3.2 的真书判据：

- 用真书 m6 真实产物跑通一次汇编（副本上），产出新 Snapshot 修订，基底转 `superseded`
- 同一输入连跑两次，`canonical_hash` **逐字节相同**（可复现性）
- 增量结果与「全量重算」结果**一致**（Gate 第四项）

---

## 7. 派发须知（写给起草 ACT 的主 Agent 自己）

- **R14**：ACT `background` 里每条事实必须当场跑命令确认，命令与输出一并写入。
  W8 期间四次被执行器顶回来，全部源于凭印象写事实（详见 `tasks/dataset-blackbox-line.md` 决定记录）
- **R13**：篡改探针副本必须 `cp -R` 整个仓库（含被 gitignore 的 `ocr/`），否则出假阴性
- 每个 ACT 必须写明停手条件；执行器遇未知**停手上报而非自行选择**——
  W8 期间这条纪律四次避免了事故

---

## 8. F 波实测后的追加裁定（2026-09-22）

F 波（`827fabb`）在真书上探出四件事，逐条裁定：

### 8.1 真书 M6 只批 assertion，不批 pattern → 创世 Gate 在真书上恒红

实测：26/26 审核结论全是 `assertion`；`candidate_set.patterns` 有 2 条
`pat_qizheng_000001/000002` 但**不在 `approved` 里**；
而 `id_allocation` 仍按这 2 条未获批 pattern 取号 →
`evaluate_genesis` 报 `allocation_monotonic: id_allocation[pat_qizheng]=2 != expected max 0`。

**裁定（采纳方向 b，并给出与裁定 64 不冲突的理由）**：
`id_allocation` **只按「已获批、进入 Snapshot 的对象」取号**。

理由——裁定 64 的「号 = 该技法命名空间历史最大号（**含已退役**）+ 1」，
其中「已退役」指的是 **M7 发过号之后再退役**的对象；
而真书这 2 条是 **M4 自发号、从未获批、M7 从未发过号**的候选，两者性质不同。
按 D-04 A，M4 本就**不该**自发 `pat_` 号（只能携带已正式的号或不带号的 `candidate_key`），
所以它们的号从一开始就不该占用正式编号空间。
让未经审核的内容影响正式编号，等于让未审内容获得事实上的身份。

**追加硬约束**：M7 遇到「携带自发 `pat_` 号的未获批候选」必须**如实写入 `assembly_report`**
（例如 `unapproved_with_self_issued_id`），**不得静默丢弃**。
现状两处口径不一致（Snapshot 丢掉它、`id_allocation` 又算上它），根因正是静默。

### 8.2 D-07 的 `collation_key` / `collation_units` 在真书路径不存在

实测：`candidate_set` 无 `collation_units` 键；26 条断言的 `collation_key` **全为 `null`**。

**裁定**：B 波**先只做「同一已正式对象 + 共享证据片段」的确定性配对**，
完整对勘（D-07 的 `(work_key, collation_key)`）**推迟到 M4 接口补齐之后**。
B 波的 `propose_pairs`（CHARTER §3.1 的独立函数）须对 `collation_key` 为 null 的输入
**如实返回「无法配对」而不是猜**，并在 `assembly_report` 里计数。

### 8.3 `reviewed_edition.decisions[]` 的规范键集：以真书为准

真书用 `decision_type` + `verdict`，g0 合成宿主用 `choice`。
**裁定**：以**真书形态为规范**。F 波已把新夹具改成真书同形，正确。
旧合成宿主 `tests/data/genesis_package.json` 在 G0 已验收范围内，**本轮不动**；
若 A/B 波发现必须统一才能继续，停手上报，不得顺手改已验收金标。

### 8.4 r1 金标携带占位包身份

实测：`assemble_genesis` 未被传入真实包身份时写占位 `pkg_m6_0000…` / `rev_0000…`。
**裁定**：B 波接线真实包身份后**必须重建 r1 金标**并在回报中贴出新旧 sha256 对照。
不得让占位值留在金标里冒充真值。

---

## 9. A 波实测后的追加裁定（2026-09-22）

A 波（`8162585`）交付合格（assembly 117→126 OK，四个冻结模块未动，两项护栏仍 PASS，
计算路径一字未动、**未偷跑合并**）。它提了四条，逐条裁定：

### 9.1 基底 artifact_type：以登记名 `canonical_snapshot` 为准（我的 ACT 写错了）

ACT 21 contract 二.2 写的 `canonical_knowledge_snapshot` 是**草稿名**，错的。
实测登记名为 `canonical_snapshot`（`impl-00-interfaces/INTERFACES.md:181`「既有 `canonical_snapshot` 修订」；
`impl-07-assembly/README.md:113` D-0-3 亦明文「以登记名为准」）。
**裁定：`canonical_snapshot`**。执行器照登记名实现是对的——
若照我 ACT 的字面写，M7 自己产出的 Snapshot 永远无法作为基底，功能自相矛盾。

> 这是我第 6 次把没查证的事实写进 ACT（R14）。前五次见 `tasks/dataset-blackbox-line.md` 决定记录与 §2「P2 更正」。

### 9.2 D-02 scope 键：**增量启用、创世不变**（ACT 内部两条硬性确实冲突）

执行器指出 ACT 21 第三节「**每个** ReleaseRun 用 X 作 scope」与「创世路径逐字不变、
107 个既有用例不许转红」不能同时成立——因为 `BDD.md:G0.8`、
`acceptance.check_configuration_and_scope`、`test_genesis_ledger` 三处都断言
`prun.edition_part_id == world["edition_part_id"]`。

**裁定：采纳执行器的处理**——增量（base 非 None）用 X，创世（base 为 None）沿用 `edition_part_id`。
理由与 D-02 本身一致：D-02 的论据是「ReleaseRun 跨多个 Edition，没有单一 EditionPart」，
而**创世只有单包单版次，不存在该问题**。全面切换需同步改 BDD + 验收判据 + 2 条用例，
属跨波改动，**不在本线范围**；若将来要做，另立 ACT 并明示。

### 9.3 增量路径目前「名实不符」——B 波必须收口（本条最要紧）

执行器主动点名了一处中间态：

```
snapshot 修订 prev_revision_id = <基底>     ← 陈说「有基底」
knowledge.meta.base_snapshot_revision_id = null   ← 陈说「无基底」
```

成因：D-03（同 Artifact 续修订）已接线，而合并未接线，增量轮仍由 `assemble_genesis` 算，
产出的是创世形状。**这不是伪造，是「接了一半」的必然中间态**，但它正是 W8 反复出现的那类形状
（`patch_reversible` 空转绿、`upstream_m6_real` 名实不符）。

**裁定**：
1. 承认该中间态在 A 波是**可接受的**（执行器按 `on_fail ②` 没有扩范围到 B 波，处理正确）
2. **B 波必须收口**：接线合并时同时补 `meta.base_snapshot_revision_id` / `assembly_seq` / `decision_refs`，
   并按 §8.4 重建 r1 金标
3. **B 波的 ACT 必须写一条护栏用例**：断言「`prev_revision_id` 非空 ⟺ `meta.base_snapshot_revision_id` 非空」，
   两者不一致即失败。**这条是本线最重要的名实一致护栏**
4. E 波的独立增量 Gate 依赖本条——现 `evaluate_genesis` 只适用于创世

### 9.4 改动 1 条既有用例：批准

该用例断言的是「`run_m7` 拒绝 base_snapshot」——正是 ACT 21 明令删除的行为。
**属「事实变了、用例随之更新」，不是放宽判据**，与 W8 ACT 18 对
`test_offset_fixture_reports_run_failed_not_host_missing` 的处理同一性质。
执行器已在回报中报备（第 97 条要求），**批准**。

---

## 10. B 波验收与一条护栏范围问题（2026-09-22）

B 波（`b1013b5`）验收通过：assembly 126→136 OK，四个冻结模块未动，
两项护栏仍 PASS，禁用库 grep 干净。主 Agent 亲验两条探针：

- **P3**（把 `meta.base_snapshot_revision_id` 写死 None、保留 `prev_revision_id`）
  → 精确命中 `test_prev_revision_and_meta_base_agree`。**§9.3 的名实一致护栏是真的。**
- **P1b**（在 `incremental.py` 内直接比对 `collation_key`）
  → 命中 `test_propose_pairs_is_the_only_matching_site`。

### 10.1 结构护栏的范围偏窄（E 波须补）

主 Agent 第一次注入的是**未被调用**的比对函数，套件**未红**；改成真实比对 `collation_key` 才命中。
查看实现（`test_incremental_proposals.py:133`）：该护栏用正则只匹配
`collation_key"] ==` 这一种字面形态。

**结论**：它挡得住「照它设计的那种绕过」，挡不住换个字段的——
绕开 `propose_pairs` 去比对 `name` / `ast_sha256` / `nfc_key` 都抓不到。
这不构成 B 波缺陷（死代码不是真实绕过，真实注入也确实命中），但覆盖面须补。

**裁定（写入 E 波要求）**：E 波的独立 Gate 必须以**行为事实**验证
「配对结果只能来自 `matcher.py`」——例如在 Gate 侧 monkeypatch/探测
`propose_pairs` 的调用，断言「不经它就产不出配对结果」，
**而不是靠 grep 源码文本**。行为验证比文本匹配结实，
这与 W8 ACT 18「独立重算才是独立验证」是同一条原则。


---

## 11. C 波的 difflib 例外（2026-09-22）

正文在 `act/23.yaml` 第一节。要点：`difflib` 只许在 `apply.py` 里**记录**已确立配对的差异，
`matcher.py` / `incremental.py` 仍然绝对禁止；必须有护栏证明它"只记录、不决策"。
C 波已落实并验收（`564717f`），主 Agent 亲验探针命中。

## 12. D 波两处草稿校准（2026-09-22）

正文在 `act/24.yaml` 第一节。要点：提案入口调用 `incremental.propose_incremental`，
**不得**在 `matcher.py` 里新增 `propose`；接线 `run_m7` 后仍须守住 §9.3 的名实一致。

---

## 13. D 波验收与三条裁定（2026-09-22）

D 波提交 `93764a5`。主 Agent 独立复验：`assembly` 151 → **163 OK**；
七个冻结模块一行未动；`m7-assembler.sh` `pass=11 fail=0 blocked=5`，两项护栏仍 PASS；`var/` 未入库。

A、B 两波测试文件被改了三处，执行器逐条说明了改前改后和理由：
都是"`run_m7` 接通合并后，旧的'增量轮不写 Snapshot'预期本该变"。
§3.1 移走的 `awaiting_human` 覆盖**另写了具名用例补回**；§3.3 实际是**加严**（多了一份真实的非空快照进入断言）。
主 Agent 认可，不算削弱。

真书第二轮实跑（基底取 r1 金标）：待决提案 0 条；affected=0、untouched=6、created=26；
**增量与全量等价**。但 `run_m7` 最终 `status=failed`，原因见 §13.3。

### 13.1 `rebuilt == affected` 验不到它名字说的东西 —— 采纳执行器建议

执行器指出：`apply._rebuilt_ids` 在两种情形下结果都等于 `touched`，
`rebuilt_entity_ids` 对 `affected` 参数完全不敏感。所以这条断言实际只验了"闭包没有过宽"，
**并不验**"没有偷偷全量重建"。它已经补了一条行为护栏（监视传给 `apply._restore_untouched` 的
`affected` 必须恰好是闭包集合，不能是 None），补上后 P1 探针转红。

这是本线第三次出现"判据名说验 A、实际验 B"（前两次：`upstream_m6_real`、`patch_reversible`）。
**E 波的独立 Gate 必须用行为事实验证增量，不许只看 `rebuilt_entity_ids`**，与 §10.1 同向。

### 13.2 闭包扩张与 `rebuilt == affected` 互斥 —— 裁定取 (b)，并补一条闭包健全性检查

执行器问：闭包沿 `alias_of` / `conflict_groups` 扩张到的基底对象，`apply` 永远不会重建它们，
于是 `rebuilt ⊊ affected`，按草稿断言 `assemble` 会拒收——**扩张语义一旦真的扩张，增量轮就挂**。

三个选项里：
- (a) 闭包只取 `touched` 交集：扩张就没意义了，健全性检查也变成同义反复。**否**。
- (c) 维持现状，扩张即拒收：真实基底里只要有关系边，第二本书就跑不过。这不是告警，是坏掉。**否**。
- **(b) 采纳**：扩张到的对象计入 `affected`，但**不要求**它们被重建，按原样拷贝。

主 Agent 核实 `apply.py:1597-1605` 后追加一条硬约束。`_restore_untouched` 会把
"不在 `affected` 里、**或**本轮没被触及"的基底对象原样拷回。所以：
**如果闭包漏掉了一个其实被改动的对象，这次的改动会被基底旧版静默覆盖，不报任何错。**
草稿的等式断言从来没防住这个洞。

所以 (b) 的完整口径是：
1. **删掉** `rebuilt == affected` 等式断言（它在扩张时不可满足，不扩张时又是空转）。
2. **新增闭包健全性检查**：`orchestrate` 在调用 `apply` **之前**，从自己交给 `apply` 的裁定里
   独立推出"本轮将要改动的对象集"，断言它 ⊆ `affected`；不满足 → `AssemblyRefused`，
   message 含「闭包不完整」。推导**不许依赖 `apply` 的内部实现**（`apply` 冻结，且要独立验证）。
3. 保留 `rebuilt ⊆ affected` 作为廉价的健全检查（不是证明）。
4. 保留执行器新增的监视护栏。
5. 扩张到但没被改动的对象：原样拷贝（`apply` 的现有行为，不动）。
6. 增量正确性的主判据仍是 **增量 ≡ 全量**（`knowledge_equivalent`）。

### 13.3 R04 对同一概念每次提及都出一条提案 —— 授权返工 B 波，只改 R04

主 Agent 核实 `incremental.py:338-380`：R04 把 `new_concept_candidates` 和 `concept_mentions`
拼起来逐条循环，主体键是 `[concept, source_id, concept_id 或 surface]`。
**同一个概念被提到几次，就出几条同键提案。** 真书 10 条里重了 3 条，
`proposal_key` 唯一性检查以 `ID_002` 拒收——**这条检查是对的，它抓到了一个真 bug。**

不能简单"按键去重、留第一条"：`_concept_basis`（:682）哈希的是名称、别名、规则哈希、概念号。
普通提及和带别名的新概念候选指向同一概念时，键相同**内容却不同**，随手丢一条会丢信息。

裁定：
1. R04 必须**先按主体键分组，每组只出一条提案**。
2. 组内：别名取并集，规则哈希取并集；名称必须一致——**同一 `concept_id` 下名称不一致**
   是真实的数据冲突，fail-closed 并给专门的 message，不许静默挑一个。
3. `basis_sha256` 按组聚合后的内容计算。
4. **不许**在 `orchestrate` 层做"按 `proposal_key` 通用去重"——那会把其他规则将来出现的
   真冲突也一起吞掉。`ID_002` 唯一性检查对其余规则**原样保留**。
5. 只改 R04，其余规则一字不动。

### 13.4 真书没覆盖"同一本书返工"路径 —— 记为已知缺口

真书第二轮是"第二本书"语义（26 条全是新建）。"同一 `(source_id, edition_part_ids)` 的第二份 m6 包"
这条替换继承路径，真书上没有数据可跑。G 波的 `rework_replacement` 判据先用 fixture 覆盖；
真书返工要等下次对同一本书重跑 M6，记入已知缺口，**不阻断**本线。

### 13.5 其余 7 条偏差 —— 认可

`assemble` 多一个 `base_snapshot_revision_id` 关键字参数（§9.3 必需）；
`step.py` 把 `LedgerError` 纳入失败封存（修掉"异常逃出事务、留下跑着的 StepRun"的隐患，这条修得好）；
多包增量仍在前置拒收（`apply` 冻结，本线只接通单包增量，记入已知缺口）；其余口径定义合理。

---

## 14. D 波返工验收（2026-09-22）

ACT 24b 提交 `5aa4cd9`。主 Agent 独立复验：
- `assembly` 163 → **172 OK**；六个冻结模块相对 `6f28d9c` 一行未动
- `incremental.py` 的全部改动块都在 R04 段（旧 338–385 行）及其紧邻的两个专用函数，R06 起一字未动
- 主 Agent 自做探针：让 `closure_soundness_violations` 恒返回空 → **3 条用例转红**（完整仓库副本，R13）
- **真书第二轮主 Agent 亲自重跑**：零重号、增量 ≡ 全量、`run_m7` **`status=succeeded`**，正本未被改动。
  **这是真书第一次以「第二轮」端到端跑通 M7。**

### 14.1 执行器报告的残留：健全性检查只看得见"来自裁定"的改动 —— 转交 E 波

`apply` 还会因为「视图候选带着基底里已有的号」去重建基底对象，这类重建**不来自任何裁定**，
本波新加的检查看不见。现在靠闭包的「同 `(work_key, collation_key)`」准则兜住——是准则保的，不是检查保的。

这在**真书「同一本书返工」**时是真风险：真书的 `collation_key` 全是 null（§8.2），
闭包准则可能兜不住带基底号的候选，于是可能又落回 §13.2 那个「改动被旧版静默覆盖」的洞。

**E 波独立 Gate 必须加一条行为判据**：比对 `apply` **实际改动的对象集**与 `affected`，
实际改动 ⊄ `affected` 即 FAIL。不许只从裁定推导（那是本波已做的），要看实际发生了什么。

---

## 15. E 波的四处校准（2026-09-22）

正文在 `act/25.yaml` 第一节。起草时实测发现一件要紧的事：

**增量路径现在不过任何 Gate。** `step.py:215` 写的是 `"incremental_gate": "pending_e_wave"`，
只有创世路径调 `evaluate_genesis`。所以 §14 里真书第二轮的 `status=succeeded`
**没有经过独立检查**。标注是老实的（写明了等 E 波），不算假绿；但在 E 波落地之前，
**这个 `succeeded` 不能当作"真书第二轮通过"来引用**。

四处校准：场景改为 r1→r2 与真书第二轮（fixture 里没有草稿说的 s1/s2/s3）；
`affected_scope_exact` 去掉 rebuilt 等于 affected 的等式（§13.2）；
为 §14.1 的静默覆盖点名加篡改用例；配对隔离从结果上做行为验证（§10.1）。
Gate 独立性的禁止导入清单**加上 `orchestrate`**。

---

## 16. E 波验收（2026-09-22）

ACT 25 提交 `48ed44c`。主 Agent 独立复验：
- `assembly` 172 → **197 OK**；真书用例 `test_real_book_second_round_all_checks_pass` **实际运行（ok，非 skip）**
- `gate.py` 只导入 `canonical`、`model`、`pipeline.ledger.ids` 与标准库，无 matcher/apply/incremental/orchestrate
- `pending_e_wave` 已从 `step.py` 删除；七个冻结模块未动；`evaluate_genesis` 行为未改
- 主 Agent 自做探针：让 `_asm_has_pairing_basis` 恒返回 True → **精确命中** `test_tamper_relation_without_deterministic_basis`

**真书第二轮 13 项独立检查全部通过。** §15 里说"没经过独立检查、不能当通过引用"的那个 `succeeded`，
现在经得起检查了。执行器动手前先用原型验证了 Gate 能只凭输入独立算出同样的闭包（fixture 与真书都相等），
没有照搬被验对象的实现。

### 16.1 留给 G 波的两件事

1. **fixture `snapshot_r2.json` 金标已经过时**：它没有 `meta`、包身份是旧的，
   跟现在增量路径的产出不是字节等价的（§8.4 当时只要求重建 r1）。
   E 波没改金标、只判"13 项全过"，做法正确。G 波须**重建 r2 金标**（与 r1 同法：由实跑产出、不手写），
   并恢复"增量产出与金标逐字节相同"这条判据。
2. **`identity_delta_contract` 口径被迫放宽**：草稿要求 delta 的 `reason_ref.proposal_key` 必须出现在
   **本轮提案**里，但 `report` 没记本轮提案键，执行器只能退而对照「总账里已落地的键 ∪ 决定 ∪ 沿用」。
   G 波须让 `report` 记下本轮提案键，Gate 改回按草稿口径检查。

---

## 17. G1 波：fixture 怎么补（2026-09-22）

正文在 `act/26.yaml` 第一节。起草时实测：fixture 只有 `ed01`、`ed99` 两个版次，
**没有「同一本书返工」场景**（`act/09` 草稿假设的 `ed01r2` 不存在），所以替换继承与身份迁移在 fixture 上都没覆盖；
对勘单元两侧只共有 `sanche-0001`，**产生不了缺文 / 增文**。

裁定：重建过时的 r2 金标；在 ed99 上声明缺失单元以产生缺文，补齐对勘四类；新增 `ed01r2`
（同 `(source_id, edition_part_ids)`，删一条断言、合并两个概念）覆盖 retired / merged / carried。
**金标一律由实跑产出，不许手写。** `report` 新增 `round_proposal_keys`，Gate 的 `identity_delta_contract` 回到草稿口径。

## 18. G2 波：写死的 BLOCKED 改为真实判定（2026-09-22）

正文在 `act/27.yaml` 第一节。`m7-assembler.sh` 现有 5 条 BLOCKED 的理由全是「未实现」，
而 B/C/D/E 四波已经实现了它们——理由写死、与事实不符。`run_all.sh` 20.5 同样写死。

主 Agent 核实规格 §15:655 后定口径：它说的是「新版次加入同一部书时，不等全部版次到齐，来一个汇一个」，
ed99 汇入 r1 正是这个场景，**已经做到**，可以如实转 PASS。「单个 Run 一次汇多个包」仍在前置拒收，
但那不是 §15:655 的要求，不算进这条判据。

真书路径新增独立判据 `upstream_m6_real_book`（副本上跑、正本只读、无账本时 BLOCKED 不许 PASS）；
原 `upstream_m6_real` 保留，但 detail 写明「输入为合成桩」，消除名实不符。

---

## 19. G1 波停手：引擎有六处跑不通（2026-09-22）

G1 执行器造 fixture 时发现，ACT 26 要造的场景在 `apply.py`（冻结）里根本跑不出来。
它写了只读探针 `pipeline/assembly/tests/probe_g_blockers.py`（提交 `1595e73`），**主 Agent 亲自复现 6/6**。

| # | 现象 | 位置 |
|---|---|---|
| F1 | **同一本书返工**：只要视图的 `source_id` 已在基底里就拒收，与提案、决定全无关 | `apply.py:468-471` |
| F2 | 缺文（Omission）：R09 不写 `targets`，`apply` 要求两侧各一条断言，缺侧按定义没有 → 拒收 | `apply.py:1225`、`incremental.py:441-446` |
| F3 | 增文（Addition）原理上不可达：Snapshot 断言没有承载「旧版声明缺失」的字段；同 source 时还会把缺文错判成增文 | `incremental.py:441` |
| F4 | 异文（VariantReading）：R08 要求同号异文，`apply` 要求同号同命题，两条约束互斥 | `incremental.py:456`、`apply.py:798` |
| F5 | 退役：IdentityDelta 的 `proposal_key` 写死成字面量 `"retire"`，不在任何提案集里 → Gate 恒红 | `apply.py:1131` |
| F6 | 合并（merged）没有任何产出路径：`merge_entities` 显式拒收 | `apply.py:307-314` |

### 19.1 这是怎么漏过去的

C 波在 `apply.py` 留了拒收护栏，注释明写「属 D 波编排」，D、E 两波都没拆。
197 个用例全绿，是因为**没有一条用例用真实输入把「同书返工」走完全程**——
相关用例都是手工构造提案驱动的（`test_apply.py:451` 的注释自己就写了）。
主 Agent 验收 C、D 波时只核对了 ACT 自己的用例，也没抓到。

这是本线第四次「测试绿、真路径不通」（前三次：M8 输入解析、`patch_reversible`、`upstream_m6_real`）。

**立纪律 R15**：每一波的验收，必须至少有一条用例**用真实形状的输入、走完从视图到 Snapshot 的全栈**；
手工构造提案驱动的单测只能证明函数正确，**不能证明路径可达**。主 Agent 验收时要专门查这一条。

### 19.2 裁定：按「单本书投产是否必需」分两类

**必须修（新开 H 波，`act/28.yaml`，授权改 `apply.py`）**：
- **F1 同书返工**：这是做增量的首要理由——审核结论改了、同一本书重跑，改动要能传进总账。
  不修，M6 的任何纠错都无法反映到已汇编的书里。拆掉护栏，让同 `(source_id, edition_part_ids)` 的替换
  真正走完 `apply`：`editions[]` 合并且不新增条目、继承基底的 `reviewed_edition_*` 身份。
- **F5 退役键**：`apply._apply_retire` 写 R11 提案的真实 `proposal_key`，删掉字面量 `"retire"`。
  执行器建议的另一条路（在 Gate 里放行字面量）等于放宽判据，**否决**。
- **F6 合并**：执行器指出矛盾在于「旧号退役后还要写 `merged_into(旧, 新)` 关系，而关系要求两端都存活」。
  裁定：**合并只记在 IdentityDelta 里**（`change_type=merged`，`from=旧号`，`to=[新号]`），**不写 `merged_into` 关系**。
  理由：规格 §16:732 规定身份变化的载体就是 IdentityMigrationMap，关系表不该承载已退役对象。

**降级为已知缺口（另开 I 波，本批不做）**：
- **F2 / F3 / F4 多版次对勘（缺文、增文、异文）**：只在**同一部书有多个版次**时才需要。
  现在真实语料是一部书一个版次，不影响单本书投产。F3 还需要给 Snapshot 加字段（改 schema），
  F4 需要先定异文的正规形状，都不是小修。
  `m7-assembler.sh` 的 `edition_collation` 判据如实给 BLOCKED，理由写
  「多版次对勘（缺文/增文/异文）引擎缺口，见 CHARTER §19」，**不许写「未实现」这种笼统说法，也不许判 PASS**。
  对齐（Alignment）是通的，fixture 覆盖它。

### 19.3 执行器顺带问的两个口径

1. **逐字节比对与随机修订号**：`meta.base_snapshot_revision_id` 在 Ledger 路径上是每轮新发的随机号。
   裁定：逐字节比对放在**纯函数层**（`orchestrate.assemble`，固定基底号）做；Ledger 层比对
   「除 `meta` 外逐字节相同，且 `meta.base_snapshot_revision_id` 等于本轮实际基底修订号」。
   这不是放宽，是检查对的东西：基底号本来就该随轮次变。
2. **返工场景的决定集**：ed01r2 会带出 R04 别名、R06 冲突两条人工提案。
   裁定：决定集作为 fixture 数据由 `build_fixture.py` 写出（显式、进版本库），代表一次审核人的选择。

### 19.4 批次重排

- **ACT 26 缩范围**：只做一.1（重建 r2 金标）与二（`report` 记本轮提案键）。
  一.2 改为只覆盖对齐；一.3（ed01r2）与三（Gate 回到草稿口径）移到 ACT 28。
- **ACT 28（H 波，新）**：修 F1、F5、F6 → 造 ed01r2 与 r3 金标 → Gate 回到草稿口径。
- **ACT 27（G2）**：放到 ACT 28 之后；`edition_collation` 按 19.2 如实 BLOCKED。
- 派发顺序：**26（缩）→ 28 → 27**。

---

## 20. G1 波（缩范围后）验收（2026-09-22）

ACT 26 提交 `c7e4084`。主 Agent 把该提交单独导出到临时目录复验（工作树上有 H 波的进行中改动，不在上面测）：
- `assembly` 197 → **200 OK**；`verify.sh` 通过；`build_fixture.py --check` 重跑生成与盘上金标**逐字节一致**（10 个文件，0 不符）——金标确由实跑产出
- 七个冻结模块（含 `gate.py`，缩范围后本 ACT 不许动它）相对 `4c020aa` 一行未动
- r2 金标新旧差异只有三类：新增 `meta`、`editions`（包身份）、`relations`（关系格式），与 ACT 26 on_fail ④ 允许的范围一致
- 主 Agent 自做探针：把 `report` 的 `round_proposal_keys` 改名 → `test_report_records_round_proposal_keys` 与键序用例**两条转红**

---

## 21. H 波第一次停手：五条裁定（2026-09-22）

H 波部分落地 `51334db`：F5 退役键改用真实提案键、Gate 的 `identity_delta_contract` 回到草稿口径，
`assembly` 200 → 202 OK，`probe_g_blockers.py` F5 转为不复现、其余照旧（没越界）。
执行器没有改任何文件，只用 monkeypatch 模拟「护栏已拆」，把 r2 → ed01r2 实际走了一遍，
逐层挖出后面挡着的问题。主 Agent 核实了三条关键说法，都属实。

### 21.1 第五次「函数有、用例绿、真路径没接线」

D 波写了 `orchestrate.carry_forward_proposals`（D-14 替换继承：视图仍声明的对象不得被 R11 退役），
还有一条通过的用例钉住口径（`test_incremental_orchestration.py:478`）。
**但全仓库只有测试在调它，`assemble` 里一次都没调。** 主 Agent 验收 D 波时没抓到。
后果：同书返工时 R11 把**所有**同 source 的断言都退役，连仍在视图里的也不放过。

同一类问题第五次出现，R15 已经立了，这里补一句**验收动作**：
**主 Agent 验收任何新增的公开函数，必须 `grep` 它在非测试代码里的调用点；只有测试调用的，一律当作未接线。**

### 21.2 裁定

**① R11 过度退役 —— 取 (a)：在 `orchestrate.assemble` 里接上 `carry_forward_proposals`。本波授权修改 `orchestrate.py`（只限接线与 report 字段）。**
- (b)（在 `incremental` 里再判一次）否决：会出现两套规则。
- `report.round_proposal_keys` 仍记**本轮生成过的全部提案键**（被过滤的也记，它们确实生成过）。
- `report` 新增 `dropped_proposal_keys`：被 `carry_forward_proposals` 剔除的提案键，升序。**不许静默丢弃。**
- 闭包健全性检查（§13.2）必须作用在**过滤之后**交给 `apply` 的那批裁定上。

**② F7「decided」被拒收 —— 在 `apply.validate_decision` 那一侧收口（`apply.py`，授权范围内）。**
- `"decided"` 是规格口径（`act/03.yaml:26`：已有合法决定的提案），`incremental` 那边不改。
- `validate_decision` 接受 `{human, blocked, decided}`；但 `decided` **必须**真的有一条合法决定对应，
  决定的 choice 仍须在提案 options 内。`decided` 却找不到决定 → 拒收。`auto` 带决定 → 仍拒收。

**③ 既有用例依赖 `merged_into` —— 授权改写 `test_apply.py:654` 这一条。**
改成两侧：「合并只记 IdentityDelta、不写关系 → 通过」「若写了 `merged_into` 指向退役号 → REF_001 拒收」。
`apply.py:19-23` 的模块说明同步改为新口径。关系种类常量里的 `merged_into` 保留（不删死分支，免得牵动 canonical/gate）。

**④ 合并的对象与方向**
- 取 (i)：fixture 改为**两个 Pattern 经 R03d 裁定合并**（`entity_kind=pattern`）。Concept 合并不做，记入已知缺口；
  给 R04 加合并分支（ii）要动 `incremental.py`，否决。
- **方向**：两个号里**较小的号存活**（`to`），较大的号退役（`from`）。理由：较早分配的号更可能已被注解锚定，
  保留它对 §16:732 的锚点可迁移率最友好；且规则确定、不依赖决定里的列表顺序。
- **引用处理**：与 `split` 同口径——退役号若被任何活对象引用（`_referenced_by` 非空），**fail-closed 停手**，
  不自动改指。fixture 选两个未被引用的 Pattern；选不出就停手上报。

**⑤ 删断言时 —— 同时删掉该单元的 `collation_units` 声明。**
视图声明的是「本版包含哪些单元」，审核人删了这条断言，本版就不再声明它。

### 21.3 顺序不变

H 波继续（接线 → F7 → 拆 F1 护栏 → F6 → 造 ed01r2 与 r3 金标 → R15 全栈用例），然后 G2。

---

## 22. H 波第二次停手：两条裁定（2026-09-22）

第二会话把 H 波推到了只差一步：用例 208 → 213，F1/F5/F6 在探针上不再复现、F2/F3/F4 仍然复现（没越界），
r3 金标重跑逐字节一致，真书第二轮没被改坏。**唯一的红是 R15 全栈用例**：
同书返工那一轮在纯函数层成功、与 r3 金标逐字节相同，到 Ledger 层却被 Gate 的 `decisions_consistent` 拒了。
执行器没有自己去改 Gate，停手上报——按 ACT 28 第八节的禁令，这是对的。

### 22.1 A：`decisions_consistent` 看不见身份变更记录 —— 授权修 Gate

根因：§21④ 把合并的落点定在 IdentityDelta、不写 `merged_into` 关系；
可 E 波的 `_asm_check_decisions_consistent` 只在 `relations` 与 `conflict_groups` 里找「决定的落点」，
签名里根本没有 identity_delta。所以**任何合并、拆分决定都恒不能通过**。
这是**第六次**「判据写在裁定之前、裁定改了判据没跟上」——这次的裁定是主 Agent 自己下的。

这**不是放宽**：检查强度两侧都保留，只是把裁定指定的载体补进来。授权改 `gate.py`，口径写严：
1. 决定的落点新增 IdentityDelta：一条 `merge_entities` 决定，**必须**恰有一条 `change_type=merged`、
   `reason_ref.proposal_key` 等于该决定提案键的 delta；`split` 决定对应 `change_type=split`。选项与类型对不上 → FAIL。
2. 反向：IdentityDelta 里每条 `merged` / `split` 都必须对应一条决定；没有决定就出现 → FAIL。
   `retired` 来自 R11 自动提案，不要求决定（沿用 `identity_delta_contract` 已验的提案键）。
3. 新增篡改用例：`test_tamper_merge_decision_without_delta`、`test_tamper_merged_delta_without_decision`、
   `test_tamper_delta_change_type_mismatches_decision`。

### 22.2 B：基底关系被静默删掉 —— 分三种情况

执行器查明：`_referenced_by` 只看本轮已写入的关系，看不见基底里的关系；最后重建关系表时，
指向退役号的基底关系被**静默删掉**。它这次删的是被合并的两个 Pattern 之间的 `distinct_from`，删对了；
但同一条路径也会静默删掉第三方对象的引用，那就是断链。

裁定（三个选项都不完全对）：
1. **合并双方彼此之间的关系**（两端都在 `{from, to}` 内）：随合并作废，删除，**记进 report**。
2. **第三方活对象指向将退役号的关系**（基底 ∪ 本轮）：按 §21④ **fail-closed 停手**，不自动改指。
   `_referenced_by` 改为同时看基底关系。
3. **R11 退役断言时指向它的关系**：随退役作废，删除，**记进 report**。
   （这里不停手：删掉的断言带着关系是返工的常态，停手等于返工永远跑不通。
   规格 §16:732 对 retired 本来就是「转为孤儿并记录」。）
- `apply` 的 report 新增 `dropped_relations`：`[{relation_key, reason: "merge_internal" | "endpoint_retired"}]`，按 `relation_key` 升序；
  `orchestrate` 的 report 透传这个字段。**静默删除一律不许。**
- 本 fixture 的两个合并目标之间只有那条 `distinct_from`，归第 1 种；`pat_qizheng_900001` 是存活方，
  它身上的 `attached` 不受影响——**fixture 不必重选**。若按新口径实跑发现须重选，停手上报。
- 新增用例：`test_merge_internal_relation_dropped_and_reported`、`test_third_party_reference_to_merged_id_refuses`、
  `test_retire_drops_relations_and_reports`。

### 22.3 其余

- Red 证据：实现已在上一会话落盘，无法再先红后绿，执行器改用整仓副本加回护栏来重现转红——**认可**。
- `_id_allocation` 在「最大号被退役」时的两难：记入已知缺口（真书当前无 Pattern 获批，不触发）。
- r2 金标因 ed99 加了两个 Pattern 而变了四个字段，执行器已逐项说明——**认可**。
- 授权范围：`gate.py`（仅 `_asm_check_decisions_consistent` 及其在 `evaluate_assembly` 里的调用）、
  `apply.py`（`_referenced_by` 与 report 字段）、`orchestrate.py`（透传 report 字段）。其余不变。

---

## 23. H 波验收（2026-09-22）

ACT 28 提交 `79bcbe7`（28 个文件）。主 Agent 把该提交单独导出复验（工作树上有 G2 的进行中改动）：
- `assembly` 200 → **220 OK**，无新增 skip
- **R15 全栈用例 `test_rework_ed01r2_end_to_end_through_run_m7` 通过**：临时 Ledger 上 r1 → ed99 → ed01r2 三轮 `run_m7`，
  不手工构造任何提案。**「同一本书改一版」第一次在真实路径上走通。**
- `probe_g_blockers.py`：F1/F5/F6 不再复现，F2/F3/F4 仍复现——修了该修的，没碰 I 波的
- fixture 重跑生成与金标逐字节一致；`verify.sh` 通过；只读模块（incremental/matcher/genesis/canonical/inputs）一行未动
- §21.1 的新验收动作：`carry_forward_proposals` 在非测试代码里有调用点（`orchestrate.py:608`）。
  主 Agent 自做探针拆掉这处接线 → **7 条用例转红，含 R15**。这条接线现在由真实路径用例守着。

### 23.1 两处授权外改动 —— 认可

1. `step.py` 残留的 `rebuilt == affected` 等式：§13.2 早已明令删除，D 波漏改这份副本。执行器主动上报，认可。
2. `gate._asm_closure` 补上规格替换条的另半句（被删除的对象本身入闭包）：**执行器起初没上报**，
   主 Agent 从 diff 里发现后要求补报。补报说明是按规格独立写的、没调用被验模块；
   去掉该规则 → `test_rework_round_all_checks_pass` 转红。内容正确，认可。
   这是第七次同类问题：**Gate 的独立实现漏了规格的一半**，此前没有返工场景，一直没暴露。

**给执行器的纪律补充**：改动 Gate（独立检查）的任何计算口径，无论多"显然正确"，都必须在回报里单列上报。

### 23.2 已知缺口（汇总）

- 多版次对勘：缺文 / 增文 / 异文（§19 F2/F3/F4）→ I 波
- Concept 合并（§21④，规则表不可达）
- 同 source 不同 `edition_part_ids` 的扩展（仍拒收并写明）
- `_id_allocation` 在最大号被退役时的两难（§22.3）
- 退役号被第三方引用时 fail-closed，不自动改指

---

## 24. G2 波验收与本轮收口（2026-09-22）

ACT 27 提交 `de1a802`。主 Agent 独立复验：
- `assembly` **229 OK**；其余四包 OK；被验模块与 fixture 相对 `8d43131` 零改动；真书正本 mtime/size 未变
- `m7-assembler.sh`：`pass=11 blocked=5` → **`pass=16 fail=0 blocked=1`**。唯一 BLOCKED 是 `edition_collation`，
  理由实指 §19 缺口；其内部仍先验对齐关系与不可比单元，错了判 FAIL（执行器 P4 探针证实）
- `run_all.sh 20.5` 按真实退出码映射，当前 BLOCKED，与 m7-assembler 退出码 2 一致；改动只在 20.5 段
- 执行器四条篡改探针全部转红

### 24.1 主 Agent 探针发现一处冗余防线无用例守护（不阻断）

把 `incremental_multi_edition` 判据里「增量 Gate 必须全过」那段检查整个去掉，`test_acceptance` 26 条仍全绿。
原因：Gate 不过时 `step._finish_incremental` 已把该轮判 `failed`，同一判据前面的「status 必须 succeeded」先抓到了。
所以这段是**重复的第二道防线**，今天去掉不会放过坏结果；但若将来有人拆掉 `step.py` 的失败封存，这道防线失效也不会被发现。
记入待办：补一条用例，喂一个 `status=succeeded` 但 Gate 未过的伪造 validation，断言该判据 FAIL。

### 24.2 收口

本轮 M7 增量汇编收口。三条真实路径——创世、新书加入、同一本书改一版——都有全栈验证。
`PLAN.md:94` **不打勾**：它的判据是 20.5 PASS，仍被多版次对勘缺口（§19 F2/F3/F4）挡住，留给 I 波。
已知缺口汇总见 §23.2。
