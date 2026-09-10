# T-03 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示以下 3 项失败，且全局 FAIL 合计为 17：
- `FAIL  T-03   内容状态七值齐备(缺失数) (期望 0, 实得 7)`
- `FAIL  T-03b  错误码已搬运 (期望 >=3, 实得 0)`
- `FAIL  T-03c  八类审核已落枚举 (期望 >=3, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证内容成熟度 7 值齐备
for v in source_verified machine_extracted cross_model_reviewed disputed needs_expert expert_verified deprecated; do
  rg -q "$v" "$SPEC" || { echo "缺失内容状态: $v"; exit 1; }
done

# 2. 验证 9 个错误码齐备
for c in SRC_001 SRC_003 TXT_001 ID_001 ID_002 REF_001 SCH_001 SCH_002 SEM_001; do
  rg -q "$c" "$SPEC" || { echo "缺失错误码: $c"; exit 1; }
done

# 3. 验证 8 类审核枚举与中文释义齐备
for r in review_source_fidelity review_edition_collation review_school_attribution review_explanation_quality review_case_authenticity review_practical_validity review_safety review_rights; do
  rg -q "$r" "$SPEC" || { echo "缺失审核枚举: $r"; exit 1; }
done
for cn in "来源忠实度" "版本和校勘" "流派归属" "解释质量" "案例真实性" "现实效度" "安全" "权利"; do
  rg -q "$cn" "$SPEC" || { echo "缺失审核中文释义: $cn"; exit 1; }
done

# 4. 验证 D-03 已有成果完整保留（严禁退化为空表或出现 TODO(D-03)）
! rg -q 'TODO\(D-03\)' "$SPEC" || { echo "错误：检测到 TODO(D-03) 空表占位残留"; exit 1; }
for a in draft sealed quarantined invalidated superseded; do
  rg -q "$a" "$SPEC" || { echo "缺失 Artifact 状态: $a"; exit 1; }
done
for s in running awaiting_human suspended succeeded failed; do
  rg -q "$s" "$SPEC" || { echo "缺失 StepRun 状态: $s"; exit 1; }
done

# 5. 代码排版与格式审查
git diff --check || exit 1

# 6. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-03` 由 FAIL 转为 PASS；
   - `T-03b` 由 FAIL 转为 PASS；
   - `T-03c` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 17 严格单调减少至 **14**；
3. `git diff --check` 无格式异常。
