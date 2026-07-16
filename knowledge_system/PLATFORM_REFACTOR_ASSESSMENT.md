# 平台化重构评估与方案（技法/书目无关化）

> **目标**：把当前"能跑通两本书的脚手架"提升为"配置驱动的知识编纂平台"，让工位能力对新技法、新书目开箱即用，而非每次复制改造。
> **评估日期**：2026-07-14　**范围**：`pipeline/` 全体工位工具、模板、注册表、schema。
> **性质判断**：不是重写，是**收敛与参数化**。制度层已通用，只需收敛执行层。

---

## 一、评估结论（现状实测）

### 1.1 已立住的通用制度（可复用，勿推倒）
- **工位模型已文档化**：`knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW`（迭代到 v1.2）+ `pipeline/HANDBOOK.md`/`AGENT_GUIDE.md`/`OPERATOR_MANUAL.md`。是方法论制度，非单书笔记。
- **三层注册表**：`registry/{schools,techniques,works}/` 各带 `_TEMPLATE.yaml`。已登记 2 技法（bazi/qimen）、2 书目（穷通宝鉴/烟波钓叟歌）。
- **schema 已分层**：`schemas/{core,shared,techniques/<技法>}/`。core=技法无关字段定义，techniques/<t>/glossary_v0.yaml=技法词表（bazi 1011 行、qimen 1171 行）。配置分离的底子已具备。
- **校验器基本通用**：`check_segments/coverage/canon`、`validate_*`、`compare_drafts` 不绑书目。
- **可复用性已被第二技法验证**：奇门《烟波钓叟歌》跑通了 seg→concepts→assertions（s01-s12 已人工签发 ku_qimen_000002）。**这是"通用性成立"的最硬证据。**

### 1.2 通用性缺口（本次重构靶点）
| # | 缺口 | 实测证据 | 影响 |
|---|------|---------|------|
| **G1** | gen 工具硬编码书目/技法/源ID | 5 个 `tools/gen_*.py` 把 `qtbj`/`bazi`/`src_qtbj_ed01`/路径前缀写死（见 `gen_paraphrase_task.py:14-44`）。换书目要改代码而非传参。 | 每开新书目复制改造，易漏改、易漂移 |
| **G2** | 模板分叉成"通用版 + _bazi 版" | stage4/5 有通用版又有 `_bazi` 版（stage5 通用 45 行 vs bazi 60 行）；stage6 **只有** `stage6_paraphrase_bazi`，无通用基座、无 qimen 版。 | 工位6对奇门不可用；模板逻辑双份维护 |
| **G3** | `tasks/`(小写) 硬编码 | `gen_assertion/concept/outline` 三工具写 `tasks/`，实际产物在 `TASKS/`。当前 macOS 大小写不敏感（同 inode 112357302）侥幸未爆，**Linux/CI 上会分裂出第二套目录导致产物丢失**。 | 潜在生产事故，跨平台必炸 |
| **G4** | 5 个 gen 工具是同骨架的复制品 | 结构雷同：读 spans→按 batch 收 segments→拷模板+glossary→写 task.yaml。仅 stage 名/模板路径/task_id 模式不同。 | 一处修 bug 要改 5 处 |

### 1.3 一句话判断
高层方案**已落地且被第二技法验证**，但"技法无关抽象"只做到一半：**制度层（注册表/schema/校验器/文档）通用，执行层（gen 工具 + 模板）仍带 bazi/qtbj 硬编码**。

---

## 二、重构方案

### 原则
- 不推倒制度层；只收敛执行层。
- **配置驱动**：技法/书目差异全部下沉到 registry + schema/techniques，代码只读配置。
- **小步可回归**：每步以"重生成穷通宝鉴 + 奇门产物、与现有 `TASKS/` diff 无实质差异"为门禁。

### P0（先做，堵隐患）——修 G3 大小写
1. `gen_assertion/concept/outline` 三工具里 `tasks/` 统一改 `TASKS/`。
2. 兜底：`grep -rn '"tasks/\|f"tasks/' tools/` 必须清零。
3. 加检查：仓库不得同时存在 `tasks/` 与 `TASKS/`。
- **验证**：大小写敏感环境（或 `git ls-files` 全大写核对）确认单一目录。风险低、立竿见影、独立可先落。

### P1（核心）——G1+G4 统一 gen 工具为配置驱动
1. 抽 `tools/lib/taskgen.py` 公共库：封装"读 spans → 按 batch 收 segments → 拷模板+glossary → 写 task.yaml"骨架。
2. 参数化：书目/技法/源ID 不写死，改为从 corpus 路径推导（`corpus/<technique>/<work_ed>`）或从 `registry/works/<work>.yaml` 读 `technique_id`/`source_id`/`work_tag`。
3. 5 个 gen_*.py 瘦身为"声明 stage 名 + 调 taskgen"，task_id 命名集中成一个函数。
- **验证**：重生成穷通宝鉴 para_s1 与奇门 concepts，与现有 `TASKS/` 产物 diff 应无实质差异。

### P2（能力补齐）——G2 模板通用基座 + 技法皮
1. 定 `task-templates/<stage>/INSTRUCTIONS.base.md`（技法无关骨架：工位目标、铁律、自查、产出格式）。
2. 技法差异下沉为 `schemas/techniques/<t>/stage<N>_addendum.md`（术语约定、该技法特有铁律）。
3. gen 工具拼装：base + technique addendum → 任务包 INSTRUCTIONS.md。
4. **优先补 stage6 通用基座**（当前唯一只有 bazi 版的工位），使工位6对奇门可用。
5. 收敛 stage4/5 的通用版与 `_bazi` 版，消除双份维护。
- **验证**：新机制重生成穷通宝鉴工位6任务包，INSTRUCTIONS 与现 `stage6_paraphrase_bazi` 语义等价（人工核对铁律不丢）；再为奇门生成一个工位6任务包冒烟。

### P3（可选，固化）——防回归
1. registry 登记校验：新书目校 technique_id 存在、source_id 唯一。
2. `check_platform.py`：扫 tools/ 里白名单外的 `qtbj`/`bazi` 字面量告警。
3. HANDBOOK 增"新增技法/书目 checklist"。

### 交付顺序与粗估
P0（0.5 天）→ P1（1-2 天，最大收益）→ P2（1-2 天，补工位6通用性）→ P3（0.5 天）。P0 独立可先落。

### 不做 / 暂缓
- 不重写校验器（已通用）；不动 corpus 数据与已签发的主张/释义产物；工位9 的平台化等工位9 本身跑通后再评。

---

## 三、给执行者的一句话
先做 P0 修大小写隐患（低风险高收益）→ 再做 P1 把 5 个 gen 工具收敛成配置驱动的公共库（消除硬编码与复制）→ P2 补 stage6 通用基座让工位6对奇门可用。每步以"重生成产物与现有 `TASKS/` diff 无实质差异"为回归门禁。
