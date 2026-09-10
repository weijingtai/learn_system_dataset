# T-10 BDD 验收场景

## B1 异常页三终态枚举完备性

Given 权威源 `docs/blackbox-spec-rework/T-transcribe.md` 确立了 M2 异常页的三种终态，
When 执行者查看架构规格 §10，
Then 规格必须明确定义以下三项枚举：
- `manually_transcribed`：人工完整转录；
- `known_unrecognizable`：已知客观不可识别（必须附理由与证据 Artifact，严禁裸标）；
- `deferred`：暂缓处理或工具链未决。

## B2 M2 Gate 放行与阻断逻辑

Given M2 Gate 必须保障输出 DigitizationPackage 的质量与完整性，
When 检查异常页的终态分布，
Then 规则必须明确：
1. `manually_transcribed` 与 `known_unrecognizable` 允许 M2 Gate 放行；
2. `deferred` 严格阻断 M2 Gate 通过，禁止进入 M3；
3. 规格明确声明该规则与 §6.1「失败为零」一致，因为「客观不可识别」属于已知受控输入局限，并非失败。
