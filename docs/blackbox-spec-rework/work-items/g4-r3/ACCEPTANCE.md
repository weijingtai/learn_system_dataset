# ACCEPTANCE：G4 第三批（D-16 映射表 / pat_ ent_ 登记）

状态：`READY`（待用户交外部 Agent 执行；`PLAN.md` 时间窗：C/S 会话 2026-09-11 承诺 NC-004 验收完成之前不碰）

## 0. 转译审查（原规划者四查，2026-09-11）

- 忠实性：r3-01 对应 D-design §D-16 的三列表、三选一标注、重复登记收敛与「零删行」判据；r3-02 对应用户 2026-09-11 对登记册 §3.4 的确认。
- 覆盖性：BDD 1.1–1.6、2.1–2.2 各有 TDD §1/§2 判据；篡改可检出（BDD 1.6）由 ACT verify 两例自检与主 Agent 矩阵外篡改证明。
- 可执行性：四个替换锚点与一个插入锚点均为 HEAD 整行文本（主 Agent 核对见下）；表 A 19 行首列名逐字取自 §19；表 B 43 个开头文字逐一核对为恰 1 条 `- [ ]`；owner 路径均存在。
- 独立性：单执行者串行两 ACT；r3-02 只碰规格 §8.1。

锚点核对（主 Agent 脚本，2026-09-11，HEAD `ed7ef7e` 之后的工作树）：r3-01 四个替换/插入锚点各 1；表 A 首列与 §19 主表 19 个首列名集合相等；表 B 43 条开头文字各恰匹配 1 条 `- [ ]`，标注三值合法；PLAN 未勾选 63 条，减 43 后余 20 条全部位于 G6 闭集各节；表 A/B 所有 owner 路径存在；`superseded-by` 引用的 11 个提交 hash `git cat-file -e` 全部存在；r3-02 两个锚点各 1，`pat_<technique>_<6位数字>` 与 `ent_<32hex>` 在规格中均 0（Red 前提）。

## 1. 范围核对

r3-01 提交恰 5 文件、r3-02 恰 1 文件；`git diff <base> -- PLAN.md` 零 `-` 内容行；`git diff --check`。

## 2. 门禁与判据

- 三门禁：`verify-T.sh` 0 FAIL、`mutations.sh all` 109/109、`schemas/verify.sh` 0。
- TDD §1/§2 全部 Green 值逐条实跑（在 `git archive` 干净树上）。
- `check_d16.py` 六条规则逐条对照 ACT `checker`，无 try/except 吞错。

## 3. 语义与质量审查（主 Agent）

- 表 A：每行 owner 是「细节所在文件」而非仅 PLAN 自身；§19 的 19 行不多不少。
- 表 B：`superseded-by` 的取代者必须是已在 HEAD 的提交或章节（主 Agent 逐条 `git cat-file -e`/grep）；`out-of-scope` 只用于 §22 明示暂缓或改七政后不再适用的项。
- 矩阵外篡改 ≥3 例（临时副本，`check_d16.py --plan 副本`）：删表 A 一行 → `R2` FAIL；把某行 owner 改成不存在路径 → `R2` FAIL；把 C 节一条改成 `- [x]` → `R5` FAIL；把 PLAN 黑箱节某条 `- [ ]` 移到 G6 节之外的新标题下 → `R4` FAIL。
- r3-02：sch_/sv_/cg_ 三行字节不变；两新行格式与登记册 §3.4 一致。

## 4. 结论

通过后主 Agent：SUBAGENT_TODO D-16 → `ACCEPTED`，G4 D 类全部 `ACCEPTED`；随后单独提交勾选 PLAN 中表 B 标 `superseded-by` 且证据在 HEAD 的条目（附提交 hash），此时才允许出现 `- [ ]` → `- [x]` 的改动；再同步 PLAN/HANDOFF，进入 G5 总准出。
