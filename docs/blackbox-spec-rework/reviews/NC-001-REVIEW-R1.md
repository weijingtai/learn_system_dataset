# NC-001 开工包审查 R1（含 v1.5 落实核对）

日期：2026-09-10。审查对象：`cc13a3e`（v1.5 落实）与 `53fd594`（NC-001 开工包）。审查人：Claude（未参与开工包编写）。
本文一次性给出全部问题、原因和逐字修复内容，执行方照做即可，不需要再猜或另行设计。

## 0. 结论

| 对象 | 结论 | 依据 |
|---|---|---|
| v1.5 落实（`cc13a3e`） | **通过** | 以 `8aa4792` 为基线按 FIX_V1_5 重放 40 处替换，9 个目标文件与 `cc13a3e` 逐字节一致，无说明之外的改动；FIX_V1_5.md 与 `review_v1_5_guard.sh` 未被改动；`LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`、`verify.sh`、`git diff --check` 均为 0 |
| NC-001 开工包（`53fd594`） | **不通过，不能标 READY** | 按门禁 §3.2 与 wjt-react 四查：忠实性不过（F1）、覆盖性不过（F2、F3、F4）、可执行性不过（F5～F9）；独立性成立 |

包的方向是对的：两级门禁、如实登记未验证项、不建空目录冒充。问题集中在三处：规格没跟着改；机器基线只覆盖十项中的一半；输出格式没定死，执行者只能自己设计。

## 1. 问题清单

| 编号 | 级别 | 位置 | 错在哪里 | 为什么必须改 | 修复 |
|---|---|---|---|---|---|
| F1 | P1 | TASKS NC-001 第 4、5 条 | TASKS 仍写「无参数运行 `check_integration_baseline.py` 退出 0」、读 `INTEGRATION_BASELINE.md`、CLIENT 根路径必须存在；开工包改成必传 `--profile`、读 JSON、local 档允许计划目录 | 门禁 §3.2 第 5 条：ACT 不得改变验收标准。照 TASKS 的总项命令运行，会因缺 `--profile` 退出 2；两处真源互相矛盾 | 替换 1～3 |
| F2 | P1 | `integration_baseline.json`、VALIDATION_CONTRACT | TASKS 要求的十项只登记了一半：缺 ② project_id、命名空间前缀、凭据注入方式；③ Emulator 启动方式；④ 各仓是否允许写入；⑤ 验证器安装方式与离线失败行为；⑥ Markdown 选型依据与离线策略；⑧ 通知表现层选择；⑨ 静音/聚合。端口的「文件:符号」完全没有机器登记 | TASKS 红条件是「十项任一缺失」「任一端口缺文件:符号」，而输入里根本没有这些字段，校验器无从检查，等于把红条件静默删掉 | 整文件 1、2 |
| F3 | P1 | VALIDATION_CONTRACT 公共规则第 2 条 | scope 只允许 `LOCAL_PREPARATION`/`TEST_FIXTURE`；测试夹具与真实输入通过时都输出 `INTEGRATED_STRUCTURE_PASS` | 真实联调完成后，基线没有合法的 scope 值，NC-001-02 永远过不了；夹具通过和真实通过在输出上无法机械区分 | 整文件 2（§2、§6） |
| F4 | P1 | VALIDATION_CONTRACT「输出」、TDD 命令 3 | 数组记录的错误路径怎么写（`repositories[?]`）没定义；状态不合格时还要不要继续报证据字段没定义；命令 3 只要求「至少包含」6 个路径，漏了 emulator、openapi、client、sdk、account_deletion 等 | 执行者必须自己设计输出，验收也无法逐字比对，写一条永真断言就能过 | 整文件 2（§4 状态闸门、§6 路径写法、§7 期望 23 行）、整文件 4 |
| F5 | P2 | VALIDATION_CONTRACT 第 9、11 行；ACT.yaml RULES 第 31、33 行 | 「当前 JSON 内的子字段均必填」「pins must match approved input」「all required fields defined by input」 | 判据取自被检查的输入本身：从 JSON 删掉一个键，对这个键的要求也跟着消失 | 整文件 2（逐键列出、版本逐项写死）、整文件 5～7 |
| F6 | P2 | VALIDATION_CONTRACT integrated 表 | `repositories[].tests` 要求 SPEC 为 PASSED，`integration.test_runs` 却只要求 6 个仓库、不含 SPEC | 两条规则互相矛盾，执行者只能自选其一 | 整文件 2（test_runs 7 条） |
| F7 | P2 | ACT.yaml | 单个 ACT 估 45 分钟，实际需要实现约 40 条规则、写 20 个以上测试方法 | 超出门禁 30–60 分钟粒度；便宜模型一次做不完，容易半途留下假绿 | 整文件 5～7（拆成 act/01、act/02） |
| F8 | P2 | PROMPT.md | 标为「草稿」，缺门禁 §3.2 第 8 条要求的验证命令、提交消息与交付证据格式 | READY 后仍需人工补写才能发送，等于没有 Prompt | 整文件 8 |
| F9 | P2 | INTEGRATION_BASELINE §1、REMAINING_DELIVERABLES | `reading-notes` 位于非 Git 父目录，基线把「新仓库还是子模块」推给 NC-004 决定 | NC-004 执行者只能现场设计版本控制归属，违反门禁「不要求执行者自行设计」 | 整文件 1（client.vcs）、替换 4、17 |
| F10 | P3 | INTEGRATION_BASELINE §2 | 3 处行号指错：`database_provider.dart:26` 实为 `final StackTrace? stackTrace;`（类在第 33 行）；`mention_input_enhancer.dart:16` 是 import（类在第 24 行）；`conftest.py:8` 是空行（`_emulator_env` 在第 11 行） | 证据不可复核；行号随提交漂移，TASKS 本就要求「文件:符号」 | 替换 5～8；机器登记改用文件与符号（整文件 1） |
| F11 | P3 | README Stop Conditions | 「输入基线的 HEAD 字段发生变化」 | 执行者被禁止修改输入、也不得扫描 Git，这个条件既不会发生也无法判定 | 替换 10 |
| F12 | 事实补录 | ⑩ 注销事件 | 包内只登记「未验证」 | 已查到现状（见 §4），先记下，免得 NC-001-02 重复调查 | 替换 9、18 |

## 2. 执行方式

- 路径一律**相对仓库根** `/Users/jingtaiwei/Git/Public/learn_system`（与 FIX_V1_4/V1_5 相对 annotation-community 不同）。
- 先做 §3.1 的 8 个整文件：用代码块内容完整覆盖目标文件，目标不存在则新建；代码块内容之后保留一个换行作为文件结尾。
- 再做 §3.2 的 18 处逐字替换：原文在目标文件中恰好出现一次，替换为给出的文字。
- 完成后运行 §5 的命令，全部为 0 才算完成。

## 3. 修复内容

### 3.1 整文件（8 个）

**整文件 1**｜文件：`openspec/annotation-community/integration_baseline.json`

