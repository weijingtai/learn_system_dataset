# ACCEPTANCE：impl-01 Artifact Ledger

状态：`READY`（H1 待用户交外部 Agent；H2 在 H1 `ACCEPTED` 后派发）

## 0. 转译审查（主 Agent 四查，2026-09-11）

- 忠实性：ACT 01 常量逐字取自规格 §8.1 三表与 §8.2 四表；ACT 03 方法覆盖 §7.1（await/record_human_event/resume、token 单次、无自动超时）、§17（事务序列九步、suspended/recovery 对账、ActorProvider、必记字段）、§17.1（Checkpoint 五条）；ACT 04 对应 D-04 决议（单机本地进程、单写入者、WAL、只读并发）；ACT 05 的 20.2/20.3 判据严格对应 §20 第 2/3 条原文；无新前缀。
- 覆盖性：BDD 1–6 每条对应 ACT `tests` 用例名与 TDD §1 Green 值；假绿由 TDD §2 的篡改/恒真检查覆盖；`run_all.sh` 改动限三处且 BLOCKED 名闭集不变。
- 可执行性：`run_all.sh` 三锚点、`check_d16.py` R3 行、根 `.gitignore`、Python 3.14 + yaml/jsonschema 已由主 Agent 核对（见下）；每个 ACT 有用例名清单、签名、DDL、CLI 用法与退出码；无模糊词；时长 10/40/90/120/60/90 分钟。
- 独立性：H1、H2 串行；ACT 05 对 `service.py` 的追加限一个方法。

派发前核对（主 Agent 脚本，2026-09-11，HEAD `375ff8b` 之后）：`run_all.sh` 三锚点各 1（a2 按脚本实际行 `OK) block_line … ;;` 订正）；`check_d16.py` R3 第 229–230 行为 `!= 43`；根 `.gitignore` 存在且无 `var/`；`var/`、`pipeline/ledger/` 不存在；Python 3.14.6、sqlite 3.53.4、`yaml`/`jsonschema`/`fcntl`/`secrets` 可导入；§19 第一列含「测试宿主匮乏」；fixture 常量（三包 `stage_package_id`/`artifact_revision_id`/`step_run_id`/输出修订/配置修订/operation、`edition_part` `art_…e1`、`technique_id qizheng`、anomalies page_002 `known_unrecognizable`）与 ACT 05 引用一致。

## 1. 范围核对

每个提交只含 ACT `commit.add` 路径；`var/` 与 `pipeline/ledger/tests` 产物不入库；`git diff --check`；fixture、Schema、规格、`.gitignore`（除一行）未动。

## 2. 门禁与判据（干净导出树，软链 `.venv`，`FIXTURE_ASSET_ROOT` 指本机页图）

- 三门禁绿；`unittest` 全过且用例数满足 TDD §1 各阈值；ACT 05 后 `run_all.sh` = `pass=2 fail=1 blocked=8`、exit 1。
- TDD §2 附加判据逐条实跑：签名逐字、状态表逐字、迁移穷举、半成品、篡改 Object、篡改 Ledger 判定、恒真检查、BLOCKED 行名、无新前缀。
- 矩阵外篡改 ≥ 5 例（主 Agent 自定，不预告）。

## 3. 语义与质量审查（主 Agent）

- `service.py` 每个写方法在单个事务内；状态更新走乐观锁；`resume_token` 不落明文；终态不可改写。
- Checkpoint 链跨 StepRun 接链且封存后只允许后继 StepRun 续写；恢复不重做已完成任务。
- `acceptance.py` 每个 PASS 名称都有对应 FAIL 出口；`fixture_ingest` 不读 fixture 之外的文件、不写 fixture。
- `ledgerd` 第二实例退出码 3；SIGTERM 清理。
- 中文注释；无 `except: pass`。

## 4. 结论

H1、H2 各自通过后记 `ACCEPTED`；全部通过后：SUBAGENT_TODO G7 impl-01 `ACCEPTED`、PLAN D-16 节 C「Artifact Ledger」条目勾选（附提交）、HANDOFF 同步；下一批 impl-02（M3 Corpus Compilation 在 Ledger 上的真实编译，目标 `run_all.sh 20.1` 的 fixture 部分）。
