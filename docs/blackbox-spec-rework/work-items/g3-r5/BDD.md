# BDD：G3 R5 区域边界封闭

所有场景的 Given 都是：从 HEAD 权威规格复制一份全新临时副本 `$SPEC`，`export LC_ALL=en_US.UTF-8`，以 `SPEC=<副本> bash docs/blackbox-spec-rework/verify-T.sh` 运行门禁。

## 1. 正常路径

- Given 副本未做任何改动
- When 运行门禁
- Then 退出码 0，输出 `FAIL 合计: 0`，且所有 `G3-*` 行为 PASS

## 2. D-07 区域封闭（R5-1）

### 2.1 TP 区域间隙 bullet
- Given 在 TP 第四条目（AST schema 版本）之后插入一个空行，再插入 `- **自由字段说明**：客户端可以使用自由字段，不受闭集枚举约束；`
- When 运行门禁
- Then 退出码非零，且存在 `^FAIL[[:space:]]+G3-D07-TP([[:space:]]|$)` 行

### 2.2 TP 区域间隙段落
- Given 在 TP 第四条目之后插入一个空行，再插入 `客户端仍可绕过 TechniqueProfilePack，使用任意自由字段参与确定性匹配。`
- Then 同 2.1，命中 `G3-D07-TP`

### 2.3 QC 区域间隙段落
- Given 在 QC 第五条目（向后兼容声明）之后插入空行，再插入 `客户端可以绕过 QueryContractPack 直接读取底层文件。`
- Then 命中 `G3-D07-QC`

### 2.4 RI 区域间隙段落
- Given 在 RI 第二条目之后插入空行，再插入 `RuleIndexPack 中的规则允许附带 Python 代码块。`（位于 `### 16.2` 之前）
- Then 命中 `G3-D07-RI`

### 2.5 区域定义
- TP 区域 = TP START 行起，到 QC START 行前一行止
- QC 区域 = QC START 行起，到 RI START 行前一行止
- RI 区域 = RI START 行起，到 `### 16.2` 标题行前一行止
- 每个区域去掉空行后，规范化行序列必须与「START + 固定有序条目」逐字相等；任何多余行、缺失行、乱序、重复都使对应 ID FAIL

## 3. T-07 表格封闭（R5-2）

### 3.1 行尾第三列
- Given 在 `| \`release-manifest\` | ... |` 行尾追加 ` 冲突附加值 |`
- Then 命中 `G3-T07-MAP`

### 3.2 末行第三列
- Given 在 `| \`query-contract\` | ... |` 行尾追加 ` 冲突附加值 |`
- Then 命中 `G3-T07-MAP`

### 3.3 表格定义
- §16.2 内所有以 `|` 开头的行构成表格；必须恰为 17 行：表头行、分隔行、15 个数据行
- 表头行与分隔行规范化后必须逐字等于硬编码常量
- 15 个数据行规范化后必须各自逐字等于 15 个硬编码 canonical 行之一，每个 canonical 行恰出现一次
- 每个数据行的 `|` 字节数必须恰为 3（两列）；既有 key/value 字典比较继续保留

## 4. T-08 §16.3.1 封闭（R5-3）

### 4.1 B3 标题重复于块尾
- Given 在 B3 第二条目（承接说明）之后、`#### 16.3.2` 之前插入 `3. **\`EvidenceBundle\` 服务**：`
- Then 命中 `G3-T08-BLOCK`

### 4.2 B1 标题重复于块尾
- Given 在 B1 第三条目（硬限制约束）之后插入 `1. **\`最小盘面概念字典\`**：`
- Then 命中 `G3-T08-BLOCK`

### 4.3 块外正文
- Given 在 B3 第二条目之后插入 `以上三个接口之外，Tag 系统还可以直接读取 \`SourceAssetPack\`。`
- Then 命中 `G3-T08-BLOCK`

### 4.4 区域定义
- §16.3.1 区域 = `#### 16.3.1` 标题行起，到 `#### 16.3.2` 标题行前一行止
- B1/B2/B3 三个精确标题在区域内必须各恰出现一次
- 区域去掉空行后的规范化行序列必须逐字等于：§16.3.1 标题、B1 标题、B1 三条目、B2 标题、B2 两条目、B3 标题、B3 两条目（共 11 行）

## 5. 回归

- Given 既有 98 例固定矩阵
- Then 修复后仍 `98/98 rejected`，无 `MUTATION_NOT_APPLIED`
- Given selftest
- Then 既有 37 项全绿，新增项全绿，分母与脚本实际一致

## 6. 变异未生效

- Given 任一新增用例的 Anchor 命中次数不为 1
- Then 打印 `MUTATION_NOT_APPLIED <cid>`，绝不计为 rejected
