# D-07 验收报告

## 1. 基本信息

- 任务 ID：`d07-technique-profile-and-query-contract`
- 状态：`ACCEPTED`
- 关联规格：`openspec/learn-system-blackbox-architecture.md` §13, §16
- 关联返工项：RB 组第 4 条

## 2. 检查清单

- [x] 工作包六件套完整且自审符合规范
- [x] 门禁增加 D-07 断言，旧规格验证确认变红（Red：FAIL 9 项，退出码 9）
- [x] 架构规格 §13 与 §16 补齐相应规约（TechniqueProfilePack、QueryContractPack、四接口、Profile/AST 版本、禁止 Python 规则、M5 FactSet 校验）
- [x] 门禁全绿（Green，`verify-T.sh` 退出码为 0，FAIL 合计 0）
- [x] 负向变异测试证明删除核心元素必 FAIL（5 类变异全部非零退出）
- [x] `git diff --check` 通过（无格式/行尾冲突）
- [x] 无非授权文件触碰（工作区隔离完整）
- [x] 独立提交完成

## 3. 验收证据记录

### Red 阶段证据
```text
=== T 类返工判据 (基线: 未返工时应大面积 FAIL) ===
...
FAIL  D-07s PublicationPackage missing TechniqueProfilePack or QueryContractPack
FAIL  D-07s QueryContractPack missing interface: getEntry
FAIL  D-07s QueryContractPack missing interface: getSourceSpan
FAIL  D-07s QueryContractPack missing interface: searchKnowledge
FAIL  D-07s QueryContractPack missing interface: matchFacts
FAIL  D-07s TechniqueProfile missing element: FactSet Profile
FAIL  D-07s TechniqueProfile missing element: operator 集合
FAIL  D-07s TechniqueProfile missing element: AST schema 版本
FAIL  D-07s rules declarative AST or Python ban missing
...
FAIL 合计: 9
退出码: 9
```

### Green 阶段证据
```text
=== T 类返工判据 (基线: 未返工时应大面积 FAIL) ===
PASS  T-01   三层术语已写入
PASS  T-02   §8.1 标识规范存在
PASS  T-02b  已冻结 ID 格式已搬运
PASS  T-03   内容状态七值齐备(缺失数)
PASS  T-03b  错误码已搬运
PASS  T-03c  八类审核已落枚举
PASS  T-04   G1-G7 已接线(缺失数)
PASS  T-04b  三级消费级别已写入
PASS  T-04c  fail-closed 已声明
PASS  T-04s  semantic obligation: 全链哈希
PASS  T-04s  semantic obligation: 确定性.*patch.*revision
PASS  T-04s  semantic obligation: source.*technique.*revision.*一致
PASS  T-04s  semantic obligation: 适用域.*冲突
PASS  T-04s  semantic obligation: 逐 source.*technique
PASS  T-04s  semantic obligation: 全部且仅返回适用规则
PASS  T-04s  semantic obligation: 已满足.*缺失.*例外
PASS  T-04s  semantic obligation: 风险簇全检
PASS  T-04s  §16 obligation: ReleaseManifest
PASS  T-04s  §16 obligation: 最低 APP 版本
PASS  T-04s  §16 obligation: source_release=dev
PASS  T-05   evidence_level 两档
PASS  T-06   EvidenceMapPack 有说明
PASS  T-06s  §16 证据链七项精确有序且闭合
PASS  D-07s PublicationPackage contains TechniqueProfilePack and QueryContractPack
PASS  D-07s QueryContractPack interface: getEntry
PASS  D-07s QueryContractPack interface: getSourceSpan
PASS  D-07s QueryContractPack interface: searchKnowledge
PASS  D-07s QueryContractPack interface: matchFacts
PASS  D-07s TechniqueProfile element: FactSet Profile
PASS  D-07s TechniqueProfile element: operator 集合
PASS  D-07s TechniqueProfile element: AST schema 版本
PASS  D-07s TechniqueProfile element: Profile 版本
PASS  D-07s rules require declarative AST and forbid executable Python
PASS  D-07s M5 verifies FactSet rule executability under G6
PASS  T-07   KnowledgePack 映射表(缺失)
PASS  T-08   Tag 三接口已承接
PASS  T-08b  Tag 五字段已写入
PASS  T-09   Orchestrator 六项查询(缺失)
PASS  T-10   异常页终态三值
PASS  T-11   §19 实测数字已写入
PASS  T-11s §19 uses the real ingest tool path
PASS  T-11s historical fact: 已由 G2 修复
PASS  T-11s historical fact: 历史缺口已遏制
PASS  T-11s historical fact: 启动覆盖本地库
PASS  T-11s historical fact: 保存即 verified
PASS  T-11s tracked non-OCR test count and scope
PASS  T-11s HEAD fact: 496 rules
PASS  T-11s HEAD fact: original_text` 非空 0
PASS  T-11s HEAD fact: is_verified=1` 为 0
PASS  T-11s HEAD fact: ge_ju_versions` 0
PASS  T-11s HEAD fact: conditions` 非空 404
PASS  T-11s HEAD fact: chapter` 非空 486
PASS  T-11s HEAD fact: 148 span
PASS  T-11s HEAD fact: 18 键
PASS  T-11s HEAD fact: 6 组碰撞
PASS  T-11s  §19 当前差距均列二元判据
PASS  T-11s binary criteria are explicit
PASS  T-11s  §19.0 每行两侧均为命令且有期望退出码
PASS  T-12   §19 施工顺序说明
PASS  T-13   §3–§18章节号→状态映射
PASS  T-13a  §16建议句局部讨论候选
PASS  T-13b  无节被标最终规范

=== D 类前置(仅提示，不计入退出码) ===
  entity_id 拆分:        6 处
  KnowledgeEntry 归位:   8 处 (目标 >=3)
  EditionPart 定义:      13 处
  失效传播改写:          残留「M3 至 M6 全部失效」0 处 (目标 0)
  §20 判据脚本:          缺失
  fixture Edition:       缺失
  RN-1 旧完成标准残留:   0 处 (目标 0)
  RN-2 身份拆分:         entity_id=6 / artifact_revision_id=13
  RN-3 人工挂起态:       awaiting_human=8 / resume_token=2

FAIL 合计: 0
退出码: 0
```

### 负向变异测试证据
```text
Mutation 1 (remove matchFacts) exit code: 1
Mutation 2 (remove TechniqueProfilePack) exit code: 1
Mutation 3 (remove AST schema 版本) exit code: 1
Mutation 4 (remove Profile 版本) exit code: 1
Mutation 5 (allow Python) exit code: 1
Restored exit code: 0
ALL 5 MUTATIONS SUCCESSFULLY FAILED AND RESTORED!
```
