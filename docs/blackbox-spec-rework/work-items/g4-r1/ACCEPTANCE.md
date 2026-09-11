# ACCEPTANCE：G4 第一批（D-13 / D-10 / D-11 / D-06 / D-08 / D-14）

状态：`ACCEPTED`（2026-09-10；六个提交 `4086c2c` D-13、`015e34f` D-10、`3598ea8` D-11、`e474ae4` D-06、`07f79dd` D-08、`d36a202` D-14，由用户交外部 Agent 在主工作树串行完成，主 Agent 独立验收通过；D-14 §22 分期与 D-08 前缀仍待用户确认）

## 验收实得（主 Agent，HEAD `d36a202`，`LC_ALL=en_US.UTF-8`）

- **范围**：六个提交各只含 `openspec/learn-system-blackbox-architecture.md`（D-14 另含 `LEARN_SYSTEM_TARGET.md`）；`git diff --check 8ebadac HEAD` 通过；删除行仅为 ACT 指定的替换目标（§6.2 两行、§14 一句、§19 表头/分隔/19 行改写为五列）。
- **门禁**：`verify-T.sh` `FAIL 合计: 0`、`PASS  G3-` 12、T-04s/T-06s/T-11/T-13 34 行全 PASS；`mutations.sh all` `109/109 rejected`，无 not-rejected/NOT_APPLIED；`openspec/schemas/verify.sh` exit 0；`LC_ALL=C` 下仅既有 `T-06s` 环境误报。
- **判据**：TDD §1 共 26 条，25 条符合；`锚点迁移关系 ≥2` 实得 1，系主 Agent 期望值写错（ACT 文本中该词只在 §18 一行出现），非执行缺陷，TDD 已加注。
- **逐字核对**：脚本抽取六个 ACT 的全部块标量与单行字段共 75 行，逐行 `grep -Fxc` 均恰 1（`状态：讨论候选` 因其他章节同文出现 5 次属预期；D-06 的 KnowledgeGraph 行已按 D-08 改为 SchoolView 版本且旧版残留 0）；§19 的 19 个数据行 `-`/`+` 去掉行尾标签后逐一配对，既有单元格字节未变。
- **语义审查**：通读 243 行 diff，插入位置、空行、代码围栏、表格与 ACT 一致；§3–§18 `状态：` 行映射与合并前相同；§22 首非空行 `状态：讨论候选`；两个新块位于 TP 冻结区之前且仅隔一个空行；D-08 未自造前缀，占位句存在。
- **备注**：六个规格提交未附 `Co-Authored-By` 署名（外部 Agent 执行，Prompt 未要求），不构成验收项。

## 0. 转译审查（原规划者四查，2026-09-10）

- 忠实性：六个 ACT 逐一对应 `D-design.md` 六条与 `SUBAGENT_TODO.md` G4 节 BACKLOG 项；主 Agent 在 README「决定记录」写死了 D-design 留给实现者的裁量点（D-13 归属、D-10 阈值、D-11 对象关系、D-06 等级与四类、D-08 逻辑分包与前缀占位、D-14 四行取舍）；验收标准（`verify-T.sh`、`mutations.sh`、`schemas/verify.sh`）未被改动。
- 覆盖性：BDD §2–§7 每条对应 TDD §1 的 Red/Green 判据；失败路径 BDD §8 由停手规则与回归门禁覆盖；G3 冻结区域由 `mutations.sh all` 109/109 保护。
- 可执行性：写路径存在；锚点全部是 HEAD `e64f2a4` 的整行文本（主 Agent 已逐一 `grep -Fxc` 为 1，见下）；验证命令只用 bash/awk/sed/grep；无模糊词；单 ACT 30–60 分钟。
- 独立性：A/B/C 写入章节两两不相交（§6.2/§14/§17 ｜ §12.2/§16 前部/§18/§20 ｜ §19/§22/TARGET）；组内 ACT 声明 `depends_on`；三组在独立 worktree 上工作，由主 Agent 串行合并。

锚点核对（`grep -Fxc`，HEAD `e64f2a4`）：16 处锚点各恰 1 次；§19 表头与注之间恰 20 行 `|` 行；19 个数据行首列与 `act/d14.yaml` 的 `labels` 键逐一对应；Red 值 SchoolView 2 / AnchorContractPack 1 / StageCheckpoint 1 / 待用户确认 0 / TARGET §22 0，与 TDD §1 一致。审查中修正两处计数（d13 期望 3；d08 ≥5 / ≥1）。结论：READY，6 个 ACT 可开工。

## 1. 合并与范围核对

对每组分支：

```bash
git log --oneline e64f2a4..<branch>                 # 提交数 = ACT 数
git diff --name-only e64f2a4 <branch>               # 只含允许文件
git diff --check e64f2a4 <branch>
git merge --no-ff <branch>                          # 顺序 A → B → C
```

每次合并后在主工作树重跑：`verify-T.sh`（0 FAIL，`PASS  G3-` 12）、`mutations.sh all`（109/109）、`schemas/verify.sh`（0）、`git diff --check`。

## 2. 机器判据（合并后）

| ACT | 判据 | 期望 | 实得 |
|---|---|---|---|
| d13 | §6.2 范围内 `Review Console（M7 模式）\|M7 回流` | 3 | |
| d10 | `^### 14.1`；`carried_forward\|ReworkImpactReport`；旧句 | 1；≥4；0 | |
| d11 | `^### 17.1`；`StageCheckpoint` | 1；≥6 | |
| d06 | 树行；`AnchorContractPack\|IdentityMigrationMap`；§20 第 11 条；锚点迁移关系 | 1；≥8；1；≥2 | |
| d08 | 列表行；`SchoolView\|changes_current_judgment`；`SchoolViewPack`；树无 SchoolViewPack | 1；≥5；≥1；0 | |
| d14 | §19 标注行 19；首纵切内 4；首纵切后 9；暂缓 6；§22 标题 1；§22 状态；TARGET §22 引用 1 | 见左 | |

## 3. 语义审查（主 Agent 逐句）

- 每个 `text_*` 字段逐字落实，无改写、无遗漏、无多余段落；
- `git diff` 只含 ACT 指定的插入与替换；
- §3–§18 的 `状态：` 行未动；§22 状态为 `讨论候选`；
- D-08 未自造前缀；D-06/D-08 新块位于 TP START 之前；
- D-14 §19 既有单元格字节不变（`git diff` 中每个数据行的差异仅为行尾 ` | <标签>`）。

## 4. 矩阵外抽查（主 Agent）

- 对合并后规格跑 `mutations.sh all` 并另做 ≥3 例临时副本变异（删除 §14.1 一条 bullet、把 §20 第 11 条改为第 12 条、把 §19 某行标签改为非法值）确认 TDD §1 判据能区分。

## 5. 结论

通过条件：三组合并后全部门禁绿；机器判据全部符合；语义审查无偏差；提交只含允许文件。通过后主 Agent 更新 `SUBAGENT_TODO.md` G4 节六项为 `ACCEPTED`（D-14 标 `ACCEPTED_PENDING_USER_REVIEW`，§22 待用户过目）、`PLAN.md`、`HANDOFF.md`。