````text
{
  "schema_version": 1,
  "spec_version": "1.5",
  "task_id": "NC-001",
  "scope": "LOCAL_PREPARATION",
  "book_work": "DEFERRED_BY_USER",
  "client": {
    "path": "/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes",
    "package": "reading_notes",
    "state": "PLANNED_NEW",
    "creation_owner": "NC-004",
    "vcs": "NEW_GIT_REPOSITORY",
    "runtime_verified": false
  },
  "sdk": {
    "flutter": "3.44.6",
    "dart": "3.12.2",
    "evidence": "/Users/jingtaiwei/flutter/bin/cache/flutter.version.json",
    "verification": "CACHE_METADATA_ONLY"
  },
  "dependencies": {
    "flutter_markdown_plus": "1.0.12",
    "drift": "2.31.0",
    "drift_dev": "2.31.0",
    "drift_flutter": "0.2.8",
    "sqlite3": "2.9.4",
    "sqlite3_flutter_libs": "0.5.42",
    "path_provider": "2.1.6",
    "build_runner": "2.15.1"
  },
  "dependency_policy": {
    "offline_failure": "ENV_BLOCKED",
    "flutter_markdown_plus_rationale": "用户指定 flutter_markdown_plus；只负责 Markdown 渲染，编辑使用 Flutter 文本输入与撤销适配"
  },
  "resolution_status": "NOT_RUN",
  "resolution_evidence": null,
  "repositories": [
    {
      "name": "SPEC",
      "path": "/Users/jingtaiwei/Git/Public/learn_system",
      "git_root": "/Users/jingtaiwei/Git/Public/learn_system",
      "head": "7dd2e5f977b95a9e1b7155ef20e648a16fe96e55",
      "dirty_entries": 14,
      "write_policy": "PER_TASK_WHITELIST",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    },
    {
      "name": "MIGRATION",
      "path": "/Users/jingtaiwei/Git/Public/xuan-migration",
      "status": "UNAVAILABLE",
      "write_policy": "READ_ONLY"
    },
    {
      "name": "STORAGE",
      "path": "/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage",
      "git_root": "/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage",
      "head": "87f0ee514ca4255909901f27f4f4a55301fb20b9",
      "dirty_entries": 0,
      "write_policy": "PER_TASK_WHITELIST",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    },
    {
      "name": "SOCIAL",
      "path": "/Users/jingtaiwei/Git/Public/xuan-migration/social",
      "git_root": "/Users/jingtaiwei/Git/Public/xuan-migration/social",
      "head": "1971f79320ba679daf9be9e89d13a221eae6ff88",
      "dirty_entries": 0,
      "write_policy": "PER_TASK_WHITELIST",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    },
    {
      "name": "NOTIFICATION",
      "path": "/Users/jingtaiwei/Git/Public/xuan-migration/notification",
      "git_root": "/Users/jingtaiwei/Git/Public/xuan-migration/notification",
      "head": "e8cee528ff6aabe6bca744e546ffbe4f25cb02a7",
      "dirty_entries": 0,
      "write_policy": "PER_TASK_WHITELIST",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    },
    {
      "name": "REST",
      "path": "/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter",
      "git_root": "/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter",
      "head": "0f8bf521a421592284e02fe0cd578b6db34ef439",
      "dirty_entries": 0,
      "write_policy": "PER_TASK_WHITELIST",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    },
    {
      "name": "SERVER",
      "path": "/Users/jingtaiwei/Git/Public/xuan-server/functions-py",
      "git_root": "/Users/jingtaiwei/Git/Public/xuan-server/functions-py",
      "head": "866ea138c2a5b51e9fa5d4280568e78308090d63",
      "dirty_entries": 0,
      "write_policy": "PER_TASK_WHITELIST",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    },
    {
      "name": "NOTIFIER",
      "path": "/Users/jingtaiwei/Git/Public/xuan-server/notifier",
      "git_root": "/Users/jingtaiwei/Git/Public/xuan-server/notifier",
      "head": "8f32132c245598e23ece1d28f5090b094e0c8037",
      "dirty_entries": 0,
      "write_policy": "READ_ONLY",
      "tests": {
        "status": "NOT_RUN",
        "reason": "只读源码调查，未执行运行基线"
      }
    }
  ],
  "ports": [
    {
      "name": "HOST_INIT",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/xuan-shell/lib/app/xuan_shell_dependencies.dart",
      "symbol": "XuanShellDependencies.create",
      "kind": "EXISTING_IMPLEMENTATION"
    },
    {
      "name": "ACCOUNT_SCOPE",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage/drift/lib/scope/scope_resolver.dart",
      "symbol": "ScopeResolver",
      "kind": "EXISTING_IMPLEMENTATION"
    },
    {
      "name": "HTTP",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/lib/src/rest_storage_driver.dart",
      "symbol": "RestStorageDriver",
      "kind": "NEW_ADAPTER"
    },
    {
      "name": "STORAGE",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage/drift/lib/record/drift_record_data_source.dart",
      "symbol": "DriftRecordDataSource",
      "kind": "NEW_ADAPTER"
    },
    {
      "name": "IM_NAVIGATION",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/social/lib/src/profile/public_profile_page.dart",
      "symbol": "PublicProfilePage.onStartChat",
      "kind": "NEW_ADAPTER"
    },
    {
      "name": "MENTION",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/social/lib/src/mention/mention_input_enhancer.dart",
      "symbol": "MentionInputEnhancer.onInsert",
      "kind": "NEW_ADAPTER"
    },
    {
      "name": "NOTIFICATION_RECEIVE",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/notification/lib/src/receive/receive_pipeline.dart",
      "symbol": "ReceivePipeline.handleDelivery",
      "kind": "EXISTING_IMPLEMENTATION"
    },
    {
      "name": "SERVER_IDENTITY",
      "file": "/Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/identity.py",
      "symbol": "resolve_app_user_id",
      "kind": "EXISTING_IMPLEMENTATION"
    }
  ],
  "identity": {
    "policy": "HOST_SCOPE_ONLY",
    "new_identity_system": false,
    "public_profile_id": "PlaygroundUserId；不是 Firebase uid，也不是 appUserId"
  },
  "openapi_validator": {
    "package": "openapi-spec-validator",
    "version": "0.9.0",
    "install_command": "python3 -m venv openspec/annotation-community/.venv-openapi && openspec/annotation-community/.venv-openapi/bin/python -m pip install openapi-spec-validator==0.9.0",
    "offline_failure": "ENV_BLOCKED",
    "status": "NOT_INSTALLED_IN_CURRENT_PYTHON",
    "evidence": null
  },
  "integration": {
    "devices": [],
    "account_pairs": [],
    "backend": {
      "status": "UNVERIFIED",
      "project_id": null,
      "namespace_prefix": null,
      "credential_injection": null,
      "evidence": null
    },
    "emulator": {
      "firestore_config": "192.168.0.165:8080",
      "auth_config": "192.168.0.165:9099",
      "project_config": "demo-xuan",
      "status": "CONFIG_ONLY_NOT_CONTACTED",
      "start_command": null,
      "evidence": null
    },
    "rules": {
      "status": "UNVERIFIED",
      "path": null,
      "evidence": null
    },
    "notifier_binding": {
      "status": "UNVERIFIED",
      "evidence": null
    },
    "notification_presentation": {
      "choice": "SOCIAL_NOTIFICATION_CENTER",
      "file": "/Users/jingtaiwei/Git/Public/xuan-migration/social/lib/src/notification/notification_center_page.dart",
      "symbol": "NotificationCenterPage",
      "status": "UNVERIFIED",
      "evidence": null
    },
    "mute_aggregation": {
      "status": "UNVERIFIED",
      "content_mute": null,
      "aggregation": null,
      "evidence": null
    },
    "test_runs": [],
    "account_deletion": {
      "status": "UNVERIFIED",
      "source": null,
      "delivery_semantics": null,
      "test_command": null,
      "exit_code": null,
      "count": null,
      "evidence": null,
      "consumer": "NC-026",
      "blocked_scope": "NC-026_ACCOUNT_DELETION"
    }
  }
}
````

