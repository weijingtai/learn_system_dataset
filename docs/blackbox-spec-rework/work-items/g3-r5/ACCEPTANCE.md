# ACCEPTANCE：G3 R5 主 Agent 独立验收

状态：`PENDING`（等待执行 Agent 交付）

## 1. 范围核对

```bash
git log --oneline ffe19df..HEAD -- docs/blackbox-spec-rework/
git show --stat --oneline <red-commit>     # 只含 g3-r3/mutations.sh
git show --stat --oneline <fix-commit>     # 只含 verify-T.sh
git diff --name-only ffe19df <fix-commit> -- docs/blackbox-spec-rework/ | grep -v -e verify-T.sh -e g3-r3/mutations.sh -e work-items/g3-r5/   # 期望空
git diff --check ffe19df <fix-commit>
```

## 2. 禁止模式扫描（对两个脚本的 diff）

- 不得新增否定词列表（如 `不得|不应|并未|尚未` 这类交替式正则用于放行判断）；
- 不得出现 `sort -u`、`[[:space:]]` 用于规范化；
- 不得从 `$SPEC` 读取内容赋给 expected/WANT；
- `run_group` 分母与 `apply_case`/`case_ids` 实际用例数一致。

## 3. 重跑门禁（`export LC_ALL=en_US.UTF-8`）

| 命令 | 期望 | 实得 |
|---|---|---|
| `verify-T.sh` 尾行 | `FAIL 合计: 0` | |
| `mutations.sh selftest` 尾行 | `SELFTEST: 41/41` | |
| `mutations.sh d07` 尾行 | `34/34 rejected` | |
| `mutations.sh t07` 尾行 | `28/28 rejected` | |
| `mutations.sh t08` 尾行 | `47/47 rejected` | |
| `mutations.sh all` 尾行 | `109/109 rejected` | |
| `MUTATION_NOT_APPLIED` 计数 | 0 | |
| Red 提交上 `all` 尾行 | `98/109 rejected` | |

## 4. 矩阵外盲测（主 Agent 私有，不写入工作包，执行 Agent 不可见）

至少 5 例，覆盖：D-07 三段间隙（含 START 与首条目之间、条目之间插入非列表行）、T-07 额外列/额外声明行、T-08 任意重复标题/块外内容、FAIL ID 超集、Package 名控制字符。每例记录：变异描述、退出码、命中 FAIL ID、`diff -q` 证明非 no-op。

## 5. 只读 Agent 复跑

由与执行 Agent 不同的只读 Agent 在同一 HEAD 上重跑 §3 全部命令并回报原始尾行；与主 Agent 结果逐行一致才算通过。

## 6. 通过条件

正常规格 0 FAIL；固定矩阵 109/109；盲测全部非零且命中指定完整 FAIL ID；提交仅两个授权脚本；无跳过、no-op 或范围外修改。通过后由主 Agent 更新 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md` 与 `PROJECT_COLD_START_HANDOFF.md`，G3 状态方可从 `REWORK_REQUIRED` 变更。
