# 标识前缀登记册（ID Prefix Registry）

状态：最终规范（前缀含义与格式）；「建议」行为讨论候选
更新时间：2026-09-10
权威来源：`openspec/learn-system-blackbox-architecture.md` §8.1（格式冻结）；本文件解释每个前缀的**含义、家族、生产者与使用规则**，是新增前缀前必须查阅的唯一登记表。

## 1. 为什么要前缀

黑箱里所有对象都用带前缀的字符串做标识。前缀一眼回答三个问题：这是什么对象、它属于哪个命名空间、它是稳定身份还是一次性修订。前缀不是可选装饰：校验器按前缀判定字段合法性（§8.1 第 5 条），下游注解按前缀决定锚定与迁移规则（§16 `AnchorContractPack`）。

## 2. 两个家族

| 家族 | 形态 | 适用对象 | 发号方式 |
|---|---|---|---|
| **人工闭集家族** | `<前缀>_<命名空间>_<定长数字>` | 由人整理、数量有限、需要可读与可对照的对象（作品、概念、流派、格局） | 人工或脚本按命名空间顺序编号，定长补零 |
| **UUIDv4 家族** | `<前缀>_<32hex>` | 机器批量产生、数量不可预估、需要无状态发号的对象（制品、修订、运行、发布、流派视图、冲突组） | Python 标准库 `uuid.uuid4().hex`，全小写 32 位十六进制 |

规则：新对象先判断属于哪个家族，再取前缀；两个家族不得混用；前缀一经登记不得改写或复用于其他对象。

## 3. 前缀总表

### 3.1 既有八类（沿用，不得改动）

| 前缀 | 对象 | 格式 | 含义 | 示例 | 生产者 |
|---|---|---|---|---|---|
| `src_` | 来源 Source | `src_<work>_ed<NN>` | 某作品的某一底本版次 | `src_qtbj_ed01` | M1 |
| `ss_` | 原文片段 SourceSpan | `ss_<work>_ed<NN>_p<NNNN>_s<NN>` | 底本中一段可定位原文（页码 + 句序） | `ss_qtbj_ed01_p0012_s03` | M3 |
| `ku_` | 知识单元 KnowledgeUnit | `ku_<technique>_<6位数字>` | 某技法下一个知识单元（旧管线的工作粒度） | `ku_qimen_000002` | M4（旧管线） |
| `as_` | 主张 Assertion | `as_<technique>_<6位数字>` | 某技法下一条可验证的知识主张 | `as_bazi_000046` | M4 |
| `pr_` | 命题 Proposition | `pr_<technique>_<6位数字>` | 主张拆出的原子命题 | `pr_bazi_000101` | M4 |
| `co_shared_` | 共享概念 | `co_shared_<domain>_NN` | 跨技法共享闭集概念（天干、地支、五行…） | `co_shared_stem_01` | Contract Registry（冻结输入） |
| `co_` | 技法概念 | `co_<technique>_<6位数字>` | 只属于一个技法的概念（含同形词在该技法下的义项） | `co_qizheng_000042` | M4 术语判层 |
| `hg_` | 同形字面锚 | `hg_<4位数字>` | 跨技法同形异义词的字面共享锚 | `hg_0042` | Contract Registry |

### 3.2 新对象六类（用户 2026-09-09 确认）

| 前缀 | 对象 | 格式 | 含义 | 生产者 |
|---|---|---|---|---|
| `art_` | Artifact 逻辑身份 | `art_<32hex>` | 一个制品跨修订不变的身份 | Artifact Ledger |
| `rev_` | Artifact Revision | `rev_<32hex>` | 制品的一次不可变物理修订；任何内容变化都换新号 | Artifact Ledger |
| `prun_` | ProcessingRun | `prun_<32hex>` | 一次批处理运行（EditionRun / ReleaseRun）。**不用 `pr_`**，避免与命题冲突 | Local Orchestrator |
| `srun_` | StepRun | `srun_<32hex>` | 运行中的一次单步执行；重跑必换新号 | Local Orchestrator |
| `pkg_` | StagePackage 逻辑身份 | `pkg_<stage>_<32hex>`，`<stage>` ∈ `m1`…`m8` | 某阶段产出的包的逻辑身份；每个版本另有 `rev_` | 各 Module |
| `rel_` | Release | `rel_<32hex>` | 一次正式发布 | M8 |

