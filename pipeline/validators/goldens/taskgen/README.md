# taskgen 黄金快照

`check_taskgen.py` 的回归基准：工位4/5/6 任务包生成器（经 `tools/lib/taskgen.py`）
应产出的**生成类**文件（`task.yaml` / `segments.yaml` / `spans.yaml`）的 byte 快照。

- 校验：`python3 validators/check_taskgen.py`
- **有意变更产物后**重新采集：`python3 validators/check_taskgen.py --update`

INSTRUCTIONS.md 与 glossary_v0.yaml 不入快照——它们是逐字拷贝，由 check 脚本
另行核对来源（模板经 `resolve_template` 按技法解析、术语表取自 `schemas/techniques/<tech>/`）。

采集用例见 `check_taskgen.py` 的 `CASES`（三工位各一个真实轮次）。改了模板/术语表/
seg 草稿而**无意**改动生成逻辑时，若校验失败，说明上游输入变了，确认无误后 `--update`。
