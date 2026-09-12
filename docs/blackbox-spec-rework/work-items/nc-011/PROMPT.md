# NC-011 执行提示（三线并行）

发送前提：wjt-react 四查 READY；SUBAGENT_TODO 登记。三节可分别发给三个执行者同时开工；每节分隔线以下全文即提示词。

## REST 线（act/01）

---

你执行 NC-011 的 REST 线 act/01：仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外）。每条 dart 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-011/` 下 README.md、BDD.md（A01～A04）、TDD.md §1～§2、act/01.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_discussion.md` §2.3、§10、§13、§14 与 `community_api.md` §10、§11（逐字照做）。

**先写测试再改实现**：先追加 4 个测试、3 个示例、manifest 3 项，取得 Red 原文（期望 4 个新测试失败），再改 openapi.yaml。

**只允许写**：act/01.yaml WRITE_NEW 清单。禁止：清单外任何文件；改动或删除既有测试与示例；新依赖；`skip`；永真断言；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；既有测试变红；validate_openapi 报 ENV_BLOCKED；需要改清单外文件。停止时在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-011/DELIVERY_REPORT_REST.md` 追加「## 待裁决」（现象、命令、原文、你看到的选项），对话最后单独输出一行 `NC-011-A 停手待裁决`。

**提交**：一个提交，只 `git add` 清单文件，消息 `feat(openapi): 评论楼内分页、回复预览与计数、评论创建冲突组件（NC-011-A）`，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_REST.md`（不 git add）：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；act/01.yaml VERIFICATION 每条命令的退出码与末 20 行。完成后对话最后单独输出一行 `NC-011-A 完成`。

## SERVER 线（act/02 → act/03 → act/04）

---

你执行 NC-011 的 SERVER 线：act/02 → act/03 → act/04 严格串行。仓库 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（git 根即此目录）；act/04 另改 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server`（git 根，测试在 `server/functions/`）。上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外。每条 Python 命令带 `PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，pytest 加 `-p no:cacheprovider`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-011/` 下 README.md、BDD.md（T01～T35）、TDD.md §1、§3～§5、act/02～04.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_discussion.md` 全文（逐字照做），`community_api.md` §4.1、§7、§11，`community_server.md` §3、§10。

**基线**：`df5c3da`，全量 `5 failed, 459 passed, 9 xfailed`，五个既有失败的 ID 见契约 §1，全程必须保持恰为这五个。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文，再实现。act/04 的测试若直接通过，按 TDD §5 给出非永真证明。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：契约 §2.1 禁止清单；改前一步测试期望；新依赖；`skip`/`xfail`；永真断言；测试内计算参考值；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；参考哈希、Thread ID、ETag 或游标字面量对不上；FAILED 集合变化或既有测试变红；并发屏障任一 `wait(10)` 超时或提交顺序与契约 §8 不符；act/04 暴露实现缺陷；需要改清单外文件。停止时在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-011/DELIVERY_REPORT_SERVER.md` 追加「## 待裁决」（现象、命令、原文、Emulator 相关输出、你看到的选项），对话最后单独输出一行 `NC-011-<B|C|D> 停手待裁决`，不再继续。

**提交**：act/02、act/03 各一个提交；act/04 在 functions-py 与 xuan-server 各一个提交。只 `git add` 本步文件，消息按各 ACT 的 COMMIT_MESSAGE，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_SERVER.md`（不 git add），每步一节：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；VERIFICATION 每条命令的退出码与末 20 行（全量 pytest 另附 `-rf` 的 FAILED 行原文）；act/04 另附 `nc011_guard.sh --require-impl server` 退出码。每步完成输出一行 `NC-011-<B|C|D> 完成`，三步全部完成后输出 `NC-011 SERVER 线完成`。

## CLIENT 线（act/05 → act/06）

---

你执行 NC-011 的 CLIENT 线：act/05 → act/06 严格串行。仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外）。每条 flutter 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-011/` 下 README.md、BDD.md（K01～K25）、TDD.md §1、§6～§7、act/05～06.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_discussion.md` §1、§2.2、§10～§12、§14（逐字照做）与 `community_client.md` §3、§4、§6、§10。

**基线**：`4588f78`，`flutter test` `+214`，`flutter analyze` 0。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文，再实现。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：契约 §2.2 禁止清单；改前一步测试期望；`pubspec.yaml`/`pubspec.lock`；新依赖；真实网络（一律 `MockClient`）；`skip`；永真断言；测试内计算 payload_hash 期望值；`git push`；删除文件。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；H1～H3 对不上；既有测试变红；act/06 需要改 act/05 文件或禁止清单文件；K11 滚动偏移无法稳定测量；需要新增文案。停止时在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-011/DELIVERY_REPORT_CLIENT.md` 追加「## 待裁决」（现象、命令、原文、你看到的选项），对话最后单独输出一行 `NC-011-<E|F> 停手待裁决`，不再继续。

**提交**：两步各一个提交，只 `git add` 本步文件，消息按各 ACT 的 COMMIT_MESSAGE，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_CLIENT.md`（不 git add），每步一节：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；VERIFICATION 每条命令的退出码与末 20 行；act/06 另附 `nc011_guard.sh --require-impl client` 退出码。每步完成输出一行 `NC-011-<E|F> 完成`，两步全部完成后输出 `NC-011 CLIENT 线完成`。
