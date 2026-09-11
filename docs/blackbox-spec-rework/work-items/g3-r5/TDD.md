# TDD：G3 R5 先红后绿

全部命令在仓库根目录执行，且先 `export LC_ALL=en_US.UTF-8`。

## 0. 开工前基线（必须与下列完全一致，否则停手）

```bash
git diff --stat ffe19df HEAD -- docs/blackbox-spec-rework/verify-T.sh docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh   # 期望：无输出
bash docs/blackbox-spec-rework/verify-T.sh | tail -1        # 期望：FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh selftest | tail -1   # 期望：SELFTEST: 37/37
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1        # 期望：MUTATIONS: 98/98 rejected
```

## 1. Red：新增用例（act/01，只改 mutations.sh）

### 1.1 新增硬编码常量（逐字，禁止推导）

```bash
L_D07_32='客户端仍可绕过 TechniqueProfilePack，使用任意自由字段参与确定性匹配。'
L_D07_33='客户端可以绕过 QueryContractPack 直接读取底层文件。'
L_D07_34='RuleIndexPack 中的规则允许附带 Python 代码块。'
V_T07_EXTRA_COL=' 冲突附加值 |'
L_T08_45='以上三个接口之外，Tag 系统还可以直接读取 `SourceAssetPack`。'
C_T08_S1631_HEAD='#### 16.3.1 三个耦合接口规范与供给子包'
C_T08_B1_SCOPE='   - **规模与范围**：规模控制在约 100–200 个概念（覆盖十天干、十二地支、九星、八门、八神等盘面基础元素），仅包含稳定 ID（`concept_id`）、名称与基础类象；'
C_T08_B2_NOTE='   - **承接说明**：为 UI 标记提供内容与分歧数据，包括吉凶定性、条件槽位可供性与流派分歧展示。'
C_T08_B3_NOTE='   - **承接说明**：为 AI 解盘与端侧证据高亮提供底层的无损证据链切片，确保标记内容能溯源至底本原页与字框坐标。'
```

（共 9 个。`L_D07_27` 复用既有常量作 d07-31 的 bullet；`C_T08_B1_SCOPE/B2_NOTE/B3_NOTE` 照抄 `verify-T.sh` 既有常量；`C_T08_S1631_HEAD` 逐字抄自规格第 734 行。expected 唯一来源是两个脚本内已提交的 `C_*` 常量与本文件，不依赖 g3-r3 目录下任何未提交草稿。）

### 1.2 新增两个原语（各自带命中断言）

- `append_gap_line <file> <anchor> <line>`：anchor 恰 1 次；在 anchor 后插入一个空行再插入 `line`；断言总行数 +2、`line` 命中次数 +1。
- `append_suffix <file> <anchor> <suffix>`：anchor 恰 1 次；把该行替换为 `anchor+suffix`；断言新行恰 1 次、原行 0 次（可基于 `replace_line` 实现）。

### 1.3 新增 11 例与绑定 ID

| cid | 操作 | 绑定 FAIL ID |
|---|---|---|
| d07-31 | `append_gap_line C_D07_TP_AST L_D07_27` | `G3-D07-TP` |
| d07-32 | `append_gap_line C_D07_TP_AST L_D07_32` | `G3-D07-TP` |
| d07-33 | `append_gap_line C_D07_QC_COMPAT L_D07_33` | `G3-D07-QC` |
| d07-34 | `append_gap_line C_D07_RI_DECLARATIVE L_D07_34` | `G3-D07-RI` |
| t07-27 | `append_suffix C_T07_M01 V_T07_EXTRA_COL` | `G3-T07-MAP` |
| t07-28 | `append_suffix C_T07_M15 V_T07_EXTRA_COL` | `G3-T07-MAP` |
| t08-43 | `append_line C_T08_B3_NOTE C_T08_B3_HEAD` | `G3-T08-BLOCK` |
| t08-44 | `append_line C_T08_B1_LIMIT C_T08_B1_HEAD` | `G3-T08-BLOCK` |
| t08-45 | `append_line C_T08_S1631_HEAD L_T08_45`（§16.3.1 标题与 B1 标题之间的块外正文） | `G3-T08-BLOCK` |
| t08-46 | `append_gap_line C_T08_B3_NOTE C_T08_B3_HEAD`（空行 + 重复 B3 标题） | `G3-T08-BLOCK` |
| t08-47 | `append_line C_T08_B2_NOTE C_T08_B2_HEAD`（B2 块尾重复 B2 标题） | `G3-T08-BLOCK` |

注意：「B3 承接说明之后追加正文」「B2 块后空行 + 正文」这两种变异在 HEAD 已被 `G3-T08-BLOCK` 拒绝（块解析会把它们吞进块内），不是 Red，不得作为新增用例；主 Agent 2026-09-10 已实跑确认上表 11 例在 HEAD 全部 exit 0。

分母更新：`d07 34`、`t07 28`、`t08 47`、`all` 合计 `109`；脚本头部用法注释同步为真实数字。

### 1.4 新增 selftest（恰 4 项，总分母 41）

- `[7] append_gap_line 在 anchor 后恰插入「空行 + 目标行」且总行数 +2`
- `[7] append_gap_line anchor 缺失 -> 失败`
- `[7] append_suffix 结果恰为 anchor+suffix 且原行消失`
- `[7] append_suffix anchor 命中 2 次 -> 失败`