**整文件 2**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md`

````text
# NC-001-01 校验字段契约

状态：PREPARING（R1 返工版，见 [NC-001-REVIEW-R1](../../reviews/NC-001-REVIEW-R1.md)）。这是 `openspec/annotation-community/tools/check_integration_baseline.py` 的输入契约，不是业务 REST Schema。权威规格为 PRD/DESIGN/TASKS v1.5 与 TASKS NC-001。本文列出的键、枚举与固定值就是全部判据：执行者不得从输入 JSON 反推必填项，也不得自行增删。

## 1. 读取范围

- 输入 JSON 由 `--input` 指定；同目录的 `INTEGRATION_BASELINE.md` 一并读取。
- JSON 中的相对路径相对于输入 JSON 所在目录解析，绝对路径保持原值。
- 对外部路径只判断存在性（exists / is_file / is_dir），不读取外部文件内容、不执行 Git、不读取凭据；唯一读取内容的文件是输入 JSON 与同目录的 `INTEGRATION_BASELINE.md`。
- 两种 profile 都不得写文件或创建目录。

## 2. 顶层（两种 profile 共同）

| 路径 | 规则 |
|---|---|
| （根） | object |
| schema_version | 整数 1，bool 不接受 |
| spec_version | 字符串 `1.5` |
| task_id | 字符串 `NC-001` |
| scope | `LOCAL_PREPARATION` / `INTEGRATED` / `TEST_FIXTURE` |
| book_work | `DEFERRED_BY_USER` |
| resolution_status | `NOT_RUN` / `RESOLVED` |
| resolution_evidence | 键必须存在；NOT_RUN 时为 null，RESOLVED 时为存在的文件 |
| client、sdk、dependencies、dependency_policy、identity、openapi_validator、integration | object |
| repositories、ports | array |

## 3. 对象规则（两种 profile 共同）

**client**：path 非空字符串；package=`reading_notes`；state ∈ `PLANNED_NEW` / `EXISTING`；creation_owner 为字符串；vcs=`NEW_GIT_REPOSITORY`；runtime_verified 为 bool。
- PLANNED_NEW：creation_owner≠`NC-004` 报 `client.creation_owner`；path 的父目录不存在报 `client.path`；path 本身已存在报 `client.state`（防止建空目录冒充）。
- EXISTING：`<path>/pubspec.yaml` 不是文件、`<path>/lib` 不是目录、`<path>/.git` 不存在，任一成立报 `client.path`。

**sdk**：flutter=`3.44.6`；dart=`3.12.2`；evidence 为存在的文件；verification ∈ `CACHE_METADATA_ONLY` / `RUNTIME_VERIFIED`。

**dependencies**：恰好下列 8 个键，值逐字相等。多出键报 `dependencies`；缺键或值不等报 `dependencies.<键>`。

| 键 | 值 |
|---|---|
| flutter_markdown_plus | 1.0.12 |
| drift | 2.31.0 |
| drift_dev | 2.31.0 |
| drift_flutter | 0.2.8 |
| sqlite3 | 2.9.4 |
| sqlite3_flutter_libs | 0.5.42 |
| path_provider | 2.1.6 |
| build_runner | 2.15.1 |

**dependency_policy**：offline_failure=`ENV_BLOCKED`；flutter_markdown_plus_rationale 为非空字符串。

**identity**：policy=`HOST_SCOPE_ONLY`；new_identity_system 为 false（bool）；public_profile_id 为非空字符串。

**repositories**：name 恰为 SPEC、MIGRATION、STORAGE、SOCIAL、NOTIFICATION、REST、SERVER、NOTIFIER 各一次，集合不符报 `repositories`。每条 path 非空；write_policy ∈ `READ_ONLY` / `PER_TASK_WHITELIST`。
- MIGRATION：status=`UNAVAILABLE`，write_policy=`READ_ONLY`，不要求 git_root、head、tests。
- 其余 7 条：git_root 非空；head 为 40 位小写十六进制；dirty_entries 为非负整数（bool 不接受）；tests 为 object；tests.status ∈ `NOT_RUN` / `PASSED` / `FAILED`；NOT_RUN 时 tests.reason 非空。
- NOTIFIER 的 write_policy 必须为 `READ_ONLY`。

**ports**：name 恰为 HOST_INIT、ACCOUNT_SCOPE、HTTP、STORAGE、IM_NAVIGATION、MENTION、NOTIFICATION_RECEIVE、SERVER_IDENTITY 各一次，集合不符报 `ports`。每条：file 为存在的文件；symbol 匹配 `^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$`（纯行号、`文件:行` 均拒绝）；kind ∈ `EXISTING_IMPLEMENTATION`（直接调用既有实现）/ `NEW_ADAPTER`（CLIENT 或 SERVER 新增适配层后使用该符号）。符号是否真在文件中由主线程守卫核对，本工具不读外部文件内容。

**openapi_validator**：package=`openapi-spec-validator`；version=`0.9.0`；install_command 非空；offline_failure=`ENV_BLOCKED`；status ∈ `NOT_INSTALLED_IN_CURRENT_PYTHON` / `VERIFIED`；evidence 键存在，未验证态时为 null。

**integration 下的对象**：表中键必须全部存在。status 为未验证态时，验证字段必须全为 null，否则报该字段路径（防止半填冒充）。

| 对象 | 未验证态 / 验证态 | 验证字段 | 常驻字段 |
|---|---|---|---|
| integration.backend | UNVERIFIED / VERIFIED | project_id、namespace_prefix、credential_injection、evidence | — |
| integration.emulator | CONFIG_ONLY_NOT_CONTACTED / VERIFIED | start_command、evidence | firestore_config、auth_config、project_config 为非空字符串 |
| integration.rules | UNVERIFIED / VERIFIED | path、evidence | — |
| integration.notifier_binding | UNVERIFIED / VERIFIED | evidence | — |
| integration.notification_presentation | UNVERIFIED / VERIFIED | evidence | choice ∈ SOCIAL_NOTIFICATION_CENTER / NOTIFICATION_PACKAGE_PAGE；file 为存在的文件；symbol 同 ports 规则 |
| integration.mute_aggregation | UNVERIFIED / VERIFIED | content_mute、aggregation、evidence | — |
| integration.account_deletion | UNVERIFIED / VERIFIED | source、delivery_semantics、test_command、exit_code、count、evidence | consumer=`NC-026`；blocked_scope=`NC-026_ACCOUNT_DELETION` |

integration.devices、integration.account_pairs、integration.test_runs 为 array，local 允许空数组。

**INTEGRATION_BASELINE.md**：必须存在；含 `TBD` 或 `待定`（区分大小写）即报 `INTEGRATION_BASELINE.md`。不扫描 `?`，因为正文中的 URL 与中文问句会误报。

## 4. integrated 增量规则

integrated 先执行 §2～§3，再执行下表。

**状态闸门**：对象的 status 不是验证态时，只报 `<对象>.status`，不再报该对象的验证字段；status 为验证态时，逐个报不合格的验证字段。

| 路径 | 通过条件 |
|---|---|
| scope | `INTEGRATED` 或 `TEST_FIXTURE` |
| client.state | `EXISTING` |
| client.runtime_verified | true |
| sdk.verification | `RUNTIME_VERIFIED` |
| resolution_status | `RESOLVED` |
| integration.backend | VERIFIED；project_id 非空；namespace_prefix 匹配 `^nc_[0-9]{8}_[0-9a-f]{4,12}$`；credential_injection=`RUNTIME_ENV_VAR`；evidence 为存在的文件 |
| integration.emulator | VERIFIED；start_command 非空；evidence 为存在的文件 |
| integration.rules | VERIFIED；path 与 evidence 均为存在的文件 |
| integration.notifier_binding | VERIFIED；evidence 为存在的文件 |
| integration.notification_presentation | VERIFIED；evidence 为存在的文件 |
| integration.mute_aggregation | VERIFIED；content_mute 与 aggregation 各自 ∈ SUPPORTED / UNSUPPORTED_E_WIRING；evidence 为存在的文件 |
| integration.account_deletion | 见 §5 |
| openapi_validator | VERIFIED；evidence 为存在的文件 |
| integration.devices | 至少 2 条；每条 device_id、platform、os_version 非空，p2p_peer 为 bool；device_id 互不相同；至少一条 p2p_peer=true。任一不满足只报 `integration.devices` |
| integration.account_pairs | 至少 2 条；每条 uid、app_user_id 非空，两列各自不重复；任一条含 token 或 password 键即不合格。任一不满足只报 `integration.account_pairs` |
| integration.test_runs | repository 恰为 SPEC、STORAGE、SOCIAL、NOTIFICATION、REST、SERVER、NOTIFIER 各一条，集合不符只报 `integration.test_runs`；集合相符时逐条按执行证据规则报 `integration.test_runs[<名>].<字段>` |
| repositories[<名>].tests（MIGRATION 除外） | status 不是 PASSED 只报 `.status`；PASSED 时按执行证据规则报 `repositories[<名>].tests.<字段>` |

**执行证据规则**：command 为非空字符串；exit_code 为整数 0（bool 不接受）；count 为正整数（bool 不接受）；evidence 为存在的文件。结构检查不能证明命令真的执行过，独立验收者必须核对原始输出。

## 5. account_deletion

- UNVERIFIED：六个验证字段全为 null；local 通过；integrated 只报 `integration.account_deletion.status`。
- VERIFIED：source 为 object，其中 file 非空、symbol 非空、event_kind=`ACCOUNT_DELETED`（sign_out、logout 等任何其他值报 `integration.account_deletion.source.event_kind`；source 不是 object 报 `integration.account_deletion.source`）；delivery_semantics ∈ AT_LEAST_ONCE / EXACTLY_ONCE；test_command 非空；exit_code 为整数 0；count 为正整数；evidence 为存在的文件。
- 至少一次送达下的重复处理由 NC-026 验证，本工具不模拟。

## 6. 错误路径写法与输出

- 对象键用点号：`client.state`。数组中按 name 或 repository 定位的记录用方括号：`repositories[SPEC].tests.status`、`ports[HTTP].symbol`、`integration.test_runs[SERVER].evidence`。
- 缺键、类型错误、枚举不符、值不等，都报该键的完整路径；父级不是 object 时只报父级路径，不再下钻。
- 退出 0：stdout 恰好一行。local 为 `LOCAL_PREPARATION_PASS`，integrated 为 `INTEGRATED_STRUCTURE_PASS`；scope=TEST_FIXTURE 时行尾追加一个空格和 `(TEST_FIXTURE)`。
- 退出 1：stdout 每行一个路径，去重后按 Python `sorted()` 排序，不输出 PASS。
- 退出 2：`--input` 缺失或不可读、JSON 语法错误、`--profile` 缺失或不是 local/integrated；stderr 输出一行诊断，不输出 traceback，stdout 为空。缺键、类型或枚举错误属于退出 1，不得崩溃成退出 2。

## 7. 当前输入的期望输出

`--profile local` 对当前 `openspec/annotation-community/integration_baseline.json`：退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`。