### 3.3 流派与视图三类（用户 2026-09-10 确认）

| 前缀 | 对象 | 格式 | 含义 | 家族 | 生产者 | 对应规格 |
|---|---|---|---|---|---|---|
| `sch_` | 流派 School | `sch_<technique>_<3位数字>` | 某技法下一个流派的稳定身份；按技法命名空间，同名流派在不同技法下是不同对象 | 人工闭集 | Contract Registry 登记；M4 只能引用已登记值 | §12.2 `SchoolView.school_id`、§13 G4 `school_ids` |
| `sv_` | 流派视图 SchoolView | `sv_<32hex>` | 某流派对某 Pattern / Concept / Assertion 的一条立场（主张归属、是否改变当前判断） | UUIDv4 | M4 候选、`review_school_attribution` 审核后正式 | §12.2 `SchoolView`、§16 `SchoolViewPack` |
| `cg_` | 冲突组 ConflictGroup | `cg_<32hex>` | 同一主题下相互冲突的一组 SchoolView 共享的分组标识 | UUIDv4 | M4 / M7 | §12.2 `conflict_group_id` |

`sch_` 编号规则：每个技法从 `001` 起顺序编号，编号不复用；流派更名只改显示名不改号；旧工作台 slug（`qin_tang`、`tian_guan`）作为别名保留在 Concept 别名字段，`guo_lao` 在旧表中类型为 book，不是流派，迁移时剔除。七政首批：`sch_qizheng_001` 琴堂派、`sch_qizheng_002` 天官派（正式登记随 M4 首次抽取时冻结）。

### 3.4 建议（讨论候选，尚未确认）

| 前缀 | 对象 | 建议格式 | 含义 | 家族 | 备注 |
|---|---|---|---|---|---|
| `pat_` | Pattern 格局 | `pat_<technique>_<6位数字>` | 某技法下一个可规则识别的格局 | 人工闭集 | §4 已有字段名 `pattern_id`，格式未登记 |
| `ent_` | KnowledgeEntry 发布词条 | `ent_<32hex>` | M8 编译出的发布视图词条 | UUIDv4 | §4 已有字段名 `entry_id`，格式未登记；建议在 M8 工作包前确认 |

## 4. 使用规则

1. **只引用已登记前缀**。规格、Schema、代码出现未登记前缀，校验器判非法（§8.1 第 5 条）。
2. **稳定身份 vs 修订**：`art_`/`pkg_`/`sch_`/`sv_`/`cg_`/`co_`/`as_` 等都是跨修订稳定的 `entity_id` 语义；内容变化用 `rev_` 表达，不换身份号。
3. **退役与迁移**：对象删除后号码永久退役；合并、拆分产生新号，旧号到新号的关系写入 `IdentityMigrationMap`（§16）。
4. **新增前缀的流程**：先在本文件 §3 增行并写清含义、家族、生产者，再由工作包把格式登记进规格 §8.1，最后才允许 Schema 与代码使用。
5. **冲突检查**：新增前缀前用 `git grep -c '\`<前缀>'` 确认仓库内未被使用；本次 `sch_`、`sv_`、`cg_` 检查结果均为 0。

## 5. 待办

- [x] 把 §3.3 三行登记进规格 §8.1「新对象标识格式」表（已由 `work-items/g4-r2/act/r2-01.yaml` 完成，规格 §8.1 第 3b 节）。
- [ ] 用户确认 §3.4 两行后移入 §3.3 并登记。
