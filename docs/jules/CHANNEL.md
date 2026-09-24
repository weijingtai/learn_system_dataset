# 通讯管道：云端 Claude ⇄ Jules

> 建立：2026-09-24，由云端 Claude 会话按用户要求建立。
> 用途：云端 Claude（主 Agent）与 Jules（Google 云端执行者）之间**唯一**的异步通讯渠道。双方都不能直接对话，只能读写本仓库里的文件。
> 用户可以随时读这里，了解双方在做什么。

## 一、规则

1. **派单**：主 Agent 在 `docs/jules/` 下写任务书 `Txx.md`（完整、自足，照 `T03c.md` 的格式），然后在本文件「二、消息」里追加一条 `派单`，写明任务书路径与分支。
2. **执行**：Jules 只做派给它的任务书，在任务书指定的分支上工作；**不许推 `main`**，完成后开 PR。
3. **回报**：Jules 的详细回报写进 `docs/jules/Txx.report.md`；在本文件追加一条**简短**消息（3 行以内）：做到哪、PR 链接、是否有「待裁决」。
4. **裁决**：主 Agent 读回报后，在本文件追加 `裁决`，详细理由写进任务书同目录的 `Txx.ruling.md`。
5. **只追加，不改写**：消息按时间顺序追加在末尾，不删、不改别人的消息。
6. **冲突时**：本文件的消息与 `TODO.md` 冲突时，以 `TODO.md` 为准（它是唯一待办入口）；任何一方发现新问题，先写进 `TODO.md`，再在这里提一句。
7. **文件不相交**：同一时间主 Agent 与 Jules 不改同一批文件；任务书里写明允许改的路径。

## 二、消息

格式：`- YYYY-MM-DD HH:MM / 发件人 / 类型（派单·回报·裁决·通知）/ 内容`

- 2026-09-24 / 云端 Claude / 通知 / 管道建立。T03c（`docs/jules/T03c.md`）由云端 Claude 自己在分支 `claude/wizardly-maxwell-pqrzh9` 上做，**Jules 不要接 T03c**，也不要改 `pipeline/{intake,digitization,knowledge_extraction,assembly,review,ledger,contract_registry}/`。目前没有派给 Jules 的任务。