`--profile integrated` 对同一文件：退出 1，stdout 与下列 23 行逐字相同。

```text
client.runtime_verified
client.state
integration.account_deletion.status
integration.account_pairs
integration.backend.status
integration.devices
integration.emulator.status
integration.mute_aggregation.status
integration.notification_presentation.status
integration.notifier_binding.status
integration.rules.status
integration.test_runs
openapi_validator.status
repositories[NOTIFICATION].tests.status
repositories[NOTIFIER].tests.status
repositories[REST].tests.status
repositories[SERVER].tests.status
repositories[SOCIAL].tests.status
repositories[SPEC].tests.status
repositories[STORAGE].tests.status
resolution_status
scope
sdk.verification
```
````

**整文件 3**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/BDD.md`

````text
# NC-001-01 可观察行为

判据见 [VALIDATION_CONTRACT.md](VALIDATION_CONTRACT.md)；「报 X」指退出 1 且 stdout 含路径 X。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 当前计划新建客户端、父目录存在、建包归 NC-004，十项中未验证项均按契约登记 | 校验 local | 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`，不声称运行就绪 |
| B02 | 同一份当前快照 | 校验 integrated | 退出 1，stdout 与契约 §7 的 23 行逐字相同 |
| B03 | 删除契约 §2～§3 中任一必填键 | 校验 local | 报该键完整路径，无 PASS |
| B04 | PLANNED_NEW 但创建责任不是 NC-004、父目录不存在或 path 已存在 | 校验 local | 分别报 `client.creation_owner`、`client.path`、`client.state`，不创建目录 |
| B05 | EXISTING 但缺 pubspec.yaml、lib 或 .git；或 sdk.evidence 指向的文件不存在 | 校验 local | 报 `client.path` 或 `sdk.evidence`，不修改任何文件 |
| B06 | 某仓库 tests 只把 NOT_RUN 改成 PASSED，没有 command/exit_code/count/evidence | 校验 integrated | 报该仓库 tests 下缺失的每个字段 |
| B07 | new_identity_system=true，或 book_work 不是 DEFERRED_BY_USER | 校验 local | 报 `identity.new_identity_system` 或 `book_work` |
| B08 | JSON 语法错误、输入文件不存在、缺 `--profile` 或 profile 未知 | 执行校验 | 退出 2，stdout 为空，stderr 一行且无 Traceback |
| B09 | 临时目录中 scope=TEST_FIXTURE、全部对象为验证态且证据文件齐全 | 校验 integrated | 退出 0，stdout 恰为 `INTEGRATED_STRUCTURE_PASS (TEST_FIXTURE)` |
| B10 | 任一次校验结束 | 比较运行前后输入与目录 | 内容与目录列表均未改变 |
| B11 | 注销事件 UNVERIFIED 且六个验证字段为 null | 校验 local / integrated | local 通过；integrated 报 `integration.account_deletion.status`；其中一个字段非 null 时 local 报该字段 |
| B12 | 注销事件 VERIFIED 但缺来源、送达语义或执行证据中任一项 | 校验 integrated | 报对应字段路径，不接受只改状态 |
| B13 | 注销事件 event_kind 为 sign_out，或送达语义不在枚举内 | 校验 integrated | 报 `integration.account_deletion.source.event_kind` 或 `integration.account_deletion.delivery_semantics` |
| B14 | ports 缺一个名字、symbol 写成行号、file 不存在 | 校验 local | 分别报 `ports`、`ports[<名>].symbol`、`ports[<名>].file` |
| B15 | 同目录 INTEGRATION_BASELINE.md 含 TBD 或待定，或该文件不存在 | 校验 local | 报 `INTEGRATION_BASELINE.md` |
| B16 | dependencies 或 sdk 版本与契约固定值不同，或 dependencies 多出一个键 | 校验 local | 报 `dependencies.<键>`、`sdk.<键>` 或 `dependencies` |
| B17 | integration 下某对象为未验证态，但验证字段已填值 | 校验 local | 报该验证字段路径，拒绝半填冒充 |
````

