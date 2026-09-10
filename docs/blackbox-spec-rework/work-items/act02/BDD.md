# ACT 02 BDD 场景

## B1 新建或人工编辑保存不自动置 verified

Given 工作台中一条未核验（`isVerified == false`）的规则，
When 用户通过表单进行人工编辑并点击保存，
Then 该规则保存后 `isVerified` 依然保持为 `false`，不被自动提升为已核验状态。

## B2 AI 产物保存强制降级为未核验（candidate 态）

Given 一条此前已通过人工核验（`isVerified == true`）的规则，
When 通过 AI 识别条件对话框并选择保存 AI 生成的 conditions，
Then 保存后该规则的 `isVerified` 被强制置为 `false`，降级为候选态，等待人工重新审核。

## B3 显式人工勾选通道依然有效

Given 用户在规则列表界面的“手动校验”列操作复选框，
When 用户主动将某条规则勾选为已核验，
Then 该规则的 `isVerified` 正确更新为 `true`，保护现有合法通道不被破坏。

## B4 代码与依赖最小化

Given 工作台现有架构，
When 完成上述改动后，
Then 全仓无需新增任何 pub 依赖，不修改表结构与持久化层。
