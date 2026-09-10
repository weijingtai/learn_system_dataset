# T-08 主 Agent 验收清单

状态：`ACCEPTED`（R1 返工完成）

## 1. Scope and Commits

- [x] 仅修改授权文件（`openspec/learn-system-blackbox-architecture.md`、`docs/blackbox-spec-rework/verify-T.sh` 及 `work-items/t08/`）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未触碰并发修改中的注解系统文件
- [x] 提交消息符合规范

## 2. Tag System Interfaces & Fields Verification

- [x] §1 与 §16.3 均清晰承接 Tag 三个接口（`最小盘面概念字典`、`MarkContentBinding`、`EvidenceBundle`）
- [x] 概念字典明确声明「不含规则 DSL」，保留硬限制
- [x] Tag 侧 G4 显式命名空间化为 `TAG_SYSTEM_DESIGN.md §12.2 的 G4`，与本规格正文 G4 内容分层门禁彻底区分
- [x] §16.3.2 表格包含五个关键字段（`omen_carrying`、`condition_affordance`、`school_variance_display`、`concept_id`、`是否改变当前判断`）
- [x] 生产 Module 列**严禁包含 M5**，M5 的职责单列为 Validator（负责校验合规性与可执行性，不负责生产）
- [x] 「是否改变当前判断」明确由知识层供给，UI 不得猜测

## 3. Evidence and Regression

### Red 阶段证据
```text
FAIL  T-08s Tag G4 missing TAG_SYSTEM_DESIGN.md namespace
FAIL  T-08s §16.3 table issue: condition_affordance生产列包含M5( M4 / M5 ); omen_carrying生产列包含M5( M4 / M5 );
FAIL 合计: 2
退出码: 2
```

### Green 阶段证据
```text
PASS  T-08s Tag interface present in §1 and §16.3: 最小盘面概念字典
PASS  T-08s Tag interface present in §1 and §16.3: MarkContentBinding
PASS  T-08s Tag interface present in §1 and §16.3: EvidenceBundle
PASS  T-08s concept dictionary preserves rule DSL restriction
PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2
PASS  T-08s §16.3 table 5 fields present and M5 excluded from producers
FAIL 合计: 0
退出码: 0
```

### 负向变异测试证据
```text
Mutation 1 (M5 producer) exit code: 1
Mutation 2 (missing namespace) exit code: 1
Mutation 3 (missing DSL restriction) exit code: 1
Mutation 4 (missing interface) exit code: 1
Restored exit code: 0
ALL 4 T-08 MUTATIONS SUCCESSFULLY FAILED AND RESTORED!
```

- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查与质量审查通过
- [x] 主 Agent 标记 `ACCEPTED`