**整文件 4**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/TDD.md`

````text
# NC-001-01 验证计划

工作目录固定 `/Users/jingtaiwei/Git/Public/learn_system`。只用 Python 标准库；不读凭据、不连 Emulator、不访问网络。判据全部以 [VALIDATION_CONTRACT.md](VALIDATION_CONTRACT.md) 为准。

## 1. 分两步提交

| 步骤 | ACT | 实现范围 | 覆盖 BDD |
|---|---|---|---|
| 1 | [act/01.yaml](act/01.yaml) | CLI 与退出 2、契约 §1～§3 与 §6、local 档输出；本步 `--profile integrated` 暂时退出 2，stderr 为 `integrated profile not implemented` | B01、B03、B04、B05、B07、B08、B10、B11（local 部分）、B14、B15、B16、B17 |
| 2 | [act/02.yaml](act/02.yaml) | 契约 §4、§5、§7；删除步骤 1 的临时退出 2 | B02、B06、B09、B11（integrated 部分）、B12、B13 |

## 2. 命令

1. `python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_check_integration_baseline.py' -v` → 0。
2. `python3 openspec/annotation-community/tools/check_integration_baseline.py --profile local --input openspec/annotation-community/integration_baseline.json` → 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`。
3. （步骤 2 起）同一命令改为 `--profile integrated` → 退出 1，stdout 与契约 §7 的 23 行逐字相同。
4. `LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh` → 0；`bash openspec/annotation-community/verify.sh` → 0；`git diff --check` → 0。
5. （步骤 2 完成后）`bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh --require-impl` → 0。

## 3. 测试文件与方法

测试文件：`openspec/annotation-community/tools/test_check_integration_baseline.py`。

公共夹具 `make_fixture(tmp)`：在 `tempfile.TemporaryDirectory()` 中写出一份键与当前 `integration_baseline.json` 完全相同的 JSON，把所有外部路径改到临时目录内（sdk.evidence、ports[].file、notification_presentation.file 各建一个空文件；client.path 指向临时父目录下尚不存在的子目录），同目录写一份不含占位的 `INTEGRATION_BASELINE.md`。单测不得依赖真实外部路径；真实输入只由命令 2、3 覆盖。每个证据字段使用各自独立的文件，删除一个文件只影响一个路径。

通过 `subprocess.run([sys.executable, CHECKER, ...], capture_output=True, text=True)` 调用，`CHECKER = Path(__file__).with_name("check_integration_baseline.py")`；断言退出码与 stdout 全文（「含」指按行拆分后包含）。

步骤 1 的 13 个方法：

| 方法 | 断言 |
|---|---|
| test_local_fixture_pass | 夹具 local 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS\n`（B01） |
| test_missing_required_keys | 契约 §2～§3 每个必填键逐个删除（subTest），退出 1 且 stdout 含该键路径（B03） |
| test_planned_new_rules | creation_owner 改为 NC-005、父目录不存在、path 已存在三例，分别含 `client.creation_owner`、`client.path`、`client.state`；运行后临时目录列表不变（B04） |
| test_existing_client_rules | state=EXISTING 时分别缺 pubspec.yaml、lib、.git，均含 `client.path`（B05） |
| test_sdk_evidence_missing | 删除 sdk.evidence 指向的文件，含 `sdk.evidence`（B05） |
| test_pins_rules | drift 改为 2.34.0 含 `dependencies.drift`；多加一个键含 `dependencies`；sdk.flutter 改为 3.44.7 含 `sdk.flutter`（B16） |
| test_identity_and_book_rejected | new_identity_system=true 含 `identity.new_identity_system`；book_work=ACTIVE 含 `book_work`（B07） |
| test_cli_errors_exit2 | JSON 语法错误、`--input` 指向不存在文件、缺 `--profile`、`--profile foo` 四例：退出 2，stdout 为空，stderr 不含 `Traceback`（B08） |
| test_inputs_unchanged | 运行 local 前后，JSON 与 MD 的 sha256 相同，临时目录文件列表相同（B10） |
| test_account_deletion_unverified_local | 当前形态 local 通过；test_command 改为 `"x"` 后含 `integration.account_deletion.test_command`（B11） |
| test_ports_rules | 删除 MENTION 条目含 `ports`；HTTP 的 symbol 写成 `42` 含 `ports[HTTP].symbol`；HTTP 的 file 指向不存在文件含 `ports[HTTP].file`（B14） |
| test_placeholder_rules | MD 追加 `TBD` 含 `INTEGRATION_BASELINE.md`；删除 MD 同样含该路径（B15） |
| test_half_filled_unverified_rejected | rules.status=UNVERIFIED 但 path 为 `"x"`，含 `integration.rules.path`（B17） |

步骤 2 的 8 个方法：

| 方法 | 断言 |
|---|---|
| test_integrated_current_golden | 夹具（scope 与各状态保持当前输入的值）integrated 退出 1，stdout 与契约 §7 的 23 行逐字相同；期望值在测试文件中以字面量写出（B02、B11） |
| test_integrated_fixture_pass | 把夹具补成完整验证态：scope=TEST_FIXTURE；client 为 EXISTING 并建 pubspec.yaml、lib、.git；全部对象为验证态并配证据文件；两台设备（一台 p2p_peer=true）、两组账号；7 条 test_runs 与 7 个 PASSED tests；resolution_status=RESOLVED；sdk.verification=RUNTIME_VERIFIED；runtime_verified=true。退出 0，stdout 恰为 `INTEGRATED_STRUCTURE_PASS (TEST_FIXTURE)\n`（B09） |
| test_integrated_fixture_evidence_removed | 在完整夹具上逐个删除证据文件（subTest：backend、emulator、rules.path、rules.evidence、notifier_binding、notification_presentation、mute_aggregation、openapi_validator、account_deletion、repositories[STORAGE].tests、integration.test_runs[SERVER]），每例退出 1 且 stdout 恰为对应的一行路径 |
| test_fake_test_pass_rejected | 当前夹具中把 repositories[STORAGE].tests.status 改为 PASSED，stdout 含该记录的 `.command`、`.count`、`.evidence`、`.exit_code`；在完整夹具上把 exit_code 改为 true，含 `repositories[STORAGE].tests.exit_code`（B06） |
| test_account_deletion_verified_missing_fields | 完整夹具中逐个把六个验证字段置 null（subTest），含对应路径（B12） |
| test_account_deletion_kind_and_delivery_rejected | event_kind=`sign_out` 含 `integration.account_deletion.source.event_kind`；delivery_semantics=`BEST_EFFORT` 含 `integration.account_deletion.delivery_semantics`（B13） |
| test_devices_and_pairs_rules | 完整夹具中：只剩 1 台设备、两台 device_id 相同、全部 p2p_peer=false 三例均含 `integration.devices`；一组账号加 token 键含 `integration.account_pairs` |
| test_test_runs_set_rules | 完整夹具删除 SPEC 那条 test_runs，stdout 恰为 `integration.test_runs` |

## 4. Red→Green

- 每步先写该步的测试，再建一个只解析参数、恒 `sys.exit(0)` 的空壳（步骤 2 沿用步骤 1 的实现），运行命令 1，记录非 0 退出码与至少一条真实断言失败原文，作为 Red。0 tests、ImportError、语法错误、文件不存在导致的退出 2 都不算 Red。
- 然后实现，运行命令 1～4（步骤 2 加命令 5），作为 Green。空壳不单独提交。
- 禁止：skip、永真断言、从 checker 输出或本文件生成期望值、捕获异常后放行、为了通过测试修改 JSON、MD 或契约。
````

**整文件 5**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/ACT.yaml`

````text
TASK_ID: NC-001-01
STATUS: PREPARING
GOAL: 实现集成基线校验器；local 档校验规划基线，integrated 档对未验证快照输出逐项缺证清单
CONTRACT: docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md
SPLIT:
  - act/01.yaml
  - act/02.yaml
ORDER: "严格按 act/01.yaml → act/02.yaml 执行，每步独立提交；act/02 以 act/01 的提交为基线"
ESTIMATE_MINUTES_TOTAL: 105
````

**整文件 6**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/act/01.yaml`

````text
TASK_ID: NC-001-01-A
PARENT: NC-001-01
STATUS: PREPARING
GOAL: 实现校验器 CLI、契约 §1～§3 与 §6 的共同规则和 local 档输出
DEPENDS_ON: []
ESTIMATE_MINUTES: 55
SCOPE:
  READ:
    - docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md
    - docs/blackbox-spec-rework/work-items/nc-001/BDD.md
    - docs/blackbox-spec-rework/work-items/nc-001/TDD.md
    - openspec/annotation-community/integration_baseline.json
    - openspec/annotation-community/INTEGRATION_BASELINE.md
  PATH_EXISTENCE_ONLY:
    - integration_baseline.json 中出现的全部外部路径，只判断是否存在，不读内容
  WRITE_NEW:
    - openspec/annotation-community/tools/check_integration_baseline.py
    - openspec/annotation-community/tools/test_check_integration_baseline.py
  FORBIDDEN:
    - /Users/jingtaiwei/Git/Public/xuan-migration 与 /Users/jingtaiwei/Git/Public/xuan-server 下的任何写入
    - openspec/annotation-community/integration_baseline.json
    - openspec/annotation-community/INTEGRATION_BASELINE.md
    - docs/blackbox-spec-rework/work-items/nc-001/ 下全部文件
    - openspec/annotation-community/ 下既有守卫与四份规格
    - PLAN.md、HANDOFF.md、docs/blackbox-spec-rework/SUBAGENT_TODO.md
