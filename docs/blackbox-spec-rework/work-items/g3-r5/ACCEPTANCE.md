# ACCEPTANCE：G3 R5 主 Agent 独立验收

状态：`ACCEPTED`（2026-09-10；act/01 `5de99fa`、act/02 `241c38c`）

## 0. act/01 验收记录（2026-09-10，主 Agent 在 `git archive 5de99fa` 隔离树副本上实跑）

- 提交 `5de99fa` 只含 `work-items/g3-r3/mutations.sh`（+123/−9）。
- `selftest` → `SELFTEST: 41/41`，四个 `[7]` 项均为 PASS，且逐行校验插入顺序（anchor / 空行 / 目标行）。
- `all` → `MUTATIONS: 98/109 rejected`；`not-rejected` 恰 11 行，cid 为 d07-31..34、t07-27..28、t08-43..47，`MUTATION_NOT_APPLIED` 0。
- 新增 9 个常量与 TDD §1.1 逐字相等（`grep -Fxc` 各 1）；`C_T08_B1_SCOPE/B2_NOTE/B3_NOTE` 与 `verify-T.sh` 同源常量逐字一致。
- 新增行禁止模式扫描（`sort -u`、`[[:space:]]`、从 `$SPEC` 推导、否定词交替式）无命中。
- 分母 34/28/47 与用法注释一致。
- 第一位执行 Agent 在 act/01 提交后随宿主进程退出，`verify-T.sh` 无残留改动；act/02 由第二位执行 Agent 从干净状态重做。

## 1. 范围核对（实得）

- `git diff --name-only 5de99fa^ 5de99fa` → 仅 `work-items/g3-r3/mutations.sh`（+123/−9）。
- `git diff --name-only 241c38c^ 241c38c` → 仅 `verify-T.sh`（+113/−30）。
- `git diff --check ffe19df 241c38c` → 通过。`ffe19df..241c38c` 区间内其余文件改动全部来自并行 C/S 会话的 NC-001 提交（`aadd1fc` 等），与两个 G3 提交无关。
- 两个提交均带 `Co-Authored-By` 署名；执行 Agent 使用显式 `git add <path>`，开工前已存在的脏文件原样保留。
- 两脚本自 `241c38c` 至验收时工作树无改动。

## 2. 禁止模式扫描（实得）

对两个提交的新增行扫描 `sort -u`、`[[:space:]]`、否定词交替式（`不得|不应|并未|尚未`）、`C_*=`/`WANT=` 从 `$SPEC` 取值：均无命中。`g3_d07_items` 已删除（残留 0）。`run_group` 分母 34/28/47 与 `apply_case`/`case_ids` 实际用例一致。

主 Agent 通读 `241c38c` diff 的实现审查：
- D-07 `g3_d07_region` 以「下一 START / `### 16.2`」为固定边界，START 重复出现会被计入区域而失配；END 缺失时区域延伸到 §16 末尾而失配。
- T-07 表格：`|` 开头行恰 17，表头/分隔行逐字，15 行成员资格与唯一性双向计数，每行 `|` 字节数恰 3。
- T-08 §16.3.1：去空行后与 11 行序列逐字相等，三个块标题各计数 1；既有三块比较保留。
- FAIL 文案数字全部实算，无写死。

## 3. 重跑门禁（`export LC_ALL=en_US.UTF-8`，主 Agent 实得）

| 命令 | 期望 | 实得 |
|---|---|---|
| `verify-T.sh` 尾行 | `FAIL 合计: 0` | `FAIL 合计: 0`，`PASS  G3-` 12 行 |
| `mutations.sh selftest` 尾行 | `SELFTEST: 41/41` | `SELFTEST: 41/41` |
| `mutations.sh d07` 尾行 | `34/34 rejected` | `d07: 34/34 rejected` |
| `mutations.sh t07` 尾行 | `28/28 rejected` | `t07: 28/28 rejected` |
| `mutations.sh t08` 尾行 | `47/47 rejected` | `t08: 47/47 rejected` |
| `mutations.sh all` 尾行 | `109/109 rejected` | `MUTATIONS: 109/109 rejected` |
| `MUTATION_NOT_APPLIED` 计数 | 0 | 0 |
| Red 提交上 `all` 尾行 | `98/109 rejected` | `98/109 rejected`（见 §0） |
| `LC_ALL=C` 下 | 仅 `T-06s` 环境误报 | 仅 `T-06s`，无 `G3-*` FAIL |

