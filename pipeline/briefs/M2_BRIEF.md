# M2 任务书：调度脚本（本文件写给执行本任务的 AI agent）

> 先读 `pipeline/AGENT_GUIDE.md`，其六条铁律在本任务中全部适用。
> 本任务只做"脚本能跑通"，**不调用任何真实 API**（真实调用是 M2b，需要用户提供 key）。
> 按步骤 1–6 顺序执行。每步末尾有验证命令，验证不通过不许进入下一步。
> 所有路径相对 `pipeline/` 目录。禁止修改 `corpus/`、`validators/validate.py`、`units/ku_qimen_000001/`。

## 步骤 1：写模型配置 `runner/config.yaml`

内容照抄以下模板（用户之后自己改模型名）：

```yaml
models:
  production:            # 生产模型（干活的）
    provider: deepseek
    endpoint: https://api.deepseek.com/chat/completions
    model: deepseek-chat
    api_key_env: DEEPSEEK_API_KEY   # 从环境变量读 key，禁止把 key 写进任何文件
    temperature: 0
  reviewer:              # 复核模型（必须与生产模型不同家族）
    provider: zhipu
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    model: glm-4-plus
    api_key_env: GLM_API_KEY
    temperature: 0
  mock:                  # 测试用假模型：不联网，直接返回任务包里的 mock_output.yaml
    provider: mock
```

**验证**：`python3 -c "import yaml; yaml.safe_load(open('runner/config.yaml'))"` 无报错。

## 步骤 2：写调度脚本 `runner/run_task.py`

用法：`python3 runner/run_task.py <任务包目录> --model production|reviewer|mock`

脚本必须做且只做这些事：

1. 读任务包目录下的 `task.yaml`、`INSTRUCTIONS.md`、`input/` 里的全部文件；
2. 拼接提示词：INSTRUCTIONS.md 全文 ＋ 分隔线 ＋ input 文件内容；
3. 按 `--model` 选配置：
   - `mock`：不联网，把任务包里 `mock_output.yaml` 的内容当作模型回复；
   - 其他：POST 到 endpoint（OpenAI 兼容格式，`temperature` 用配置值；key 从环境变量读，读不到就报错退出，**不打印 key**）；`requests` 库的 import 写在真实调用的函数内部，保证 mock 模式不装 requests 也能跑；
4. 把结果存到 `<任务包>/output/<model名>_<时间戳>/`：
   - `response.yaml`：模型回复原文；
   - `run.yaml`：运行记录，含 model、endpoint、时间、每个输入文件的 sha256、response.yaml 的 sha256；
5. 只写 `output/` 目录，不改任务包的其他任何文件；
6. 出错时打印一行错误原因并以退出码 1 结束，不留半写的文件。

**验证**：`python3 runner/run_task.py --help` 或无参数运行时打印用法说明。

## 步骤 3：写任务模板 `task-templates/stage3_segmentation/INSTRUCTIONS.md`

这是给做"语义切分"的模型看的说明，必须包含以下规则（可润色但不可删减）：

- 你的唯一任务：把输入的古文按完整语义切成若干段，**一个字都不许改、不许删、不许加**；
- 输出格式（YAML）：`segments:` 列表，每段含 `seg_id`（s01 起顺序编号）、`text`（逐字复制的原文）、`note`（一句话说明为什么在此切分）；
- 所有段落的 text 连起来必须等于输入原文（程序会检查）；
- 无法判断切分点时输出 `status: blocked_missing_context` 并说明缺什么，禁止猜。

同目录放 `task.yaml` 模板（字段：task_id、stage: segmentation、source_snapshot、instruction_version: seg_v0.1）。

**验证**：两个文件存在且 YAML 可解析。

## 步骤 4：建首个任务实例 `tasks/task_qimen_000001_seg/`

- `task.yaml`：按模板填，task_id 为 `task_qimen_000001_seg`；
- `INSTRUCTIONS.md`：从模板复制；
- `input/text.md`：从 `corpus/qimen/yanbo/source/transcript_v1.md` **复制**那四联歌诀正文（复制，不是移动；corpus 不许动）；
- `mock_output.yaml`：手写一份符合步骤 3 输出格式的切分结果（**切分粒度按 HANDBOOK 第 3 章类型 A：按联切，四联 = 4 段**，text 逐字复制），供 mock 测试用。
  【勘误 2026-07-10】本条原写"8 句 = 8 段"，与 HANDBOOK 类型 A 规则冲突，导致首次执行按单句切出半联。教训：任务书不得重述切分规则，只许引用 HANDBOOK 章节——规则只能有一个出处。

**验证**：`ls tasks/task_qimen_000001_seg/` 能看到 4 项。

## 步骤 5：跑通 mock

```
python3 runner/run_task.py tasks/task_qimen_000001_seg --model mock
```

**验证（全部满足才算过）**：
- 退出码 0；
- `tasks/task_qimen_000001_seg/output/mock_*/` 下有 `response.yaml` 和 `run.yaml`；
- `run.yaml` 里有输入文件的 sha256 和 response 的 sha256；
- `git status --short corpus/` 无任何输出（corpus 未被改动）。

## 步骤 6：汇报并停止

输出：本次创建的文件清单、步骤 5 的 run.yaml 内容、遇到的问题。**不要继续做任何额外工作**（不要写真实 API 调用测试、不要建第二个任务、不要改进校验程序）。
