# NC-016a 执行提示（两线并行）

发送前提：wjt-react 四查 READY。两节分别交给两个执行者（tmux + `cmd --yolo`），分隔线以下全文即提示词。

## STORAGE 线（act/01）

---

你执行 NC-016a 的 STORAGE 线 act/01，单线完成，不要启动子 agent。仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage`（上级 xuan-migration 不是 git 仓库，绝不在那里执行 git）。**该仓库 AGENTS.md 禁止在 main 上改代码**：先在仓库根执行 `git worktree add .worktrees/nc016-guard-aad -b fix/nc016-guard-aad 8ddb877`，之后一切改动、测试、提交都只在 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage/.worktrees/nc016-guard-aad` 内进行；worktree 的 `core`、`drift`、`p2p` 三包各运行一次 `PATH=/Users/jingtaiwei/flutter/bin:$PATH flutter pub get`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-016a/` 下 README.md、BDD.md（X01～X03）、TDD.md §1～§2、act/01.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/private_sync_impl.md` §1、§2.1、§3、§10 与 `private_sync.md` §3.3、§7（逐字照做）；xuan-storage `AGENTS.md`。

**先写测试再改实现**：按 TDD §2 先记录改动前通过数，复制样例、写测试，取得 Red 原文，再实现。

**只允许写**：act/01.yaml WRITE_NEW 清单。禁止：main 上任何写入、merge、rebase、push；其他 worktree；清单外文件；pubspec；新依赖；改既有断言；`skip`；永真断言；删除文件；git add `.dart_tool` 或 `pubspec.lock`。

**停手**：契约两种解释、worktree 或 pub get 失败、需改 pubspec、既有测试变红、需要在 main 上操作时立即停止：在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-016a/DELIVERY_REPORT_STORAGE.md` 追加「## 待裁决」（现象、命令、原文、你看到的选项），在进度文件末尾追加 `待裁决：NC-016a-A`，对话最后单独输出 `NC-016a-A 停手待裁决`。

**进度文件**：`/Users/jingtaiwei/tmux-agents/runs/nc016s.progress.md`，内容恰为 `## 阶段 1 STORAGE act/01` 与 `- [ ] NC-016a-A` 两行；完成后改为 `- [x] NC-016a-A <commit 前 7 位>`。

**提交**：一个提交，在分支 `fix/nc016-guard-aad`，只 `git add` 清单文件，消息 `fix(sync): guard 比较设备 ID/指纹/过期，BlobCipher 可选 AAD（NC-016a-A）`，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_STORAGE.md`（不 git add）：worktree 创建与 pub get 输出；改动前通过数；Red 原文；commit 哈希与 `git show --stat`；VERIFICATION 每条退出码与末 20 行；守卫 `--require-impl storage` 退出码。完成后对话最后单独输出 `NC-016a STORAGE 线完成`。

## CLIENT 线（act/02 → act/03）

---

你执行 NC-016a 的 CLIENT 线：act/02 → act/03 严格串行，不要启动子 agent。仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 git 仓库；上级 xuan-migration 不是 git 仓库，绝不在那里执行 git）。每条 flutter 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-016a/` 下 README.md、BDD.md（S01～S17）、TDD.md §1、§3～§4、act/02～03.yaml；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/private_sync_impl.md` 全文与 `private_sync.md` §4.3、§4.4、§6、§10（逐字照做）；`local-persistence.md` §5、§5.2。

**开工前**：`git log --oneline -1` 为 `4a0d70a` 开头、`git status --short` 为空，否则停手。

**先写测试再改实现**：每步先写本步测试取得真实 Red 原文，再实现；act/03 的 S07「密文无明文」写在最前；S08 参考值逐字取自契约 §9，禁止在测试内调用被测函数生成期望值。

**只允许写**：各 ACT 的 WRITE_NEW 清单；`note_repository.dart` 只在类末尾追加。禁止：清单外文件；pubspec；新依赖；改既有测试期望；真实网络；`skip`；永真断言；`git push`；删除文件。

**停手**：契约两种解释、§9 参考值对不上（含 `newKeyPairFromSeed` 与 pyca 不一致）、需改仓储既有方法或 act/02 文件、既有测试变红时立即停止：在 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-016a/DELIVERY_REPORT_CLIENT.md` 追加「## 待裁决」，在进度文件末尾追加 `待裁决：NC-016a-X`，对话最后单独输出 `NC-016a-<B|C> 停手待裁决`。

**进度文件**：`/Users/jingtaiwei/tmux-agents/runs/nc016c.progress.md`，内容恰为：

```
## 阶段 1 CLIENT act/02
- [ ] NC-016a-B
## 阶段 2 CLIENT act/03
- [ ] NC-016a-C
```

每完成一步改为 `- [x] NC-016a-X <commit 前 7 位>`。

**提交**：两步各一个提交，只 `git add` 本步文件，消息按各 ACT 的 COMMIT_MESSAGE，末尾空一行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：`DELIVERY_REPORT_CLIENT.md`（不 git add），每步一节：commit 哈希与 `git show --stat`；Red 原文；VERIFICATION 每条退出码与末 20 行；act/03 另附守卫 `--require-impl client` 退出码。完成后对话最后单独输出 `NC-016a CLIENT 线完成`。
