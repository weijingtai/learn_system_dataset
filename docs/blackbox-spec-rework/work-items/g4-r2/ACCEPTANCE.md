# ACCEPTANCE：G4 第二批（前缀登记 / D-15 / D-18）

状态：`READY`（待用户交外部 Agent 执行）

## 0. 转译审查（原规划者四查，2026-09-10）

- 忠实性：r2-01 对应用户 2026-09-10 前缀裁定与登记册 §5 待办；r2-02 对应 D-15 与「页图不进 Git」裁定；r2-03 对应 D-18；验收标准（三个既有门禁）未改动。
- 覆盖性：BDD §2/§3.1–3.6/§4.1–4.4 每条对应 TDD §1–§3 判据；失败路径由停手规则与 `verify.sh`/`run_all.sh` 的 FAIL/BLOCKED 语义覆盖；篡改可检出（BDD 3.4、4.3）证明判据不是永真。
- 可执行性：写路径均为新建或既有；锚点为 HEAD `38d44f3` 整行文本（主 Agent 已核对，见下）；命令只用 bash/awk/sed/grep/python(.venv)/sqlite3；常量（ID、哈希、尺寸、行/字数、batch 划分）全部硬编码；无模糊词；r2-02 60 分钟、其余 ≤ 60。
- 独立性：D、E 写不同文件（E 的规格改动限于 §20，D 限于 §8.1/§12.2/§22.1）；E `depends_on` D；两组串行。

锚点核对（`grep -Fxc`，HEAD `38d44f3`，2026-09-11 主 Agent 实跑）：r2-01 三处（§8.1 第 4 节标题、§12.2 占位子串、登记册 §5 待办）各 1；r2-02 §22.1 锚点 1；r2-03 三处（§20 标题、第 1 条、第 7 条）各 1；§20 编号行 11、含「判据：」0、`#### 3b.` 0（均为 Red 前提）。输入核对：三张 PNG sha256 与 README Inputs 一致；page_001/003 行数 4/39、字数 37/193（合 230）；page_002 行 0；`.venv/bin/check-jsonschema` 存在；`ge_ju_rules` 496 条、`original_text` 非空 0 条。

## 1. 范围核对

三个提交各只含允许文件；fixture 目录内 `find -iname '*.png' -o -iname '*.pdf'` 为 0；`git diff --check`。

## 2. 门禁与判据

- 回归：`verify-T.sh` 0 FAIL、`mutations.sh all` 109/109、`schemas/verify.sh` 0。
- TDD §1/§2/§3 全部 Green 值逐条实跑。
- `bash pipeline/corpus/_fixture/mini_ed01/verify.sh` 本机 exit 0；`FIXTURE_ASSET_ROOT=/nonexistent` exit 3 且三行 BLOCKED；两种篡改 exit 1。
- `build_fixture.py --out` 重放 `diff -r` 无差异。
- `run_all.sh` 11 行 + SUMMARY，退出 1，`20.7 FAIL 0/496`，其余 BLOCKED 且行名逐字属于 §19 主表第一列。

## 3. 语义与质量审查（主 Agent）

- `verify.sh` V1–V8 无空断言、无永真、无跳过；篡改任一被检对象都能让对应 V 项 FAIL（主 Agent 另做 ≥3 例矩阵外篡改：改 span 的 `end_offset`、改一个 `glyph_id`、改 expected m2 的 `content_sha256`）。
- `run_all.sh` 无把 BLOCKED 写成 PASS 的分支；`FIXTURE_DIR` 透传生效；`.venv` 缺失路径输出 BLOCKED 而非报错退出。
- §20 条目编号与条数不变；第 7 条阈值句存在；§3–§18 状态行未动。
- fixture 内容为机器转录，README 明确不作知识来源。

## 4. 结论

通过后主 Agent 更新 `SUBAGENT_TODO.md`（D-15、D-18 → `ACCEPTED`；前缀登记记入 D-08 条目）、`PLAN.md`、`HANDOFF.md`；G4 仅剩 D-16。
