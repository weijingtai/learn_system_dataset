# ACCEPTANCE：G4 第一批（D-13 / D-10 / D-11 / D-06 / D-08 / D-14）

状态：`DISPATCHED`（2026-09-10，三组并行，各自 worktree）

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
