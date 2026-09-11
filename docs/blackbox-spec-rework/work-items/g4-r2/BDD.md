# BDD：G4 第二批

Given 通用：主工作树 HEAD 祖先含 `38d44f3`（E 组还须含 D 组两个提交），`export LC_ALL=en_US.UTF-8`，`.venv` 存在。

## 1. 回归（每个 ACT 完成后）

- `verify-T.sh` 尾行 `FAIL 合计: 0`；`mutations.sh all` `109/109 rejected`；`openspec/schemas/verify.sh` exit 0；`git diff --check` 无输出。

## 2. r2-01 前缀登记

- Then §8.1 出现 `#### 3b. 流派与视图标识格式（用户 2026-09-10 确认）` 小节，表内恰三行 `sch_` / `sv_` / `cg_`；§12.2 不再含「待用户确认」占位句而含指向 §8.1 3b 与登记册的句子；`openspec/id-prefix-registry.md` §5 第一项勾选。

## 3. r2-02 mini fixture

### 3.1 结构
- Then `pipeline/corpus/_fixture/mini_ed01/` 含 `README.md`、`manifest.yaml`、`pages/page_001.json`、`pages/page_002.json`、`pages/page_003.json`、`source/transcript_v1.md`、`anomalies.yaml`、`spans.yaml`、`expected/m1.stage_package.yaml`、`expected/m2.stage_package.yaml`、`expected/m3.stage_package.yaml`、`tools/build_fixture.py`、`verify.sh`；目录内无任何图像文件。

### 3.2 正常路径（本机有素材）
- When `bash pipeline/corpus/_fixture/mini_ed01/verify.sh`
- Then exit 0，输出以 `PASS` 开头的检查行 ≥ 8，末行 `FIXTURE OK`。

### 3.3 素材缺失
- When `FIXTURE_ASSET_ROOT=/nonexistent bash pipeline/corpus/_fixture/mini_ed01/verify.sh`
- Then 非图像检查照常执行并全部 PASS，输出含 `BLOCKED_SOURCE_ASSET_MISSING ocr/data_work/sanche_pages/page_001.png`（三页各一行），exit 3，且不创建任何文件。

### 3.4 篡改可检出
- Given 复制 fixture 到临时目录并删除 `spans.yaml` 中任一 span
- When 对该副本运行 verify（`FIXTURE_DIR=<副本>`）
- Then exit 1，输出含 `FAIL coverage`。
- Given 改动 `pages/page_001.json` 一个字节
- Then exit 1，输出含 `FAIL manifest_sha256`。

### 3.5 可重放
- When 本机有素材时运行 `.venv/bin/python pipeline/corpus/_fixture/mini_ed01/tools/build_fixture.py --out <临时目录>`
- Then 临时目录与仓库内 fixture 逐字节相同（`diff -r` 无输出，`tools/` 与 `README.md` 除外）。

### 3.6 规格引用
- Then §22.1 新增一条 bullet 指向 fixture 路径。

## 4. r2-03 §20 判据化

### 4.1 输出形态
- When `bash openspec/acceptance/run_all.sh`
- Then 恰 11 行匹配 `^(PASS|FAIL|BLOCKED)  20\.(1|2|3|4|5|6|7|8|9|10|11)  `，每个编号恰一次，顺序 1→11；BLOCKED 行含 `前置缺失:` 与一个 §19 差距行名；末行 `SUMMARY pass=<n> fail=<n> blocked=<n>`；退出码 = FAIL 条数。
- When `bash openspec/acceptance/run_all.sh 20.7`
- Then 只输出该一行（加 SUMMARY），退出码同规则。

### 4.2 当前预期状态（HEAD + fixture 存在）
- Then `20.7` 为 `FAIL`（496 条 rule `original_text` 全空，准入阈值不满足）；`20.1`、`20.3`、`20.4`、`20.10` 的 fixture/契约前置子检查 PASS 后为 `BLOCKED`；其余为 `BLOCKED`；总退出码 1。

### 4.3 fixture 缺陷上浮
- Given 临时副本 fixture 删除一个 span，`FIXTURE_DIR=<副本> bash openspec/acceptance/run_all.sh 20.1`
- Then `FAIL  20.1`（不是 BLOCKED）。

### 4.4 §20 文本
- Then §20 仍恰 11 条、编号不变；列表前有一段说明判据入口；每条末尾含 `判据：` 与 `run_all.sh 20.N`；第 7 条含准入阈值句。

## 5. 失败路径
- 素材缺失/哈希不符、`check-jsonschema` 不可用、锚点不唯一 → 停手报告。
