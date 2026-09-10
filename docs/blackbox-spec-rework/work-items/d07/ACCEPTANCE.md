# D-07 验收报告（G3 R2 返工）

## 1. 基本信息

- 任务 ID：`d07-technique-profile-and-query-contract`
- 状态：`REWORK_REQUIRED_R3`（指定变异已修；兼容性否定语义和 Package 改名仍可假绿）
- 关联规格：`openspec/learn-system-blackbox-architecture.md` §13、§16（只读，未修改）
- 关联缺陷台账：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md` D-07 节
- 提交：`fix: harden D-07 package-specific gates`（hash 见最终执行报告）

## 2. 变更文件

- `docs/blackbox-spec-rework/verify-T.sh`（D-07 段改为专属块解析）
- `docs/blackbox-spec-rework/work-items/d07/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

规格正文未改动。

## 3. 起点证据

```text
分支: codex/docs/knowledge-compilation
HEAD: 3987c6a fix: add G3 R2 cold-start handoff
cc03b79 是 HEAD 的祖先: 是
git status --short: 无输出（工作树干净）
git diff --check: 退出 0
bash docs/blackbox-spec-rework/verify-T.sh: 退出 0，FAIL 合计: 0
```

## 4. Red baseline（加固前，证明假绿）

```text
d07-1   exit=0   D-07 删除 TechniqueProfilePack 的「事实字段与枚举」整条
d07-2   exit=0   D-07 将「事实字段与枚举」改成否定语义（客户端自由猜测）
d07-3   exit=0   D-07 删除 RuleIndexPack 的「每条规则显式声明 Profile 版本及 AST schema 版本」整条
```

三个变异在加固前全部返回 0，复现 R2 复核所报假绿。

## 5. Green 证据（加固后，正常规格）

```text
退出码: 0
PASS  D-07s TP dedicated block located
PASS  D-07s QC dedicated block located
PASS  D-07s RI dedicated block located
PASS  D-07s TechniqueProfilePack element: FactSet Profile
PASS  D-07s TechniqueProfilePack element: operator 集合
PASS  D-07s TechniqueProfilePack element: AST schema 版本
PASS  D-07s TechniqueProfilePack mandates fact fields and closed enum values
PASS  D-07s TechniqueProfilePack forbids executable or model-generated Python
PASS  D-07s QueryContractPack interface: getEntry
PASS  D-07s QueryContractPack interface: getSourceSpan
PASS  D-07s QueryContractPack interface: searchKnowledge
PASS  D-07s QueryContractPack interface: matchFacts
PASS  D-07s QueryContractPack declares backward compatibility
PASS  D-07s RuleIndexPack binds every rule to profile_version and AST schema version
PASS  D-07s RuleIndexPack keeps rules declarative AST/YAML/JSON
PASS  D-07s M5 verifies FactSet executability under G6 and produces no contract
PASS  D-07s PublicationPackage lists TechniqueProfilePack and QueryContractPack
FAIL 合计: 0
```

## 6. 负向变异证据（加固后）

| 变异 | 加固前退出码 | 加固后退出码 | 触发的 FAIL |
|---|---|---|---|
| d07-1 删除「事实字段与枚举」整条 | 0（假绿） | 1 | `TechniqueProfilePack fact fields / closed enums missing or negated` |
| d07-2 改为「包中不列任何事实字段与枚举；字段由客户端自由猜测」 | 0（假绿） | 1 | 同上 |
| d07-3 删除 RuleIndexPack 的逐规则版本声明整条 | 0（假绿） | 1 | `RuleIndexPack per-rule profile_version / AST schema version missing` |

```text
=== d07-1 === FAIL  D-07s TechniqueProfilePack fact fields / closed enums missing or negated / FAIL 合计: 1
=== d07-2 === FAIL  D-07s TechniqueProfilePack fact fields / closed enums missing or negated / FAIL 合计: 1
=== d07-3 === FAIL  D-07s RuleIndexPack per-rule profile_version / AST schema version missing / FAIL 合计: 1
```

每次变异只触发 1 条 FAIL，无连带误报。`d07-3` 同时证明跨块代偿已阻断：`ReleaseManifest` 中的「Schema/Profile 版本」文字保留不动，RuleIndexPack 门禁仍非零退出。

## 7. 检查清单

- [x] 门禁改为三份契约的专属块解析，锚点缺失或重复一律 FAIL
- [x] 正常规格退出 0、`FAIL 合计: 0`
- [x] 三个强制变异加固前返回 0、加固后非零退出
- [x] R2 六件套口径一致，执行时状态为 `IMPLEMENTED_AWAITING_REVIEW`
- [x] 规格正文、业务代码与 Scope 外文件未被触碰
- [x] `git diff --check` 退出 0
- [ ] 主 Agent 独立验收（未完成）

R3 主 Agent 独立验收不通过：兼容性否定语义与 Package 改名仍可假绿。返工见 `../../reviews/G3-REVIEW-R3.md`；未启动 G4。
