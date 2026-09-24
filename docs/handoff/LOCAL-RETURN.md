# 交还本地（2026-09-24，云端 Claude → 本地主 Agent）

> 用户决定：T03c 剩余部分与 T04 **交还本地 Claude Code** 继续做。Jules 已停用（原因见下）。
> 读完本文件后，照旧以仓库根 `TODO.md` 为唯一待办入口。

## 一、先把云端的提交拉到本地

云端工作都在 GitHub 仓库 `weijingtai/learn_system_dataset` 的分支 **`claude/wizardly-maxwell-pqrzh9`**（基于 `main` = `f4df613`）。本地工作树若没有 GitHub 远端，先加一个：

```bash
git remote add github https://github.com/weijingtai/learn_system_dataset.git   # 已有则跳过
git fetch github claude/wizardly-maxwell-pqrzh9
git switch -c t03c-local github/claude/wizardly-maxwell-pqrzh9      # 或按本地惯例在自己分支上 merge（不 rebase）
```

**不要用** `run-web-app-preview-14224512467231758506` 分支上的 `b637aee`：那是 Jules 的空提交（文件树与父提交相同，没改任何代码），见 `docs/jules/CHANNEL.md`。

## 二、T03c 现状（111 处后门，已清 30 处）

| 包 | 命中 | 状态 | 提交 |
|---|---|---|---|
| intake（M1） | 3 | 清零 | `c099512` |
| digitization（M2） | 5 | 清零 | `0ecf5dc` |
| knowledge_extraction（M4） | 22 | 清零 | `a1ed93a` |
| assembly（M7） | 28 | **待做** | — |
| review（M6） | 53 | **待做** | — |

- 做法、端口新增方法、排序如何保持不变、每步的测试原文与篡改探针：`docs/jules/T03c.report.md`。
- 剩余两包的完整指引（现成端口方法清单、排序规则、缺查询时怎么补）：`docs/jules/T03c-remaining.md`——原写给 Jules，本地照用即可；其中「从哪个分支拉」「开 PR」两条按本地惯例处理。
- 原任务书与禁止事项：`docs/jules/T03c.md`。
- 端口已新增 7 个只读方法（`latest_processing_run`、`latest_checkpoint_step_run`、`list_revisions`、`list_human_events`、`list_transformation_inputs/outputs/human_events`），用例 `pipeline/ledger/tests/test_read_queries_t03c.py`；继续新增时把方法名加进其中的 `T03C_METHODS`。

## 三、要停下来问用户的一处

`pipeline/assembly/inputs.py:173` 的回退查询用了 `transformations.output_artifact_revision_id`，**该列不存在**（输出在 `transformation_outputs` 表），走到这里会抛 `sqlite3.OperationalError`。既有缺陷，修法会改变行为，须用户裁决。候选：(a) `describe_revision(候选包)['step_run_id']` → `get_step_run`；(b) 改查 `transformation_outputs`；(c) 暂保留（守护用例会红）。先写用例证明现状。

## 四、本地比云端多能做的验证

云端没有页图、没有真书账本，所以有 6 条已知红（T14）和 38 条 skip（dataset_compiler 36、assembly 2）。**本地请在 M1/M2/M4 的三个提交上补跑一遍 11 个包**，确认在有页图、有真书账本时也不比本地基线多红或多 skip——云端验证不到这部分。

云端环境另发现：缺 `en_US.UTF-8` locale 与 `sqlite3` 命令行会多 2 条假红（已入 `TODO.md` T15）。本地 macOS 一般不受影响。

## 五、之后的顺序

T03c 完成并合入 → T04（`wip/t04a-handoff`、`wip/t04b-handoff`，裁决 `docs/handoff/t04a-ruling1.md`，现场说明 `docs/handoff/CLOUD-HANDOFF.md` 第二节）→ `TODO.md` 其余条目。
