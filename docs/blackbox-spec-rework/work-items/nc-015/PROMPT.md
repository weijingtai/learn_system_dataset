# NC-015 执行提示

发送前提：wjt-react 四查与攻击场景审查判定 READY；主线程已在 SUBAGENT_TODO 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-015：在规格仓库 `/Users/jingtaiwei/Git/Public/learn_system`（分支 `codex/docs/knowledge-compilation`）内，按契约 `openspec/annotation-community/contracts/private_sync.md` 交付 18 个正反样例与检查器。这是规格侧产物，不写任何 Dart/Flutter 代码；xuan-storage、reading-notes、xuan-server 只读。Python 用 `/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python`，测试用 `unittest`（本机无 pytest）。

**先读**：`AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-015/` 下 README.md、BDD.md、TDD.md、ACT.yaml、act/01～02.yaml、ACCEPTANCE.md；契约 `private_sync.md` 全文（§7 样例表与 §8 红条件逐字照做）；`fixtures/community/content_hash_cases.json` 只读第一个 case 的 `expected_hash`。

**先写测试再改实现**：act/02 先写 16 个 unittest 取得 ImportError 原文，再写检查器。

**只允许写**：`openspec/annotation-community/fixtures/private_sync/*.json`（18 个，文件名逐字按契约 §7）、`openspec/annotation-community/tools/check_private_sync_protocol.py`、`openspec/annotation-community/tools/test_check_private_sync_protocol.py`。禁止：改契约或任何其他文件；新增依赖；真实密码学库（签名/密文为格式级，D-NC015-07）；`skip`、永真断言。

**判据**：只来自契约与 TDD/BDD。契约有两种以上解释、`content_hash_cases.json` 第一个 case 无 `expected_hash`、检查器需读契约以外文档：立即停止并原样报告。

**提交**：两步各一个提交，只 `git add` 本步文件，不 push；提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。仓库工作树可能有其他会话的未跟踪文件，绝不 `git add -A`。

**交付报告**：每步 commit 哈希与 `git show --stat`；act/01 附 `content_hash` 取值与来源 case 名；act/02 附 Red 原文、命令 1/2 输出末 10 行、`nc015_guard.sh --require-impl` 退出码；跳过项与剩余风险。
