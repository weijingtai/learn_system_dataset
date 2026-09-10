# T-06 Executor Prompt

你是 T-06 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t06/README.md`
- `docs/blackbox-spec-rework/work-items/t06/BDD.md`
- `docs/blackbox-spec-rework/work-items/t06/TDD.md`
- `docs/blackbox-spec-rework/work-items/t06/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 9 FAIL，T-06 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` §16 PublicationPackage 清单后，为 `EvidenceMapPack` 补充内容定义与约束说明：
   - **逐段写出完整无损证据链**：`EvidenceLink → Assertion → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`。明确声明：SourceAnchor 作为发布期证据锚点必须随包发布，严禁留在 M3 内部而不进发布包；
   - **坐标系同源可换算强约束**：字框坐标系必须与 `SourceAssetPack` 中对应页图的像素尺寸同源可换算，保证客户端在渲染时能够实现精确高亮与原图叠绘；
   - **发布门禁检查**：该链路的完整性与引用闭合性是 `ValidationReport` 的 fail-closed 一票否决检查项；任一证据链断裂或悬空引用直接阻断 PublicationPackage 签发。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t06/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 9 严格减少至 8，且 T-06 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: define EvidenceMapPack content and lossless evidence chain`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、EvidenceMapPack 定义对照及全局 T 结果。
