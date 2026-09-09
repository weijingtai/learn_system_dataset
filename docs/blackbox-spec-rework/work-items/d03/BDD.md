# D-03 BDD 验收场景

## B1 人工队列与恢复

Given 一本书的一个阶段产生多个人工决定，When 阶段等待、逐条登记决定并恢复，Then 全程属于同一个 StepRun，决定以不可变 Artifact Revision 写入 Ledger，恢复只读取冻结输入与显式事件。

## B2 防重复恢复

Given StepRun 处于 `awaiting_human`，When 使用绑定当前 `step_run_id` 与 `status_version` 的 token 恢复，Then token 原子消费；再次使用或跨版本使用必须失败。

## B3 deadline

Given 人工队列超过提醒期限，When 无人处理，Then系统只提醒，不自动失败、放行或清空队列。

## B4 两种暂停

Given 一个任务等待人工，另一个任务因可恢复系统故障停止，Then 前者为 `awaiting_human`，后者为 `suspended`，二者不得混用。

## B5 Ledger 不可用

Given Ledger 不可持久写入，When 模块产生新输出，Then 不得声称 `suspended` 已记录，也不得继续接受输出；恢复必须从最后耐久状态续接。

## B6 终态与重跑

Given StepRun 已进入终态，When 需要重跑，Then 旧记录不可改写，新建 `step_run_id`，并用 `supersedes_step_run_id` 建立关联。

## B7 双状态轴

Given Artifact 生命周期与内容成熟度同时存在，Then `draft/sealed/...` 不得替代 `source_verified/machine_extracted/...`，两者正交。

## B8 单机无身份系统

Given 当前为单人单机，Then `resume_token` 仅承担状态机防重放，不引入用户身份、会话或权限设计。