DEPENDENCY_ALLOWLIST: [Python 标准库]
SIGNATURE:
  cli: "check_integration_baseline.py --profile local|integrated --input PATH"
  exit_0: "local 档 stdout 恰为 LOCAL_PREPARATION_PASS；scope=TEST_FIXTURE 时追加 ' (TEST_FIXTURE)'"
  exit_1: "stdout 每行一个契约 §6 写法的路径，去重后 sorted()"
  exit_2: "CLI 或输入错误，stderr 一行；本步 --profile integrated 也退出 2，stderr 为 integrated profile not implemented"
RULES:
  - "判据只取 VALIDATION_CONTRACT.md §1～§3 与 §6，不从输入 JSON 反推必填项"
  - "对外部路径只调用 exists、is_file、is_dir，不读内容、不执行 git 或其他子进程"
  - "收集全部错误后统一输出，不在第一个错误处返回"
TESTS_FIRST:
  - "写入 TDD §3 步骤 1 的 13 个方法；建只解析参数、恒退出 0 的空壳；运行 TDD 命令 1，保存非 0 退出码与断言失败原文"
STEPS:
  - "实现参数解析与退出 2 分支"
  - "实现契约 §2 顶层与 §3 对象规则，按 §6 生成路径"
  - "实现 INTEGRATION_BASELINE.md 占位扫描"
  - "运行 VERIFICATION 全部命令并满足 TDD 期望"
  - "只暂存两个文件并提交，消息为 feat(nc-001): 集成基线校验器 local 档"
VERIFICATION:
  - "python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_check_integration_baseline.py' -v"
  - "python3 openspec/annotation-community/tools/check_integration_baseline.py --profile local --input openspec/annotation-community/integration_baseline.json"
  - "LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh"
  - "bash openspec/annotation-community/verify.sh"
  - "git diff --check"
ON_FAIL: "停止并报告失败命令、退出码与断言原文；不改输入、契约或测试期望，不安装依赖，不扩大范围"
````

**整文件 7**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/act/02.yaml`

````text
TASK_ID: NC-001-01-B
PARENT: NC-001-01
STATUS: PREPARING
GOAL: 实现契约 §4、§5、§7；integrated 档对完整证据给出结构通过，对当前快照输出 23 行缺证清单
DEPENDS_ON: [NC-001-01-A]
ESTIMATE_MINUTES: 50
SCOPE:
  READ:
    - docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md
    - docs/blackbox-spec-rework/work-items/nc-001/BDD.md
    - docs/blackbox-spec-rework/work-items/nc-001/TDD.md
    - openspec/annotation-community/integration_baseline.json
    - openspec/annotation-community/INTEGRATION_BASELINE.md
  PATH_EXISTENCE_ONLY:
    - integration_baseline.json 中出现的全部外部路径，只判断是否存在，不读内容
  WRITE:
    - openspec/annotation-community/tools/check_integration_baseline.py
    - openspec/annotation-community/tools/test_check_integration_baseline.py
  FORBIDDEN:
    - /Users/jingtaiwei/Git/Public/xuan-migration 与 /Users/jingtaiwei/Git/Public/xuan-server 下的任何写入
    - openspec/annotation-community/integration_baseline.json
    - openspec/annotation-community/INTEGRATION_BASELINE.md
    - docs/blackbox-spec-rework/work-items/nc-001/ 下全部文件
    - openspec/annotation-community/ 下既有守卫与四份规格
    - PLAN.md、HANDOFF.md、docs/blackbox-spec-rework/SUBAGENT_TODO.md
DEPENDENCY_ALLOWLIST: [Python 标准库]
SIGNATURE:
  cli: "check_integration_baseline.py --profile local|integrated --input PATH"
  exit_0: "integrated 档 stdout 恰为 INTEGRATED_STRUCTURE_PASS；scope=TEST_FIXTURE 时追加 ' (TEST_FIXTURE)'"
  exit_1: "stdout 每行一个契约 §6 写法的路径，去重后 sorted()"
  exit_2: "CLI 或输入错误，stderr 一行；删除步骤 1 中 integrated 的临时退出 2"
RULES:
  - "判据只取 VALIDATION_CONTRACT.md §4～§7"
  - "状态闸门：对象 status 不是验证态时只报 <对象>.status"
  - "不得修改步骤 1 已有测试的期望；只追加步骤 2 的方法与完整夹具构造函数"
  - "23 行期望在测试文件中以字面量写出，不读取 VALIDATION_CONTRACT.md 生成"
TESTS_FIRST:
  - "写入 TDD §3 步骤 2 的 8 个方法；运行 TDD 命令 1（此时 integrated 仍退出 2），保存非 0 退出码与断言失败原文"
STEPS:
  - "实现契约 §4 各行与状态闸门"
  - "实现契约 §5 account_deletion 验证态规则"
  - "实现 TEST_FIXTURE 输出后缀"
  - "运行 VERIFICATION 全部命令并满足 TDD 期望"
  - "只暂存两个文件并提交，消息为 feat(nc-001): 集成基线校验器 integrated 档"
VERIFICATION:
  - "python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_check_integration_baseline.py' -v"
  - "python3 openspec/annotation-community/tools/check_integration_baseline.py --profile local --input openspec/annotation-community/integration_baseline.json"
  - "python3 openspec/annotation-community/tools/check_integration_baseline.py --profile integrated --input openspec/annotation-community/integration_baseline.json（期望退出 1，stdout 与契约 §7 逐字相同）"
  - "LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh"
  - "bash openspec/annotation-community/verify.sh"
  - "git diff --check"
  - "bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh --require-impl"
ON_FAIL: "停止并报告失败命令、退出码与断言原文；不改输入、契约或测试期望，不安装依赖，不扩大范围"
````

**整文件 8**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/PROMPT.md`

````text
# NC-001-01 执行提示

发送前提：wjt-react 四查判定 READY，且主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把下面分隔线以下的全文原样发给执行 Agent。

---

你在 `/Users/jingtaiwei/Git/Public/learn_system` 的当前工作树执行 NC-001-01：实现集成基线校验器。其他 Agent 在同一工作树并行工作，不要回退、暂存或提交任何不属于你的改动。

**先读（按顺序）**：`AGENTS.md`；工作包目录 `docs/blackbox-spec-rework/work-items/nc-001/` 下的 README.md、VALIDATION_CONTRACT.md、BDD.md、TDD.md、ACT.yaml、act/01.yaml、act/02.yaml、ACCEPTANCE.md。

**只允许写**：`openspec/annotation-community/tools/check_integration_baseline.py` 与 `openspec/annotation-community/tools/test_check_integration_baseline.py`。

**禁止**：修改工作包、契约、`integration_baseline.json`、`INTEGRATION_BASELINE.md`、四份规格与既有守卫、PLAN.md、HANDOFF.md、SUBAGENT_TODO.md；写入任何外部仓库；读取凭据、连接 Emulator 或访问网络；安装依赖；创建 `reading-notes` 目录；读取外部文件内容（只允许判断路径是否存在）。

**步骤**：严格按 act/01.yaml → act/02.yaml。每步先写测试，按 TDD §4 取得真实断言失败（Red），再实现（Green），再运行该 ACT 的 VERIFICATION 全部命令。

**提交**：每步一个提交，只 `git add` 上面两个文件。提交消息分别为 `feat(nc-001): 集成基线校验器 local 档` 与 `feat(nc-001): 集成基线校验器 integrated 档`。

