# T-11 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线；R1 的语义门禁必须在旧 §19 上变红，不能只依赖数字频次：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

变异基线至少覆盖：错误的 `tools/ingest_epub.py` 路径、把 G2 历史缺陷写成当前缺口、把测试统计写成未排除 `.venv` 的 `find` 命令，以及删除任一当前差距的二元判据；每个变异都必须产生非零退出码。

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证实测数字出现频次 (期望 >= 2)
test $(grep -c "496\|148" "$SPEC") -ge 2 || { echo "实测数字 496/148 频次不足"; exit 1; }

# 2. 验证 18 键碰撞说明
grep -q "18 键\|18键" "$SPEC" || { echo "缺失 18 键碰撞说明"; exit 1; }

# 3. 验证 §19 表格行数扩展 (期望 >= 21)
rows=$(grep -c "^|" <(sed -n '/## 19/,/## 20/p' "$SPEC"))
test "$rows" -ge 21 || { echo "§19 表格行数不足: $rows (期望 >= 21)"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 真实 HEAD 事实与二元判据门禁
grep -q "pipeline/tools/ingest_epub.py" "$SPEC"
! grep -Eq "(^|[^/])tools/ingest_epub.py" "$SPEC"
grep -q "已由 G2 修复" "$SPEC"
grep -q "历史缺口已遏制" "$SPEC"
grep -q "git ls-files" "$SPEC"
grep -q ".venv" "$SPEC"
grep -q "为 3 个" "$SPEC"
grep -q "当前失败" "$SPEC"
grep -q "修复后判据" "$SPEC"

# 6. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中 `T-11` 及其 `T-11s` 语义门禁全部 PASS；全局 FAIL 不增加。
3. `git diff --check` 无格式异常。
