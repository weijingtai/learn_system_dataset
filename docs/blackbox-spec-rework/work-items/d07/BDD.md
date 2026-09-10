# D-07 BDD 行为场景（R2 返工版）

## 场景 1：TechniqueProfilePack 专属块闭合（正常路径）

- **Given**：规格 §16 中 `TechniqueProfilePack` 有独立导语段；
- **When**：运行语义门禁；
- **Then**：该段内必须齐备 `FactSet Profile`、事实字段与闭集枚举、`operator 集合`、`AST schema 版本`，且明确禁止可执行或模型生成的 Python 规则。

## 场景 2：QueryContractPack 专属块闭合（正常路径）

- **Given**：规格 §16 中 `QueryContractPack` 有独立导语段；
- **When**：运行语义门禁；
- **Then**：该段内必须齐备 `getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts` 四接口与向后兼容声明。

## 场景 3：RuleIndexPack 专属块闭合（正常路径）

- **Given**：规格 §16 中 `RuleIndexPack` 有独立导语段；
- **When**：运行语义门禁；
- **Then**：该段内必须要求每条规则显式声明 `profile_version` 与 AST schema 版本，且规则为声明式 `结构化 AST/YAML/JSON`。

## 场景 4：删除「事实字段与枚举」整条（异常路径）

- **Given**：从 `TechniqueProfilePack` 专属块删除「事实字段与枚举」整条；
- **When**：运行语义门禁；
- **Then**：必须非零退出；`ReleaseManifest` 或 §16 其他文字不得代偿。

## 场景 5：把「事实字段与枚举」改成否定语义（异常路径）

- **Given**：该条被改成「包中不列任何事实字段与枚举；字段由客户端自由猜测」；
- **When**：运行语义门禁；
- **Then**：必须非零退出（否定语义不得通过）。

## 场景 6：删除 RuleIndexPack 的逐规则版本声明（异常路径）

- **Given**：从 `RuleIndexPack` 专属块删除「每条规则必须显式声明 Profile 版本及 AST schema 版本」整条；
- **When**：运行语义门禁；
- **Then**：必须非零退出；`ReleaseManifest` 中泛化的「Schema/Profile 版本」文字不得让该门禁通过。

## 场景 7：M5 工位边界（正常路径）

- **Given**：§13 定义 M5 校验职责；
- **When**：运行语义门禁；
- **Then**：必须确认 M5 在 G6 下校验 FactSet 规则可执行性，且不生产任何包契约与 Tag 字段。
