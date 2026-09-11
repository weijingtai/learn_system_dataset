# ACCEPTANCE：G4 第二批（前缀登记 / D-15 / D-18）

状态：r2-01 / r2-02 `ACCEPTED`（`851fa70`、`6fc8536`）；r2-03 `REVIEWING`（`4884b6a` 判据全绿，仅回退分支需按裁定 3 返工，见 §5 与 `PROMPT-E2.md`）

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

## 5. 验收记录（主 Agent，2026-09-11）

方法：把待验提交 `git archive` 到 scratchpad 干净目录（软链 `.venv`），避免同工作树 C/S 会话未提交文件干扰；页图根用 `FIXTURE_ASSET_ROOT` 指向本机 `ocr/data_work/sanche_pages`。

### 5.1 三件裁定（执行者上报）

1. 哈希环：ACT 缺陷，采纳执行者解法（`manifest.files` 限 6 个非 expected 文件，期望包由 V5+V6 钉死）。已回写 `act/r2-02.yaml`。
2. offset 读法：严格 offset，采纳。已回写 `act/r2-02.yaml`。
3. 仓库外副本 `verify.sh` 推不出仓库根：script_spec 缺陷；裁定 `fx()` 一律调用仓库内规范脚本并透传 `FIXTURE_DIR`，不接受回退分支。已回写 `act/r2-03.yaml`；E 组按 `PROMPT-E2.md` 返工一处。

并发提交非线性（nc-002 的 `301a99c` 夹在 D 组两提交之间）：文件范围无交集，不影响验收。

### 5.2 r2-01（`851fa70`）ACCEPTED

范围 2 文件；TDD §1 五条全 Green；`text_3b` 与 `replacement_substring` 逐字一致，3b 节后接空行再接 `#### 4.`；§8 状态行仍为「待验证假设」；门禁绿。

### 5.3 r2-02（`6fc8536`）ACCEPTED

范围 14 文件、无图像；TDD §2 十三条全 Green（`FIXTURE OK` exit 0；缺图 exit 3 且 3 行 BLOCKED；`43 5`；页集 `['page_001','page_003']`；Schema ok-m1..m3；三页 JSON 与 OCR 原件逐字节相同；`REPRO_OK`；§22.1 命中 1）。矩阵外篡改 6 例全部 exit 1 并命中对应 V 项：删 span → coverage；页 JSON 改 1 字节 → manifest_sha256+anchors；`end_offset`+1 → coverage；改 `glyph_id` → anchors（把 manifest/m3 哈希同步改掉后仍被 anchors 抓住，证明 V4 独立于 V1）；改 m2 `content_sha256` → expected_hash；改 bbox.w → anchors；改 `span_id` 前缀 → ids（V2）；改 anomalies 终态 → coverage。`verify.sh` 六处 `continue` 均在追加失败记录之后，非跳过；退出逻辑 1/3/0 与定义一致；`build_fixture.py` 只用标准库 + yaml，无时间戳/随机；`--ocr-data /nonexistent` → `BLOCKED_SOURCE_ASSET_MISSING` exit 3 且不建目录。主 Agent 自误两条已撤回（传绝对路径 `--asset-root` 导致 path_ref 差异；页图不是生成器输入）。

### 5.4 r2-03（`4884b6a`）REVIEWING → 返工一处

范围 2 文件；门禁绿；TDD §3 十一条全 Green（11 行 + SUMMARY、exit 1、`FAIL  20.7` 含 `0/496`、BLOCKED 全带「前置缺失: 」且 5 个行名逐字属于 §19 第一列、副本删 span 后 `20.1` 为 FAIL、未篡改副本仍 BLOCKED）；§20 除第 7 条替换外各条原文不变、11 条编号连续、判据后缀齐全、intro 段逐字一致。唯一不通过：`run_all.sh` `fx()` 先跑 `$FIXTURE_DIR/verify.sh`，仅在 `BLOCKED_ENV` 时回退到规范脚本，违反裁定 3。返工后主 Agent 复验 TDD §3 全部判据 + 「副本 verify.sh 被篡改为直接打印 FIXTURE OK 时 20.1 仍按规范脚本判定」。
