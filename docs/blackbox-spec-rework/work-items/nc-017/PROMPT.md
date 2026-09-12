# NC-017 执行提示

发送前提：wjt-react 四查 READY；NC-011 CLIENT 线 act/06 已提交。主 Agent 经 `~/tmux-agents` 派给 agy；分隔线以下全文即提示词。

---

你执行 NC-017：在 Flutter 包 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，绝不在那里执行 git；learn_system 只读，交付报告除外）实现口令加密导出文件的格式层与写入器。单线串行，不要启动子 agent。每条 flutter 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`，`pub get` 只用 `--offline`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-017/` 下 README.md、BDD.md、TDD.md、ACT.yaml、act/01～02.yaml、ACCEPTANCE.md；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/private_export.md`（全文逐字照做）。

**开工前**：`git log --oneline -1` 的提交信息必须含 `NC-011-F`，否则停手。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文，再实现。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：清单外任何文件；cryptography 以外的依赖；真实网络；`skip`；永真断言；在测试内调用被测函数生成参考值（K、D、头部字节、各摘要一律用契约 §7 字面量）；`git push`；删除文件。

**进度文件**：开工时创建 `/Users/jingtaiwei/tmux-agents/runs/nc017.progress.md`，内容恰为：

```
## 阶段 1 act/01
- [ ] NC-017-A
## 阶段 2 act/02
- [ ] NC-017-B
```

每完成一步把对应行改为 `- [x] NC-017-X <commit 前 7 位>`。

**遇到下列情况立即停止，不要自己决定**：契约有两种解释；参考值对不上；`pub get` 改动其他包；需要改清单外文件；既有测试变红。停止时先在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-017/DELIVERY_REPORT.md` 追加「## 待裁决」（现象、命令、原文、你看到的选项），再在进度文件末尾追加 `待裁决：NC-017-X 见 DELIVERY_REPORT.md`，对话最后单独输出 `NC-017-X 停手待裁决`，不再继续。

**提交**：两步各一个提交，只 `git add` 本步文件，消息按各 ACT 的 COMMIT_MESSAGE，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT.md`（不 git add），每步一节：commit 哈希与 `git show --stat` 原文；Red 命令、退出码、原文；VERIFICATION 每条命令的退出码与末 20 行；act/01 另附 `pubspec.lock` 中 cryptography 段原文；act/02 另附 `nc017_guard.sh --require-impl` 退出码。全部完成后对话最后单独输出一行 `NC-017 完成`。