**停止条件**：命令结果与 TDD 期望不符，且不是你的实现错误；契约有两种以上解释；需要写允许范围之外的文件。停止时报告失败命令、退出码与原文，不自行修改契约或期望。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败断言原文；
3. Green：VERIFICATION 每条命令的退出码与输出末 20 行；
4. 步骤 2 另附：integrated 命令的完整 stdout，以及 `bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh --require-impl` 的退出码；
5. 跳过项、未运行项与剩余风险。

integrated 对当前快照退出 1 是必须保留的负例，不要把它报告成失败；也不要把本任务说成 NC-001 总项完成。
````

### 3.2 逐字替换（18 处）

**替换 1**｜文件：`openspec/annotation-community/TASKS.md`

原文：
```text
- [ ] 新增 `SPEC/tools/check_integration_baseline.py`。红条件：`INTEGRATION_BASELINE.md` 含 `TBD`/`待定`/`?` 占位、或 CLIENT 根路径在文件系统中不存在、或任一端口缺 `文件:符号` 形式、或上述十项必填项任一缺失。
```

替换为：
```text
- [ ] 新增 `SPEC/tools/check_integration_baseline.py`，机器输入为 `SPEC/integration_baseline.json`，并扫描同目录 `INTEGRATION_BASELINE.md`；字段契约见 `PACK/nc-001/VALIDATION_CONTRACT.md`。分两级：**NC-001-01** 用 `--profile local` 校验规划基线，允许 CLIENT 为 `PLANNED_NEW`（创建归 NC-004、父目录存在、目录尚不存在），未验证项必须按契约如实登记；**NC-001-02** 用 `--profile integrated` 作为本任务总项准出，要求 CLIENT 为 `EXISTING` 且十项全部为验证态。两级共同红条件：`INTEGRATION_BASELINE.md` 含 `TBD`/`待定` 占位、任一端口缺存在的文件或合法符号、上述十项必填项任一缺失。
```

**替换 2**｜文件：`openspec/annotation-community/TASKS.md`

原文：
```text
- [ ] 验收：每个端口列真实文件/符号和「已有实现/新增适配」，不把 mock 或内存降级当生产；目录/版本未唯一确定则本任务不通过。运行 `python3 SPEC/tools/check_integration_baseline.py`，退出 0。
```

替换为：
```text
- [ ] 验收：每个端口列真实文件/符号和「已有实现/新增适配」，不把 mock 或内存降级当生产；目录/版本未唯一确定则本任务不通过。NC-001-01 运行 `python3 SPEC/tools/check_integration_baseline.py --profile local --input SPEC/integration_baseline.json`，退出 0，只关闭 NC-001-01；**NC-001 总项**运行同一命令的 `--profile integrated`，退出 0 且 stdout 恰为 `INTEGRATED_STRUCTURE_PASS`（不带 `(TEST_FIXTURE)`）才可标 ACCEPTED。
```

**替换 3**｜文件：`openspec/annotation-community/PRD.md`

原文：
```text
| 2026-09-10 | v1.5：新增 R-21 行为事件数据源（DESIGN §11、NC-026），并同步 verify.sh 与总守卫的 R 编号和版本判定 | R-21 | [FIX_V1_5](FIX_V1_5.md) |
```

替换为：
```text
| 2026-09-10 | NC-001 拆为两级：NC-001-01 以 `--profile local` 校验规划基线（允许 CLIENT 计划新建），NC-001-02 以 `--profile integrated` 作为总项准出；机器输入为 integration_baseline.json，补端口表与十项字段；CLIENT 定为独立 Git 仓库 | R-18 | [NC-001-REVIEW-R1](../../docs/blackbox-spec-rework/reviews/NC-001-REVIEW-R1.md) |
| 2026-09-10 | v1.5：新增 R-21 行为事件数据源（DESIGN §11、NC-026），并同步 verify.sh 与总守卫的 R 编号和版本判定 | R-21 | [FIX_V1_5](FIX_V1_5.md) |
```

**替换 4**｜文件：`openspec/annotation-community/INTEGRATION_BASELINE.md`

原文：
```text
xuan-migration 父目录目前不是 Git 仓库，后续工程包须明确新仓库/子模块装配归属，不得在父目录假设可直接提交。
```

替换为：
```text
xuan-migration 父目录不是 Git 仓库；CLIENT 定为独立 Git 仓库（与该目录下其他子模块一致，JSON 记为 client.vcs=NEW_GIT_REPOSITORY），由 NC-004 在 `reading-notes` 内执行 `git init` 建立，不在父目录提交；远端地址由用户后续指定，不阻塞本地开发。
```

**替换 5**｜文件：`openspec/annotation-community/INTEGRATION_BASELINE.md`

原文：
```text
database_provider.dart:26，AnnotationDatabaseProvider
```

替换为：
```text
database_provider.dart:33，AnnotationDatabaseProvider
```

**替换 6**｜文件：`openspec/annotation-community/INTEGRATION_BASELINE.md`

原文：
```text
mention_input_enhancer.dart:16，MentionInputEnhancer/onInsert
```

替换为：
```text
mention_input_enhancer.dart:24，MentionInputEnhancer/onInsert
```

**替换 7**｜文件：`openspec/annotation-community/INTEGRATION_BASELINE.md`

原文：
```text
conftest.py:8，_emulator_env
```

替换为：
```text
conftest.py:11，_emulator_env
```

**替换 8**｜文件：`openspec/annotation-community/INTEGRATION_BASELINE.md`

原文：
```text
Terra 建议中的 notebook 依赖和新增随机身份未采纳。
```

替换为：
```text
端口的机器登记见 JSON `ports`（8 项，按文件与符号记录、不用行号，由校验器检查）；上表行号仅供阅读，以 JSON 为准。Terra 建议中的 notebook 依赖和新增随机身份未采纳。
```

**替换 9**｜文件：`openspec/annotation-community/INTEGRATION_BASELINE.md`

原文：
```text
| 宿主账号注销 | 来源、送达语义和测试均未验证 | NC-001 登记证据，NC-026 消费；缺证只阻断 NC-026 注销子项，不能以退出登录代替删号事件 |
```

替换为：
```text
| 宿主账号注销 | 来源、送达语义和测试均未验证。已查到的只有客户端删号：xuan-account `lib/auth/auth_coordinator.dart` 的 `AuthCoordinator.deleteAccount` 调 `deleteCurrentAccount()` 删除 Firebase 当前用户并清本地会话，xuan-shell `ShellAccountController.deleteAccount` 转调；functions-py 的 `main.py` 与 `xuan/` 中没有删号处理函数或触发器，服务端当前收不到删号事件 | NC-001 登记证据，NC-026 消费；缺证只阻断 NC-026 注销子项，不能以退出登录代替删号事件 |
```

**替换 10**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/README.md`

原文：
```text
输入JSON与调查证据矛盾、输入基线的HEAD字段发生变化、执行需越过读写范围、需要访问真实云或身份凭据、标准库不可用均停止并报告。
```

替换为：
```text
输入JSON与调查证据矛盾、契约存在两种以上解释、执行需越过读写范围、需要访问真实云或身份凭据、标准库不可用均停止并报告。执行者不核对仓库 HEAD 是否仍为采样值，HEAD 新鲜度由 NC-001-02 重新取证。
```

**替换 11**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/README.md`

原文：
```text
当前没有 checker，因此初始命令应退出2并显示文件不存在，不算行为Red。真正Red由下述测试针对未实现checker的返回与诊断建立。
```

替换为：
```text
当前没有 checker；Red 按 TDD §4 用空壳取得真实断言失败，文件不存在导致的退出 2 不算 Red。
```

**替换 12**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/README.md`

原文：
```text
精确两文件、每项成对测试、Red/Green原始输出和单独commit。
```

替换为：
```text
精确两文件，按 act/01.yaml → act/02.yaml 分两个提交，每步交付 Red/Green 原始输出。
```

**替换 13**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/README.md`