## 4. 矩阵外盲测（主 Agent 私有脚本，执行 Agent 不可见；实得）

13 例规格盲测全部退出非零、命中指定完整 FAIL ID、`diff -q` 证明非 no-op：

| 例 | 变异 | 命中 | `ffe19df` 基线 |
|---|---|---|---|
| B01 | TP START 与首条目之间插入非列表行 | `G3-D07-TP` | 已拦截 |
| B02 | QC 块尾空行后插入 `>` 引用行 | `G3-D07-QC` | **假绿** |
| B03 | RI 块尾两个空行后追加例外 bullet | `G3-D07-RI` | **假绿** |
| B04 | RI START 后紧接附注 bullet | `G3-D07-RI` | 已拦截 |
| B05 | §16.2 表头后分隔行改为三列 | `G3-T07-MAP` | **假绿** |
| B06 | `school-views` 行尾追加空第三列 | `G3-T07-MAP` | **假绿** |
| B07 | 表尾追加未知 key 行 | `G3-T07-MAP` | 已拦截 |
| B08 | `SourceAssetPack` 值内插入 vertical-tab | `G3-T07-MAP` | 已拦截 |
| B09 | §16.3.1 标题后空行 + 正文 | `G3-T08-BLOCK` | **假绿** |
| B10 | B3 块尾追加 `4.` 编号标题 | `G3-T08-BLOCK` | 已拦截 |
| B11 | §16.3.1 内重复 §16.3.1 标题 | `G3-T08-BLOCK` | 已拦截 |
| B12 | B1 供给行 Package 名插入 form-feed | `G3-T08-BLOCK` | 已拦截 |
| B13 | B2 标题重复出现在 B1 之前 | `G3-T08-BLOCK` | **假绿** |

FAIL ID 超集测试：把脚本树复制到隔离目录，让门禁把 `FAIL  G3-D07-TP` 改印为 `FAIL  G3-D07-TP-X`，运行 `d07`：绑定 `G3-D07-TP` 的 13 例（d07-01/02/04/11/12/13/19/26/27/29/30/31/32）全部 `not-rejected`，其余 21 例 rejected，汇总 `21/34`。证明超集 ID 不能冒充绑定 ID。

## 5. 只读 Agent 复跑

由与执行 Agent 不同的只读 Agent（Sonnet）在同一 HEAD 上重跑 §3 全部命令并回报原始尾行；与主 Agent 结果逐行一致才算通过。### 5.1 实得（只读 Agent，HEAD `7ba3f35`，未做任何写操作）

- `verify-T.sh` 尾行 `FAIL 合计: 0`；`PASS  G3-` 12；无 `^FAIL` 行。
- selftest `41/41`；d07 `34/34`；t07 `28/28`；t08 `47/47`；all `109/109`；`MUTATION_NOT_APPLIED` 与 `not-rejected` 合计 0。
- `git diff --check ffe19df 241c38c` exit 0；`241c38c` 只含 `verify-T.sh`，`5de99fa` 只含 `mutations.sh`。
- 其独立盲测（QC 向后兼容声明之后追加第五个查询接口 bullet）命中 `FAIL  G3-D07-QC ...(START x1，区域非空行 7/6)`，`FAIL 合计: 1`。
- 两处「与预期不符」的回报经主 Agent 核对均非缺陷：`ffe19df..241c38c` 区间多出的文件全部来自并行 C/S 会话的 NC-001 提交；其 awk 插入命中 3 行是 macOS awk 在 UTF-8 locale 下多字节 `==` 不可靠（`verify-T.sh` 注释已记录，门禁自身以 `LC_ALL=C` 规避），不影响门禁判定。

以上与 §3 主 Agent 结果逐行一致。

## 6. 通过条件

正常规格 0 FAIL；固定矩阵 109/109；盲测全部非零且命中指定完整 FAIL ID；提交仅两个授权脚本；无跳过、no-op 或范围外修改。通过后由主 Agent 更新 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md` 与 `PROJECT_COLD_START_HANDOFF.md`，G3 状态方可从 `REWORK_REQUIRED` 变更。
