# G7 DRAFTS REVIEW R1

生成时间：2026-09-12

## 1. 完整度表
| 包 | 文件数 | ACT 数 | 截断情况 |
|---|---|---|---|
| impl-04-dataset | 9 | 5 | 无 |
| impl-05-knowledge | 13 | 9 | 无 |
| impl-06-review | 15 | 11 | 无 |
| impl-07-assembly | 13 | 9 | 无 |
| impl-08-orchestrator | 14 | 10 | 无 |
| impl-09-intake | 11 | 7 | 无 |
| impl-10-corpus-semantic | 11 | 7 | 无 |

## 2. 接口对账表（参照 impl-00/INTERFACES.md 闭集）
| 生产者 | 消费者 | 不一致描述 |
|---|---|---|
| impl-09 (M1/M2) | Ledger | 新增了闭集外类型：`source_asset`, `ocr_anomaly_log`, `ocr_audit_log`, `ocr_edit_history` |
| impl-10 (M3) | Ledger/M4 | 新增了闭集外类型：`semantic_windows`, `model_request` 等 8 项 |
| impl-05 (M4) | Ledger | 新增了闭集外类型：`candidate_submission`, `candidate_lane_set` 等 |
| impl-07 (M7) | Ledger | 拟新增 `release_policy` |
| 各包 | Orchestrator | 未统一使用 Contract Registry 加载 Schema，绕过统一接入 |

## 3. 冲突提议
1. **新增 artifact_type 冲突**：impl-05, impl-07, impl-09, impl-10 均试图绕过 `INTERFACES.md` §4 的临时闭集，各自分配新类型名。此举违反了 G7-PLAN §1 规则 2（共享面独占，Ledger 拦截规则只有一路能写）。
2. **验收脚本修改冲突**：impl-07, impl-08, impl-10 均提议修改 `run_all.sh` 及相关 `m3-coverage.sh`，存在文件写入与判定逻辑冲突。
3. **架构边界重叠**：impl-06 和 impl-07 在争夺对 Snapshot 与 `ReviewedEditionPackage` 的所有权。

## 4. 依赖与分波核对
- **违反分波**：各包部分 ACT（如 impl-07 的创世汇编）尝试调整先后顺序交付，可能打乱 G7-PLAN 串并行批次。
- **未规划能力**：impl-09 提出了 OCR 模型旁路挂载、本地日志文件的跟踪要求，依赖额外的外部状态文件。

## 5. 统一待裁决表 (节选 P0 阻塞项)
| 编号 | 来源包 | 问题 | 选项 | 草稿推荐 | 建议 | 规格行号 | 优先级 |
|---|---|---|---|---|---|---|---|
| G7-Q01 | impl-05 | 候选提交件如何登记为 Ledger 冻结修订 | A: 立即封存 / B: 缓冲 | A | A | - | P0 |
| G7-Q02 | impl-06 | 新增 artifact_type 与候选包验证 | A: 临时闭集 / B: 新 schema | A | A | - | P0 |
| G7-Q03 | impl-07 | Snapshot 的粒度与身份归属 | A: M7 发号 / B: M8 | A | A | - | P0 |
| G7-Q04 | impl-09 | 新 artifact_type 绕过临时闭集 | A: 统一登记 / B: 各自分配 | A | A | - | P0 |
| G7-Q05 | impl-10 | 真实模型调用开关与 Adapter 归属 | A: 只读回放 / B: 真实调用 | A | A | - | P0 |

## 6. 下游约束检查
各包消费上游 StagePackage 是否写明「只接受 StepRun succeeded 的包」：
- impl-04-dataset (M8): ✅ 满足
- impl-05-knowledge (M4): ✅ 满足
- impl-06-review (M6): ✅ 满足
- impl-08-orchestrator: ✅ 满足 (提取为有效 succeeded StepRun)
- impl-09-intake (M2): ✅ 满足 (M1 约束)
- impl-10-corpus-semantic (M3): ✅ 满足 (M2 约束)
- **impl-07-assembly (M7)**: ❌ 缺失明确声明消费上游必须 succeeded (仅提到了自身的写入限制)