原文：
```text
3. [ACT](ACT.yaml)：只写两个工具文件；
```

替换为：
```text
3. [ACT](ACT.yaml) 及 [act/01](act/01.yaml)、[act/02](act/02.yaml)：分两步只写两个工具文件；
```

**替换 14**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/ACCEPTANCE.md`

原文：
```text
2. 核对commit只有两个新文件，输入与旧门禁无diff；外部仓库无本任务改动。
```

替换为：
```text
2. 核对 act/01、act/02 两个提交合计只涉及两个工具文件，输入与旧门禁无diff；外部仓库无本任务改动。
```

**替换 15**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/ACCEPTANCE.md`

原文：
```text
3. 重跑TDD全部命令。命令1需发现并运行全部命名用例；命令2退出0；命令3退出1是必须保留的负例。捕获退出码，不以一串命令末条成功掩盖前面失败。
```

替换为：
```text
3. 重跑TDD全部命令。命令1需发现并运行 TDD §3 列出的全部 21 个方法；命令2退出0且 stdout 恰为 `LOCAL_PREPARATION_PASS`；命令3退出1且 stdout 与 VALIDATION_CONTRACT §7 的 23 行逐字相同，这是必须保留的负例；`bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh --require-impl` 退出 0。逐条捕获退出码，不以一串命令末条成功掩盖前面失败。
```

**替换 16**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/ACCEPTANCE.md`

原文：
```text
核对 VALIDATION_CONTRACT.md 与 JSON、BDD B11～13、TDD 五个新增命名测试及 ACT READ 范围闭合。
```

替换为：
```text
核对 VALIDATION_CONTRACT.md 与 JSON、BDD B01～B17、TDD §3 的 21 个方法及 act/01、act/02 的读写范围闭合。
```

**替换 17**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/REMAINING_DELIVERABLES.md`

原文：
```text
| 仓库与范围 | 新鲜 HEAD、现有测试输出/数量、每仓允许写入路径 | NC-001；本轮快照不是运行证据；NC-004 创建 CLIENT 时须明确仓库归属 |
```

替换为：
```text
| 仓库与范围 | 新鲜 HEAD、现有测试输出/数量、每仓允许写入路径 | NC-001；本轮快照不是运行证据；CLIENT 已定为 NC-004 在 client.path 内 git init 的独立仓库（client.vcs=NEW_GIT_REPOSITORY） |
```

**替换 18**｜文件：`docs/blackbox-spec-rework/work-items/nc-001/REMAINING_DELIVERABLES.md`

原文：
```text
| 注销事件 | 源文件/符号、删号事件语义、送达保证、真实触发测试 | NC-001 登记、NC-026 消费；缺证仅阻断 NC-026 注销子项 |
```

替换为：
```text
| 注销事件 | 源文件/符号、删号事件语义、送达保证、真实触发测试 | NC-001 登记、NC-026 消费；缺证仅阻断 NC-026 注销子项。已知现状：只有客户端删号（xuan-account `AuthCoordinator.deleteAccount` → `deleteCurrentAccount()`），functions-py 没有删号处理函数或触发器，服务端当前收不到删号事件；取证时如实登记为缺口，不以退出登录或客户端回调冒充 |
```

## 4. 注销事件现状（事实记录，供 NC-001-02 与 NC-026 使用）

- **客户端**：`xuan-migration/xuan-account/lib/auth/auth_coordinator.dart` 的 `AuthCoordinator.deleteAccount` 先调 `authGateway.deleteCurrentAccount()`，再清除本地会话。该方法的实现在 `xuan-migration/xuan-storage/firebase/lib/account/firebase_account_auth_gateway.dart`，取 `_auth.currentUser` 执行删除。`xuan-migration/xuan-shell/lib/account/shell_account_controller.dart` 的 `ShellAccountController.deleteAccount` 只是转调。
- **服务端**：`xuan-server/functions-py/main.py` 的导出与 `xuan/` 目录中都没有删号处理函数或认证触发器；本机也没有 Node 版 `xuan-server/functions/` 目录。
- **推论**：删号目前只在客户端发生，服务端收不到任何删号事件，⑩ 暂时取不到合格来源。到 NC-026 时注销子项会是 BLOCKED；要解除，需要新增一条由服务端执行的删号路径：先按 DESIGN §11.3 去标识化，再删除 Firebase 账号。这是 NC-026 之前的设计工作，不影响 NC-001-01、NC-002 与本地笔记。
- **未核实**：本机未安装 firebase-functions Python 包（`requirements.txt` 为 `firebase-functions~=0.4.2`），它能否订阅删号事件，由 NC-001-02 查官方文档后登记。

## 5. 完成标准与提交

依次运行，全部为 0 才算完成：

```bash
bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh
```

```bash
git diff --check
```

守卫包含：v1.5 守卫与 verify.sh 回归（K01）、8 个整文件逐字一致（K02）、18 处替换已落实（K03）、基线事实可复核（K04：客户端路径、SDK 与锁文件版本、每个端口的符号确实在文件中）、HEAD 新鲜度提示（K05，只提示不计失败）、契约 §7 的 23 行已排序（K06）、BDD 与 TDD 编号及 ACT 粒度（K07）、校验器实现核对（K08：未实现时 SKIP；加 `--require-impl` 后必须通过，供验收 NC-001-01 使用）。

只暂存下列 14 个文件，用一个提交，消息为 `docs(nc-001): apply NC-001-REVIEW-R1 package rework`。不要暂存 SUBAGENT_TODO.md、HANDOFF.md、PLAN.md，其中有其他 Agent 未提交的改动；台账状态由主线程另行更新。

- `openspec/annotation-community/integration_baseline.json`
- `openspec/annotation-community/INTEGRATION_BASELINE.md`
- `openspec/annotation-community/TASKS.md`
- `openspec/annotation-community/PRD.md`
- `docs/blackbox-spec-rework/work-items/nc-001/` 下的 VALIDATION_CONTRACT.md、BDD.md、TDD.md、ACT.yaml、act/01.yaml、act/02.yaml、PROMPT.md、README.md、ACCEPTANCE.md、REMAINING_DELIVERABLES.md

完成后由未参与编写的审查者做 wjt-react 四查；判定 READY 后，才在 SUBAGENT_TODO 登记 NC-001-01 为 READY 并派发 PROMPT。

## 6. 需要用户知道的两件事

1. **CLIENT 用独立 Git 仓库。** `reading-notes` 所在的 xuan-migration 不是 Git 仓库，其他子模块都是各自独立的仓库，本文按同一做法定下来；远端地址以后再定，不影响本地开发。若希望改成别的方式，需要在执行本文前说明。
2. **注销事件目前服务端收不到。** 这不影响现在的工作，但 NC-026 做注销去标识化之前，需要补一条服务端删号路径（§4）。

## 7. 本次核对证据

- v1.5 重放：`git archive 8aa4792` 展开到临时目录后应用 40 处替换，失败 0；9 个目标文件与 `git show cc13a3e:<路径>` 逐字节比对全部一致。
- 在 HEAD 上运行 `LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`、`verify.sh`、`git diff --check HEAD~2 HEAD`，均为 0。
- 外部事实：6 个外部仓库 HEAD 与 JSON 采样值一致；`flutter.version.json` 为 3.44.6 / 3.12.2；`xuan-storage/drift/pubspec.lock` 中 7 个依赖版本与 JSON 一致；pub-cache 有 flutter_markdown_plus-1.0.12；`reading-notes` 不存在、父目录存在；10 处源码行号逐条打开核对，3 处指错（F10）。
- 本文的全部修复已先在临时副本（`git archive HEAD` 展开）上应用：8 个整文件与 18 处替换全部落位，`nc001_r1_guard.sh` 退出 0；在未应用修复的真实仓库上运行同一守卫为非 0。