### 1.5 Red 期望输出（修 verify-T.sh 之前）

```bash
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh selftest | tail -1   # SELFTEST: 41/41
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh d07 | grep -E '^not-rejected|rejected$'
#   期望恰 4 行 not-rejected：d07-31 d07-32 d07-33 d07-34；汇总 d07: 30/34 rejected
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t07 | grep -E '^not-rejected|rejected$'
#   期望恰 2 行 not-rejected：t07-27 t07-28；汇总 t07: 26/28 rejected
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t08 | grep -E '^not-rejected|rejected$'
#   期望恰 5 行 not-rejected：t08-43..47；汇总 t08: 42/47 rejected
```

任何一行是 `MUTATION_NOT_APPLIED` 即 Anchor 常量抄错，停手修常量，不得改规格。

## 2. Green：封闭三类区域（act/02，只改 verify-T.sh）

### 2.1 D-07：替换 `g3_d07_items` 的「遇非列表行即停」为区域提取

- 新函数 `g3_d07_region <规范化§16> <START规范行> <END规范行>`：从 `$0 == START` 起打印到 `$0 == END` 前一行止（含 START 行，不含 END 行），跳过空行；END 未出现则打印到末尾。
- TP：END = QC START；QC：END = RI START；RI：END = `g3norm "$C_T07_HEAD"`（即 `###16.2KnowledgePack与PublicationPackage双向映射表`）。
- WANT 改为 `START行 + 条目`（`g3_join_items` 前置 START 规范行）。
- 三个 START 各恰出现一次的既有检查保留；四接口只能来自 QC 区域条目的检查保留（从区域中去掉首行 START 后比较）。
- 删除旧函数 `g3_d07_items`（不得保留死代码）。FAIL 行文案改为 `(START x%s，区域非空行 %s/5)`（TP）、`/6`（QC）、`/3`（RI），第二个数字 = 区域去空行后的行数（含 START 行），由 `g3_nlines` 实算。

### 2.2 T-07：表格 17 行完整封闭

- 在 `verify-T.sh` 新增硬编码常量（逐字，`C_T07_M01..M15` 抄自 `mutations.sh`）：

```bash
C_T07_TBL_HEAD='| 早期 KnowledgePack 目录建议 (`TARGET.md §9`) | 现行黑箱架构落点 (`PublicationPackage` 子包 / 规约) |'
C_T07_TBL_SEP='|---|---|'
```
- 新检查 `t07_tbl_err`：取 `sec162n` 中所有以 `|` 开头的行；要求行数 17；第 1 行等于规范化表头、第 2 行等于规范化分隔行；第 3–17 行每行 `|` 字节数恰 3，且每行等于 15 个规范化 canonical 行之一、每个 canonical 恰命中一次（用 `g3cnt` 逐一计数，不用 `sort -u`）。
- `G3-T07-MAP` 的 PASS 条件改为 `t07_map_err = OK && t07_decl_err = OK && t07_tbl_err = OK`；FAIL 文案追加 `[表行:%s]`。

### 2.3 T-08：§16.3.1 全区域序列相等 + 标题唯一

- 新增常量 `C_T08_S1631_HEAD='#### 16.3.1 三个耦合接口规范与供给子包'`。
- 从 `sec1631n` 中去掉以 `####16.3.2` 开头的收尾行（同 `sec162` 的做法），去掉空行，得到 `t08_s1631_seq`。
- `T08_S1631_WANT` = `g3_join_items` 依次拼接：S1631_HEAD、B1_HEAD、B1_SUPPLY、B1_SCOPE、B1_LIMIT、B2_HEAD、B2_SUPPLY、B2_NOTE、B3_HEAD、B3_SUPPLY、B3_NOTE（11 行，全部 `g3norm`）。
- 三个 HEAD 在 `sec1631n` 中各用 `g3cnt` 计数，必须为 1。
- `G3-T08-BLOCK` 的 PASS 条件追加：`t08_s1631_seq = T08_S1631_WANT` 且三个 HEAD 计数均为 1；FAIL 文案追加 `区域行数=<n>(期望11)` 与 `标题计数 B1xN B2xN B3xN`。既有 `g3_t08_block` 三块比较保留。

### 2.4 Green 期望输出

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                              # FAIL 合计: 0
bash docs/blackbox-spec-rework/verify-T.sh | grep -c '^PASS  G3-'                  # 与修复前相同（12）
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh selftest | tail -1   # SELFTEST: 41/41
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh d07 | tail -1        # MUTATIONS: 34/34 rejected
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t07 | tail -1        # MUTATIONS: 28/28 rejected
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t08 | tail -1        # MUTATIONS: 47/47 rejected
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -4        # d07: 34/34 / t07: 28/28 / t08: 47/47 / MUTATIONS: 109/109 rejected
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | grep -c 'MUTATION_NOT_APPLIED'   # 0
git diff --check                                                                    # 无输出
```

## 3. 禁止的「通过方式」

- 在 `g3_d07_items` 里加否定词过滤；
- 只检查 canonical 行「存在」而不检查行数、唯一性和区域内无其他行；
- 把新增用例绑定到更宽泛的 ID 或去掉绑定；
- 让 `run_group` 的分母与实际用例数不一致。
