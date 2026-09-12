# NC-012a 执行提示（三线并行）

发送前提：wjt-react 四查 READY；SUBAGENT_TODO 登记。三节可分别发给三个执行者同时开工；每节分隔线以下全文即提示词。

## REST 线（act/01）

---

你执行 NC-012a 的 REST 线 act/01：仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外）。每条 dart 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`，并显式设置不少于 600 秒超时。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-012a/` 下 README.md、BDD.md（A01～A04）、TDD.md §1～§2、act/01.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_interactions.md` §2.3、§9、§12、§15 与 `community_api.md` §10、§12（逐字照做）。

**开工前**：`git log --oneline -1` 为 `4671c92` 开头、`git status --short` 为空，否则停手。

**先写测试再改实现**：先追加 4 个测试、4 个示例、manifest 4 项，取得 Red 原文（期望 4 个新测试失败），再改 openapi.yaml。

**只允许写**：act/01.yaml WRITE_NEW 清单。禁止：清单外任何文件；改动或删除既有测试与示例；新依赖；`skip`；永真断言；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；既有测试变红；validate_openapi 报 ENV_BLOCKED；check_examples 拒收契约示例；需要改清单外文件。停止时在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-012a/DELIVERY_REPORT_REST.md` 追加「## 待裁决」（现象、命令、原文、你看到的选项），对话最后单独输出一行 `NC-012a-A 停手待裁决`。

**提交**：一个提交，只 `git add` 清单文件，消息 `feat(openapi): 互动响应包装、我的分享链接与收藏读取端点（NC-012a-A）`，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_REST.md`（不 git add）：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；act/01.yaml VERIFICATION 每条命令的退出码与末 20 行。完成后对话最后单独输出一行 `NC-012a-A 完成`。

## SERVER 线（act/02 → act/03）

---

你执行 NC-012a 的 SERVER 线：act/02 → act/03 严格串行。仓库 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（git 根即此目录）；act/02 另改 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server`（git 根，测试在 `server/functions/`）。上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外。每条 Python 命令带 `PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，pytest 加 `-p no:cacheprovider`；pytest 与 npm 命令显式设置不少于 600 秒超时。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-012a/` 下 README.md、BDD.md（I01～I27）、TDD.md §1、§3～§4、act/02～03.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_interactions.md` 全文（逐字照做），`community_api.md` §4.1、§7、§12，`community_discussion.md` §7、§8.1。

**基线**：`0fad16e`，全量 `5 failed, 496 passed, 9 xfailed`，五个既有失败 ID 为 `tests/test_config.py::test_集合名与_ts_逐项一致`、`tests/test_registration.py::test_全部_callable_已在入口注册`、`test_三个_trigger_已注册`、`test_与_入口总数对齐`、`test_没有多余的未声明导出`，全程必须保持恰为这五个。开工前 `git status --short` 为空，否则停手。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文，再实现。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：契约 §2.1 禁止清单；改前一步测试期望；新依赖；`skip`；新增 `xfail`；永真断言；测试内计算参考值；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；参考哈希、文档 ID、ETag 或游标字面量对不上；FAILED 集合变化或既有测试变红；I10 重试 5 次仍 503；存储文档不过 NC-002 Schema；需要改清单外文件。停止时在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-012a/DELIVERY_REPORT_SERVER.md` 追加「## 待裁决」（现象、命令、原文、Emulator 相关输出、你看到的选项），对话最后单独输出一行 `NC-012a-<B|C> 停手待裁决`，不再继续。

**提交**：act/02 在 functions-py 与 xuan-server 各一个提交；act/03 一个提交。只 `git add` 本步文件，消息按各 ACT 的 COMMIT_MESSAGE，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_SERVER.md`（不 git add），每步一节：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；VERIFICATION 每条命令的退出码与末 20 行（全量 pytest 另附 `-rf` 的 FAILED 行原文）；act/03 另附 `nc012a_guard.sh --require-impl server` 退出码。每步完成输出一行 `NC-012a-<B|C> 完成`，两步全部完成后输出 `NC-012a SERVER 线完成`。

## CLIENT 线（act/04 → act/05 → act/06）

---

你执行 NC-012a 的 CLIENT 线：act/04 → act/05 → act/06 严格串行。仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外）。每条 flutter 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`，并显式设置不少于 600 秒超时。git 用 `/usr/bin/git`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-012a/` 下 README.md、BDD.md（J01～J26）、TDD.md §1、§5～§7、act/04～06.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_interactions.md` §1、§2.2、§9～§11、§15（逐字照做）与 `community_client.md` §3、§4、§10。

**基线**：`d80703b`，`flutter test` `+270`，`flutter analyze` 0；开工前 `git status --short` 为空，否则停手。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文，再实现。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：契约 §2.2 禁止清单；改前一步测试期望；`pubspec.yaml`/`pubspec.lock`；新依赖；真实网络（一律 `MockClient`）；`skip`；永真断言；测试内计算 payload_hash 期望值；新增 §10.11 闭集外文案；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；§9 哈希或 M1～M8 对不上；删除社区 `MentionRef` 后既有测试变红；J12 无法用 `Completer` 稳定复现挂起；act/05 或 act/06 需要改前一步文件或禁止清单文件；需要新增文案。停止时在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-012a/DELIVERY_REPORT_CLIENT.md` 追加「## 待裁决」（现象、命令、原文、你看到的选项），对话最后单独输出一行 `NC-012a-<D|E|F> 停手待裁决`，不再继续。

**提交**：三步各一个提交，只 `git add` 本步文件，消息按各 ACT 的 COMMIT_MESSAGE，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_CLIENT.md`（不 git add），每步一节：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；VERIFICATION 每条命令的退出码与末 20 行；act/06 另附 `nc012a_guard.sh --require-impl client` 退出码。每步完成输出一行 `NC-012a-<D|E|F> 完成`，三步全部完成后输出 `NC-012a CLIENT 线完成`。
