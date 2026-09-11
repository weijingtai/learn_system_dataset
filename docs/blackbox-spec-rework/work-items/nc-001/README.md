# NC-001：工程基线开工包

状态：PREPARING。只交付 NC-001-01 本地规划基线的验证工具；NC-001 总项尚未 READY/ACCEPTED。依据：TASKS NC-001、INTEGRATION_BASELINE.md §6（本轮范围裁定）；书籍工作按用户最新指令暂缓。

## Goal

让下一位执行者机械验证“哪些本地决定已落实、哪些外部能力仍未验证”，禁止将计划目录或静态证据当成运行成功。

## Inputs

仓库根 `/Users/jingtaiwei/Git/Public/learn_system`；输入 `openspec/annotation-community/INTEGRATION_BASELINE.md` 与 `integration_baseline.json`，以及 PRD/DESIGN/PLANS/TASKS v1.5、openspec/subagent-delivery-gate.md。这些输入只读；不要求执行者重新选包/设计身份。

## Scope

只新建 `openspec/annotation-community/tools/check_integration_baseline.py` 与 `test_check_integration_baseline.py`；用 Python 标准库 argparse/json/pathlib/unittest/tempfile，不安装依赖。测试输出写临时目录。不得修改本包、输入JSON、既有守卫、HANDOFF/PLAN、任何外部仓库。

## Dependencies / Baseline

父目录存在、CLIENT=PLANNED_NEW且创建归NC-004；当前没有 checker；Red 按 TDD §4 用空壳取得真实断言失败，文件不存在导致的退出 2 不算 Red。外部测试均未运行；不把本包通过声称成它们通过。

开工基线（提交 `aadd1fc` 实测，执行者不必重验）：`LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`=0、`bash openspec/annotation-community/verify.sh`=0、`git diff --check`=0、`bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh`=0（K08 为 SKIP）。前两条守卫读取共享文件 `docs/blackbox-spec-rework/SUBAGENT_TODO.md`，`git diff --check` 覆盖整个共享工作树；并行的 G3 线随时可能改动它们。执行者遇这三条失败时先 `git diff --stat`，失败来源不在本任务两个文件之内的判为外部失败，只记录、不返工、不停工。

## Stop Conditions

输入JSON与调查证据矛盾、契约存在两种以上解释、执行需越过读写范围、需要访问真实云或身份凭据、标准库不可用均停止并报告。执行者不核对仓库 HEAD 是否仍为采样值，HEAD 新鲜度由 NC-001-02 重新取证。NC-001-02 联调工作另行准备；其十项缺口不能由本执行者临时设计/填值。

## Deliverables

精确两文件，按 act/01 → act/02 → act/03 → act/04 分四个提交，每步交付 Red/Green 原始输出。`--profile local` 是 LOCAL_PREPARATION_PASS；`--profile integrated` 对现有未验证快照必须失败。只有后续真实联调基线通过才能申请NC-001整项验收。

## 一次性交付与阅读顺序

1. 本 README：边界与状态。
2. [BDD](BDD.md)、[TDD](TDD.md)、[校验字段契约](VALIDATION_CONTRACT.md)：行为、反例和判据。
3. [ACT](ACT.yaml) 及 [act/01](act/01.yaml)、[act/02](act/02.yaml)、[act/03](act/03.yaml)、[act/04](act/04.yaml)：分四步只写两个工具文件；[PROMPT](PROMPT.md) 待 READY 后原样发送。
4. [ACCEPTANCE](ACCEPTANCE.md)：独立复核与验收。
5. [剩余交付清单](REMAINING_DELIVERABLES.md)：完整 NC-001 尚缺的十项证据、责任和后续文档。

R2 返工（[NC-001-REVIEW-R2](../../reviews/NC-001-REVIEW-R2.md)）已落实：契约歧义裁定、必填键全表、类型/枚举负例、四步拆分、共享守卫外部失败规则。v1.5 已同步第十项；未验证事实以 UNVERIFIED/null 记录，不由执行者猜值。文档齐备不等于 READY；本包不包含业务代码实施授权。

校验器必须显式传入 --profile；不得把 local 命令写成 TASKS NC-001 的总项验收命令。总项要求实际 CLIENT 存在与完整证据，本地 profile 的 PLANNED_NEW 放行只适用于 NC-001-01。
