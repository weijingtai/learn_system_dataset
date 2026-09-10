# NC-001：工程基线开工包

状态：PREPARING。只交付 NC-001-01 本地规划基线的验证工具；NC-001 总项尚未 READY/ACCEPTED。依据：TASKS NC-001、INTEGRATION_BASELINE.md §6（本轮范围裁定）；书籍工作按用户最新指令暂缓。

## Goal

让下一位执行者机械验证“哪些本地决定已落实、哪些外部能力仍未验证”，禁止将计划目录或静态证据当成运行成功。

## Inputs

仓库根 `/Users/jingtaiwei/Git/Public/learn_system`；输入 `openspec/annotation-community/INTEGRATION_BASELINE.md` 与 `integration_baseline.json`，以及 PRD/DESIGN/PLANS/TASKS v1.4、openspec/subagent-delivery-gate.md。这些输入只读；不要求执行者重新选包/设计身份。

## Scope

只新建 `openspec/annotation-community/tools/check_integration_baseline.py` 与 `test_check_integration_baseline.py`；用 Python 标准库 argparse/json/pathlib/unittest/tempfile，不安装依赖。测试输出写临时目录。不得修改本包、输入JSON、既有守卫、HANDOFF/PLAN、任何外部仓库。

## Dependencies / Baseline

父目录存在、CLIENT=PLANNED_NEW且创建归NC-004；当前没有 checker，因此初始命令应退出2并显示文件不存在，不算行为Red。真正Red由下述测试针对未实现checker的返回与诊断建立。外部测试均未运行；不把本包通过声称成它们通过。

## Stop Conditions

输入JSON与调查证据矛盾、输入基线的HEAD字段发生变化、执行需越过读写范围、需要访问真实云或身份凭据、标准库不可用均停止并报告。NC-001-02 联调工作另行准备；其九项缺口不能由本执行者临时设计/填值。

## Deliverables

精确两文件、每项成对测试、Red/Green原始输出和单独commit。`--profile local` 是 LOCAL_PREPARATION_PASS；`--profile integrated` 对现有未验证快照必须失败。只有后续真实联调基线通过才能申请NC-001整项验收。
