# ACCEPTANCE：impl-01 Artifact Ledger

状态：H1（ACT 00/01/02）`ACCEPTED`（`ba9b68e`、`823bead`、`0dff35d`，见 §5）；H2 `DISPATCHED`（`PROMPT-H2.md`）

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

## 5. 验收记录

### 5.1 H1（2026-09-11，`git archive 0dff35d` 干净树，软链 `.venv`）

执行者上报三点，裁定：① DDL 表数 16 是对的，ACT/TDD 的「15」为主 Agent 数错，已订正；② `from`/`to` 为 Python 关键字，采纳 `from_status`/`to_status`；③ 采纳 `insert_stage_package` 与四个只读 helper（`stage_packages` 表在 contract 内，H2 需用而 ACT 03 scope 不含 `store.py`）。三点已回写 `act/02.yaml`/`TDD.md`。

- 范围：三提交分别 1 / 8 / 6 文件，只含 `commit.add` 路径；无 `var/`、`__pycache__`；`git diff --check` 通过；`.gitignore` +3 行（空行、中文注释、`var/`）。
- 门禁：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` `D16 OK`（R3 已为 `< 43` 才 FAIL）。
- ACT 00 篡改：表 B 追加合法行（44）→ `D16 OK`；删一行（42）→ `FAIL R3 …=42（应 ≥ 43）`。
- ACT 01：`unittest` 26/26；`ids.PATTERNS` 19 项与 ACT 逐字相等；`ARTIFACT_TRANSITIONS`/`STEP_RUN_TRANSITIONS` 与 §8.2 表逐字相等；5×5 与 6×6 迁移穷举结果与表一致；表外取值 `SCH_002`；`ERROR_CODES` 九码逐字；`kind_of` 最长前缀（`co_shared_`、`prun_` 优先）；`pr_`+hex32 冒充 processing_run_id → `ID_001`；`LocalActorProvider` 返回 `local_owner`。
- ACT 02：`sqlite_master` 16 张表逐字；抽查四表列名齐全；外键 20 条；`journal_mode=wal`；`schema_meta` 1.0.0；Object Store 去重、篡改一字节 `verify` False、缺对象 `REF_001`、无 tmp 残留；跨进程第二写入者 `WriterLocked`、释放后可取得；只读连接写入 `OperationalError`；乐观锁过期版本 `IllegalTransition`、成功后 `status_version` 递增；异常事务回滚审计计数不变。
- 质量：导入只有标准库 + 自身包；中文 docstring；测试只用 `tempfile`。
- 主 Agent 自误：验收脚本用 `multiprocessing` 从 stdin 起子进程在 macOS 失败，改为 `subprocess` 复验，与执行者无关。
