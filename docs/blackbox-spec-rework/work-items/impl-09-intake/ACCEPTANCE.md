# ACCEPTANCE：impl-09 M1 电子文本入库 + M2 电子文本清洗

## 1. 审查要点

### 1.1 代码质量

- 所有公开函数名、参数名、返回键、检查名、CLI 输出前缀与 ACT contract 逐字一致
- 中文注释与 docstring
- 只用标准库 + PyYAML + jsonschema；无外部依赖
- 不新增 ID 前缀（片段 ID 用已登记的 `ss_`/`sem_`；finding_id 用 `<kind>@<raw_start>-<raw_end>` 复合键格式，无新前缀）

### 1.2 契约完整性

- M1 产出 source_manifest 顶层键序与 INTERFACES §4 一致
- M2 产出四类 artifacts（raw_text, cleaned_text_revision, deterministic_patch_set, sanitization_report）键集与 §81 一致
- sanitization_report 的 kind 闭集与 §81 一致（12 项）
- sanitization_report 的 terminal_state 闭集与 §10.1 一致（3 项）
- gate.py 不 import cleaner/patcher/reporter/raw_text

### 1.3 可追溯性

- 每个 sanitization_report finding 都有 raw_start/raw_end（原始偏移）
- patch 映射可逆：apply_patches(raw, patches) == cleaned
- 片段 ID 偏移基准为冻结的 raw_text，不随清洗修订漂移

### 1.4 安全性

- 不伪造文件、哈希或人工决定
- 不调用模型 API
- 不写 fixture 目录
- P7：人工决定由用户决定表产出，执行者不代填
- P8：finding_id 无新前缀，格式 `<kind>@<raw_start>-<raw_end>`
- 第 52、53 条：所有测试用合成文本样例与合成决定表均标 `synthetic_fixture: true`；验收判定不得把它们当作真实签发或真实书源

### 1.5 边界

- 本包只新建 `m1-intake.sh`、`m2-sanitization.sh` 两份验收脚本
- **不修改 `run_all.sh`**；接进 `run_all.sh` 属另一个独占 ACT（P4），由主 Agent 安排
- 两份脚本在宿主缺失时 exit 2（BLOCKED）

### 1.5 回归

- check_interfaces.py 末行 fail=0
- run_all.sh 基线不变（SUMMARY pass=2 fail=1 blocked=8）
- schemas/verify.sh 退出码 0
- git diff --check 无警告

## 2. 判据

| 检查项 | 判据 | 依据 |
|---|---|---|
| M1 产出键序 | source_manifest 顶层键序与 INTERFACES §4 一致 | act/00 contract |
| M2 四类产物 | raw_text, cleaned_text_revision, deterministic_patch_set, sanitization_report 均产出 | act/02 contract |
| kind 闭集 | 12 项（encoding_issue, replacement_char, private_use_area, control_char, escape_residue, watermark, header_footer, duplicate, missing, textualized_diagram, variant_mixed, suspected_error） | §81 |
| terminal_state 闭集 | 3 项（processed, known_unresolvable, deferred） | §10.1 |
| deferred 阻断 | deferred_count > 0 时 Gate 不通过 | §10.1 |
| gate 独立性 | gate.py 不 import cleaner/patcher/reporter/raw_text | act/03 contract |
| patch 可逆 | apply_patches(raw, patches) == cleaned | act/02 contract |
| 来源无关 | source_info 含 source_site, source_url 字段 | §77 D2 |
| 验收脚本 | m1-intake.sh / m2-sanitization.sh exit 0/1/2 如实 | §19.0 |
| 回归 | check_interfaces.py fail=0，run_all.sh 基线不变 | gates |
| synthetic_fixture | 所有测试用合成数据标 `synthetic_fixture: true`；验收判定不把合成数据当真实签发 | 第 52、53 条 |
| finding_id 格式 | finding_id 为 `<kind>@<raw_start>-<raw_end>`，无新前缀 | P8 |
| run_all.sh 不动 | 本包不修改 run_all.sh；验收脚本 exit 2 表示 BLOCKED | §1 边界 |

## 3. 验收记录

验收记录由主 Agent 填写。

## 4. 待裁决

无。
