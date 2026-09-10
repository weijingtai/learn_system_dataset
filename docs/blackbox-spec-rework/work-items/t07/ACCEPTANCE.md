# T-07 主 Agent 验收清单

状态：`REWORK_REQUIRED_R2`（正文基本正确，唯一归属门禁假绿）

## 1. Scope and Commits

- [x] 仅修改授权文件（`openspec/learn-system-blackbox-architecture.md`、`docs/blackbox-spec-rework/verify-T.sh` 及 `work-items/t07/`）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未触碰并发修改中的注解系统文件
- [x] 提交消息符合规范

## 2. KnowledgePack Mapping Table Verification

- [x] §16.2 包含全部 15 个早期目录条目，逐项严格映射，无任何遗漏且无空行
- [x] 每个条目在第一列各出现且仅出现一次（数据行总数严格为 15）
- [x] `query-contract` 唯一归属 `QueryContractPack`，严禁归入 `RuleIndexPack` 或 `SearchIndexPack`
- [x] `optional-vector-index` 保留非目标声明（依据 §21）
- [x] 包含明确的 KnowledgePack 取代声明（`PublicationPackage` / `KnowledgeDataPack` 正式取代早期草案）

## 3. Evidence and Regression

### Red 阶段证据
```text
FAIL  T-07s §16.2 映射表不合规: query-contract未归属QueryContractPack; query-contract错归IndexPack;
PASS  T-07s §16.2 包含KnowledgePack取代声明
FAIL 合计: 1
退出码: 1
```

### Green 阶段证据
```text
PASS  T-07s §16.2 映射表15项唯一且query-contract正确归属QueryContractPack
PASS  T-07s §16.2 包含KnowledgePack取代声明
FAIL 合计: 0
退出码: 0
```

### 负向变异测试证据
```text
Mutation 1 (wrong mapping) exit code: 1
Mutation 2 (missing row) exit code: 1
Mutation 3 (missing replacement statement) exit code: 1
Restored exit code: 0
ALL 3 T-07 MUTATIONS SUCCESSFULLY FAILED AND RESTORED!
```

- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查与质量审查通过
- [ ] 主 Agent 标记 `ACCEPTED`（等待 R2 返工）

R2 复核：追加第二归属、给 optional-vector-index 追加 SearchIndexPack、把“正式取代”改成“不得取代”时，现门禁仍为 0；返工见 `../../reviews/G3-REVIEW-R2.md`。
