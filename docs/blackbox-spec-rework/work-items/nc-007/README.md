# NC-007：历史差异、恢复与冲突处理旅程

- 任务 ID：`NC-007`
- 状态：`REWORK`（2026-09-11 主 Agent 验收：act/01～04 形式门禁通过，盲测发现两处实质缺陷——长文差异在中间区 > 2000 行时整篇删插、手动合并工作区自动保存导致合并提交失败；追加 act/05、act/06，契约 §6）。原状态 `READY`
- 目标：在 Flutter 包 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes` 实现历史修订列表、纯本地长文差异对比、多分支冲突检测与 PRD 旅程 6 四选项冲突处理完整路径。
- 依赖：`NC-004`（Drift 修订库与仓储接口）、`NC-005`（编辑器控制器与页面）、`NC-006`（撤销/重做栈支持）。
- 仓库：`xuan-migration/reading-notes`（独立 Git 仓库）；`xuan-migration` 父目录不是 Git 仓库；`learn_system` 仓库只读。

---

## 1. 目标与范围

1. **纯本地差异算法** (`lib/src/history/revision_compare.dart`)：
   - 行级别/段落级别比较，输出新增、删除、未变更块；
   - 连续未变更超过 3 行默认折叠，提供展开与上/下一处变更导航；
   - 支持 1 MiB 大文本，单线程计算无溢出；
   - 绝不调用任何服务端明文 diff 接口。
2. **历史修订页面** (`lib/src/history/revision_history_page.dart`)：
   - 遍历并展示历史修订（ID、时间、设备、说明、父版本、恢复来源）；
   - 支持查看任意修订快照；
   - 恢复旧版调用 `NoteRepository.restoreRevision`，生成带 `restored_from` 的新修订，不破坏历史链。
3. **冲突处理控制器与横幅** (`lib/src/history/revision_conflict_controller.dart`、`conflict_banner.dart`)：
   - 多 head（≥2）进入冲突态；
   - 顶部横幅非阻断展示，正文默认本机版本且保持自由编辑与自动保存；
   - 提供四选项：保留本机、采用对方、手动合并、稍后处理；
   - 选稍后处理后横幅在当前会话内不再自动弹出，不阻断任何编辑；
   - 手动合并工作区复用 NC-006 撤销栈，提交前收到新分支不覆盖当前合并稿。

---

## 2. 禁止项

1. 禁止写入 `learn_system` 仓库（本工作包除外）；
2. 禁止修改 `xuan-migration` 其他子目录；
3. 禁止修改 NC-004、NC-005、NC-006 既有实现与测试；
4. 禁止修改 `pubspec.yaml` 与 `pubspec.lock`（零新依赖）；
5. 禁止调用服务端明文 diff 接口；
6. 禁止在测试中使用 `skip` 或永真断言；
7. 禁止物理删除或直接覆写旧修订。

---

## 3. 门禁与验证

- 基线命令：`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`
- 静态分析：`flutter analyze` 报告 0 issues
- 单元与集成测试：`flutter test` 报告 `+145: All tests passed!`
- 专属守卫：`bash docs/blackbox-spec-rework/reviews/nc007_guard.sh --require-impl`
