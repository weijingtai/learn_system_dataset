# D-07 BDD 行为场景

## 场景 1：TechniqueProfilePack 完备性规范（正常路径）

- **Given**：黑箱架构规格定义发布子包 PublicationPackage；
- **When**：编译器封存发布包且下游系统消费该技法规则时；
- **Then**：
  - `TechniqueProfilePack` 明确作为发布子包之一出现；
  - 包含 `FactSet Profile`（如 `QizhengFactSet`、`BaziFactSet` 等）；
  - 包含事实字段与枚举定义、operator 集合；
  - 包含规则 AST schema 版本声明；
  - 首纵切明确采用 `QizhengFactSet`。

## 场景 2：QueryContractPack 完备性规范（正常路径）

- **Given**：客户端或只读适配器需要查询结构化知识；
- **When**：下游消费端调用查询接口时；
- **Then**：
  - `QueryContractPack` 明确作为发布子包之一出现；
  - 显式定义 `getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts` 四个只读查询接口；
  - 包含接口向后兼容性声明（兼容演进规则）；
  - `matchFacts` 输入为版本化 FactSet，输出全部且仅适用规则，不依赖自由文本猜测。

## 场景 3：RuleIndexPack 规则的声明式与版本绑定（正常路径）

- **Given**：`RuleIndexPack` 包含用于确定性匹配的规则集合；
- **When**：规则被打包与消费时；
- **Then**：
  - 每条规则必须显式声明所依据的 TechniqueProfile 版本；
  - 规则只能是纯声明式结构化 AST / YAML / JSON；
  - 绝对禁止可执行 Python 代码。

## 场景 4：M5 工位职责边界与 G6 可执行性校验（正常路径）

- **Given**：M5 进行确定性验证（ValidationPackage）；
- **When**：执行 G6 盘面确定性匹配门禁校验时；
- **Then**：
  - M5 依据 G6 执行规则对 FactSet 的可执行性与 AST 完整性校验；
  - 任一条件不全或例外成立时，禁止输出肯定判断；
  - M5 仅为校验器工位，严禁将 M5 声明为生产 Tag 字段的工位。

## 场景 5：缺少任一查询接口或核心字段（异常路径）

- **Given**：规格中缺失 `matchFacts`、`getEntry`、`getSourceSpan`、`searchKnowledge` 中任意一个；
- **When**：运行语义校验门禁；
- **Then**：校验脚本必须非零退出（FAIL），阻断验收。

## 场景 6：缺少 Profile 版本声明或 AST Schema 版本（异常路径）

- **Given**：规格中未要求规则声明 Profile 版本，或未定义 AST schema 版本；
- **When**：运行语义校验门禁；
- **Then**：校验脚本必须非零退出（FAIL），阻断验收。

## 场景 7：允许 Python 规则或 M5 越权生产（异常路径）

- **Given**：规格中允许规则包含可执行 Python，或将 M5 列为 Tag 字段生产工位；
- **When**：运行语义校验门禁；
- **Then**：校验脚本必须非零退出（FAIL），阻断验收。
