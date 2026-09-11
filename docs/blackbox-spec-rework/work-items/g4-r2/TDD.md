# TDD：G4 第二批（先红后绿）

`export LC_ALL=en_US.UTF-8`；`S=openspec/learn-system-blackbox-architecture.md`；`F=pipeline/corpus/_fixture/mini_ed01`。

## 0. 开工基线

```bash
git merge-base --is-ancestor 38d44f3 HEAD && echo ANCESTOR_OK
git status --short -- openspec pipeline/corpus/_fixture         # 期望空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1            # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1   # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo "schemas exit=$?"           # 0
ls .venv/bin/check-jsonschema .venv/bin/python                  # 都存在
for i in 1 2 3; do shasum -a 256 ocr/data_work/sanche_pages/page_00$i.png; done   # 与 README Inputs 三个哈希一致
ls -l ocr/data_work/data/page_001.json ocr/data_work/data/page_002.json ocr/data_work/data/page_003.json
```

## 1. r2-01 Red → Green

| 判据 | Red | Green |
|---|---|---|
| `grep -c '^#### 3b\. 流派与视图标识格式' $S` | 0 | 1 |
| `sed -n '/^#### 3b\. /,/^#### 4\. /p' $S \| grep -c '^| \`sch_\|^| \`sv_\|^| \`cg_'` | 0 | 3 |
| `grep -c '待用户确认' $S` | 1 | 0 |
| `grep -c '§8.1 第 3b 节' $S` | 0 | 1 |
| `grep -c '^- \[x\] 把 §3.3 三行登记进规格' openspec/id-prefix-registry.md` | 0 | 1 |

## 2. r2-02 Red → Green

| 判据 | Red | Green |
|---|---|---|
| `ls $F 2>/dev/null \| wc -l` | 0 | ≥ 8 |
| `find $F -iname '*.png' -o -iname '*.pdf' -o -iname '*.jpg' \| wc -l` | 0 | 0 |
| `bash $F/verify.sh; echo exit=$?` | （脚本不存在） | 末行 `FIXTURE OK`，exit=0 |
| `FIXTURE_ASSET_ROOT=/nonexistent bash $F/verify.sh; echo exit=$?` | — | 含 3 行 `BLOCKED_SOURCE_ASSET_MISSING`，exit=3 |
| `.venv/bin/python -c "import yaml;d=yaml.safe_load(open('$F/spans.yaml'));print(len(d['spans']), len({s['batch_id'] for s in d['spans']}))"` | — | `43 5` |
| `.venv/bin/python -c "import yaml;print(sorted({s['page'] for s in yaml.safe_load(open('$F/spans.yaml'))['spans']}))"` | — | `['page_001', 'page_003']` |
| `grep -c 'known_unrecognizable' $F/anomalies.yaml` | — | 1 |
| `for m in m1 m2 m3; do .venv/bin/check-jsonschema --schemafile openspec/schemas/stage_package.schema.json $F/expected/$m.stage_package.yaml >/dev/null && echo ok-$m; done` | — | ok-m1 ok-m2 ok-m3 |
| `cmp $F/pages/page_001.json ocr/data_work/data/page_001.json && cmp $F/pages/page_003.json ocr/data_work/data/page_003.json && echo SAME` | — | SAME |
| 篡改（临时副本删一个 span）→ `FIXTURE_DIR=<副本> bash $F/verify.sh; echo exit=$?` | — | 含 `FAIL coverage`，exit=1 |
| 篡改（临时副本 page_001.json 改一字节）→ 同上 | — | 含 `FAIL manifest_sha256`，exit=1 |
| `.venv/bin/python $F/tools/build_fixture.py --out /tmp/mini_ed01_rebuild && diff -r --exclude=tools --exclude=README.md /tmp/mini_ed01_rebuild $F && echo REPRO_OK` | — | REPRO_OK |
| `sed -n '/^### 22\.1 /,/^### 22\.2 /p' $S \| grep -c '_fixture/mini_ed01'` | 0 | 1 |

## 3. r2-03 Red → Green

| 判据 | Red | Green |
|---|---|---|
| `bash openspec/acceptance/run_all.sh; echo exit=$?` | exit=127（不存在） | 11 条 + SUMMARY，exit=1 |
| `bash openspec/acceptance/run_all.sh \| grep -cE '^(PASS\|FAIL\|BLOCKED)  20\.[0-9]+  '` | 0 | 11 |
| `bash openspec/acceptance/run_all.sh \| grep -E '^(PASS\|FAIL\|BLOCKED)  20\.' \| awk '{print $2}' \| tr '\n' ' '` | — | `20.1 20.2 20.3 20.4 20.5 20.6 20.7 20.8 20.9 20.10 20.11 ` |
| `bash openspec/acceptance/run_all.sh \| grep -c '^FAIL  20\.7 '` | — | 1 |
| `bash openspec/acceptance/run_all.sh \| grep -E '^BLOCKED' \| grep -vc '前置缺失: '` | — | 0 |
| `bash openspec/acceptance/run_all.sh 20.7 \| grep -cE '^(PASS\|FAIL\|BLOCKED)  20\.'` | — | 1 |
| 临时副本 fixture 删一个 span → `FIXTURE_DIR=<副本> bash openspec/acceptance/run_all.sh 20.1 \| grep -c '^FAIL  20\.1 '` | — | 1 |
| `sed -n '/^## 20\./,/^## 21\./p' $S \| grep -cE '^[0-9]+\. '` | 11 | 11 |
| `sed -n '/^## 20\./,/^## 21\./p' $S \| grep -cE '^[0-9]+\. .*判据：.*run_all\.sh 20\.[0-9]+'` | 0 | 11 |
| `sed -n '/^## 20\./,/^## 21\./p' $S \| grep -c '准入阈值'` | 0 | 1 |
| `grep -c '_fixture/mini_ed01' $S` | 1（22.1） | ≥ 2 |

## 4. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                              # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1        # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo "schemas exit=$?"                # 0
git diff --check
git status --short | grep -v '^??' | grep -v -e 'openspec/learn-system-blackbox-architecture.md' -e 'id-prefix-registry' -e '_fixture/mini_ed01' -e 'openspec/acceptance/'   # 期望空（他人脏文件除外，原样报告）
```
