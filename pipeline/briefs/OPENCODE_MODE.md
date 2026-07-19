# OPENCODE_MODE：无 API key 的工作方式

> 背景：本项目不使用 DeepSeek/GLM 的 API key。模型分工改为：
> **生产模型 = OpenCode**（直接在仓库里干活）；**复核模型 = Claude**（Cowork 会话，不同模型家族）；**仲裁 = 人工**（回答 ESC 选择题）。
> 异构双路的原则不变，只是"调 API"变成"你分别叫两个工具干活"。

## 一、一个任务包的完整走法

```
1. 任务包就绪（TASKS/task_xxx/，含 INSTRUCTIONS、input、task.yaml）
2. 你把下面的启动句粘给 OpenCode        ← 生产
3. OpenCode 写出结果、归档、自跑校验、汇报
4. 你把"复核启动句"粘给 Claude（Cowork）  ← 复核（不同家族）
5. 两边一致 → 通过；分歧 → ESC 选择题给你
```

## 二、给 OpenCode 的启动句（模板，替换任务目录名即可）

> 阅读 pipeline/AGENT_GUIDE.md，然后执行任务包 pipeline/tasks/<任务目录名>：按其中 INSTRUCTIONS.md 完成任务，把结果写到该任务包的 output/draft_opencode.yaml；然后运行 `python3 pipeline/runner/run_task.py pipeline/tasks/<任务目录名> --model manual --from pipeline/tasks/<任务目录名>/output/draft_opencode.yaml --by opencode` 归档；再运行对应校验（切分任务是 `python3 pipeline/validators/check_segments.py pipeline/tasks/<任务目录名> --type <类型>`），把校验结果原样贴出来；FAIL 则按 AGENT_GUIDE 第三节修，最多两次；**收尾必须回填 output/result.yaml 的 uncertainties 与 lesson_candidates 两个字段（本批遇到的括号夹注、标目边界存疑、值得后人避坑的规律都写进去；不许无脑留空数组）**；最后汇报并停止。禁止修改 corpus/、validators/、schemas/。

> ⚠ 教训回流是硬环节，不是可选项：INSTRUCTIONS 开头的"必读 LESSONS"和收尾的"回填 result"缺一不可。曾因 C 类模板漏掉这两环，导致 8 批经验全部丢失（见 LESSONS.md 类型 C 小节末条）。

## 三、给 Claude 的复核启动句（模板）

> 对 pipeline/tasks/<任务目录名> 做独立复核：不看 OpenCode 的结果，先自己从 input/ 原文按 INSTRUCTIONS 做一遍，然后与 output/ 里最新归档结果做结构化比对，一致项列出，分歧项按 HANDBOOK 2.3 出 ESC。

## 四、审计规矩（manual 模式的意义）

OpenCode 的产出必须经 `run_task.py --model manual` 归档，因为归档时会记录：任务 ID、指令版本、输入文件哈希、提示词哈希、结果哈希、执行者名字。**没有归档记录的产出视为不存在**——聊天窗口里的结果不算数（v1.1.1 §7.1）。

## 五、分工边界

| 角色 | 做什么 | 不做什么 |
|---|---|---|
| OpenCode（生产） | 执行任务包、写代码、跑校验 | 不复核自己的产出、不升级 status |
| Claude（复核） | 独立重做＋比对、验收里程碑、修文档流程 | 不替 OpenCode 改产出文件 |
| 你（仲裁） | 答 ESC 选择题、抽查签发、拍板 | 不逐条整理内容 |

## 六、将来有 API key 时

runner 的 production/reviewer 模式已经写好，届时改 config.yaml 里的模型名、设好环境变量即可切回 API 批量模式，任务包和校验完全不变。
