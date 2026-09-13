# G7 黑箱剩余工作分波计划（Dataset 会话）

更新时间：2026-09-12
执行方式：tmux + `cmd --yolo`，模型 `deepseek/deepseek-v4.1-flash`（用户 2026-09-12 指令；W1 期间用 agy，额度不稳后切换，监控用 `tmux-watch.sh --agent cmd`），**同时最多 2～3 路**；主 Agent 只写裁决、只读报告文件与待裁决表，验收用脚本在 `git archive` 干净树上跑。裁决见 `G7-RULINGS.md`。

## 0. 现状

- 已验收：impl-01 Artifact Ledger；impl-02 M3 结构层（J3 `c5f744c`、ACT 06 `eee3c35`）；impl-00 act/10 INTERFACES §4 闭集登记（`ea90ca8`）；impl-03 M5 首切片（K2 `6e21038`、CLI 返工 `8367893`）。impl-04 M8 首切片 K1/K2/ACT 07 已验收，ACT 08（`950b77b`，run_all 20.4/20.8）验收中。`m3-coverage.sh`、`m5-evidence-gate.sh`、`m8-span-identity.sh` 均 exit 2；`run_all.sh` `pass=2 fail=1 blocked=8`。
- 草稿：impl-05～10 仍为 `DRAFT`（impl-08 已定稿 `cd6c7a6` 待四查），按 `G7-RULINGS.md` 裁剪后逐包定稿、四查、实现。
- 首纵切口径（用户决定，G7-RULINGS 第 43 条）：交付 mini_ed01 上 Ledger → M3 → M5 → M8 可跑通证据链；§20.3/20.4/20.8 可判，§20.1/§20.9 如实 BLOCKED（M4/M6 未接入、GraphProjectionPack 未编译），不改规格 §22.3 正文。

## 1. 并行规则

1. 每路 agy 只写自己的目录；提交用 `git commit -m … -- <路径…>`，只提交自己的路径；遇 `index.lock` 等待重试，不删锁。
2. 高风险共享面（`openspec/schemas/`、`pipeline/corpus/_fixture/`、`openspec/acceptance/run_all.sh`、`pipeline/ledger/`）同一时刻只允许一路写。
3. 执行方不写台账（SUBAGENT_TODO/HANDOFF/PLAN/ACCEPTANCE），报告写 `~/tmux-agents/runs/<会话>.report.md`，有疑问写「待裁决」后停手。
4. 监控 `tmux-watch.sh --interval 60 --idle-need 3 --stall 1800`；被唤醒先读报告文件。
5. agy 额度耗尽：换 agy 内另一模型续接一次；仍不可用则暂停并告知用户，不改派批量子 Agent。
6. 注解社区线（C/S 会话）也在本工作树用 agy，派发前 `tmux ls` 计入并行数。

## 2. 分波

| 波次 | 并行路数 | 内容 | 写范围 | 出口 |
|---|---|---|---|---|
| W0 | 主 Agent | 回归门禁补录、提交 impl-02 验收记录；草稿原样提交为 DRAFT 快照 | 台账、草稿目录 | 提交 |
| W1 | 2 | **A** 补全 impl-00 接口总表与 impl-03（M5）草稿；**B** 对账审查 impl-04～10 草稿与 impl-00 的接口一致性，汇总全部待裁决项 | A：`impl-00-interfaces/`、`impl-03-validation/`；B：`reviews/G7-DRAFTS-REVIEW-R1.md` | 主 Agent 一次性裁决，写 `G7-RULINGS.md` |
| W2 | 2 | **C** 执行 impl-00 契约 ACT（新 Schema、fixture m4/m5/m8 期望产物、verify 扩展）；**D** 按裁决定稿 impl-03、impl-04 为 READY 并做 wjt-react 四查 | C：schemas + fixture（独占）；D：两个工作包目录 | 主 Agent 验收 C；D 判 READY |
| W3 | 2 | **E** impl-03 M5 实现（`ACCEPTED`）；**F** impl-04 M8 实现（K1–K3 验收收尾）。原 **G** impl-05 按用户决定（G7-RULINGS 第 43 条）移出首纵切 | `pipeline/validation/`、`pipeline/dataset_compiler/` 各自独占 | 首纵切关键路径 Ledger→M3→M5→M8 跑通；`m5-evidence-gate.sh`、`m8-span-identity.sh` exit 2；§20.1/§20.9 如实 BLOCKED |
| W4 | ≤3 | **I** impl-08 Orchestrator + Contract Registry（`ACCEPTED`，K4 `f79eafd`）；**G** impl-05 M4 最薄接入（K1–K3 `ACCEPTED`，K4 验收脚本进行中）；impl-00 前置 act/12、act/05（`ACCEPTED`） | 各自宿主目录；`run_all.sh` 单写者 | §20.1、§20.10 已计算化判定（仍 BLOCKED） |
| W5 | ≤3 | **H** impl-06 M6 最薄接入（定稿中，先于 P：M8 知识链需要 M6 正式知识）；**P** impl-04 跟进批：知识链前三段与 GraphProjectionPack 接 M6 正式知识（H 定稿后起草）；**J** impl-09 M1/M2 真实接入（前置：用户撰写真实前十页人工终态决定表，P7）；**K** impl-10 M3 语义层（前置：用户确认 SemanticSpan 前缀，P8） | 各自宿主目录 | §20.1、§20.4、§20.8、§20.9 转判；`m3-coverage.sh` exit 0 |
| W6 | 1 | **L** impl-07 M7 增量汇编（首纵切外） | `pipeline/assembly/` | §20.5 |

每一波全部验收后才开下一波；某路返工只占用该路名额。

## 3. 每波主 Agent 动作（控制 token）

1. 写一份提示词文件（`~/tmux-agents/runs/prompts/<会话>.txt`），启动 agy，挂监控。
2. 被唤醒：读报告文件 → 需要裁决的只读待裁决段 → 回复或验收。
3. 验收：`git archive` 干净树 + 预写脚本，输出只取 `tail`/SUMMARY 行；结论写 ACCEPTANCE，台账随验收一并提交。
