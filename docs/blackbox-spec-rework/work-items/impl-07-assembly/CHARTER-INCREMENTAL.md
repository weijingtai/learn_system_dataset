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
| P2 | 「`m7-assembler.sh` 固定保留一行 `BLOCKED upstream_m6_real`，只能返回 2」（§1.2） | G0-06 已把该项做成**可转判 PASS** 的路径；当前实跑 `pass=11 fail=0 blocked=5` | D-13 的前提松动，接线条件要重判 |
| P3 | ACT 02「包骨架 + 规范化 + ReviewedEdition 视图」待建 | **g0-01 已建**（`canonical.py` / `model.py` / `genesis.py` / `gate.py` / `inputs.py` 均在库），W8 8.5（act/11）又补了 `evidence_level` / `corpus_spans_revision_id` | ACT 02 **不能照原样派发**，须改为「在既有骨架上扩增量」 |

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
