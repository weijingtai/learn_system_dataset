# mini_ed01 m4 金标（impl-00/05 独占 ACT，P4）

本目录是 **M4 Knowledge Extraction 薄接入**的验收宿主金标，供 impl-05 K4 以
`pipeline.knowledge_extraction.acceptance --fixture <mini_ed01> --gold-dir <本目录>` 使用。

## 金标内容与来源

- `submission_assertion_a.yaml`、`submission_assertion_b.yaml`、
  `submission_concept_mention_a.yaml` **逐字取** impl-05 定稿 `README.md` 附录 A
  （三件提交件；B 路 item 0/1 与 A 路逐字相同，item 1 仅 `relation: qualifies`）。
- `ruling_m4_d001.yaml` = 附录 A 四键（`schema_version` / `dispute_id` / `choice` / `rationale`）
  **追加两键** `synthetic_fixture: true`、`actor_ref: fixture:mini_ed01`
  （G7-RULINGS §9.7 第 52 条、§9.8 第 55 条；与 impl-05 附录 A 修订后内容逐字相同）。
- `candidate_set.yaml`：**canonical JSON 字节**（虽以 `.yaml` 命名，内容为
  `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")`，
  与 impl-05 act/00 `canonical_json` 同一函数规则）。其 `rejected[].detail` 冻结为
  `quote 不在 Span 内`（impl-05 act/01 TXT_001 文案）。
- `expected/m4.stage_package.yaml`：由 `build_expected_m4.py` **确定性产出**
  （只读 `candidate_set.yaml` 字节 + 四个输入金标；stdlib only；不 import
  `pipeline.knowledge_extraction`；无 uuid/时间/随机；两次运行字节相同）。
  信封 ID / lineage / logs 均为固定占位；`counts` 与 `manifest.content_sha256`
  由 `candidate_set` 计算。impl-05 的 `golden_match` 只比对 `counts` /
  `manifest.content_sha256` / payload 四个标量 / assertions 的
  `(assertion_id, proposition)` 列表，**不比对任何 ID/lineage/logs 字段**。

## 用法

```bash
.venv/bin/python pipeline/corpus/_fixture/mini_ed01/m4/build_expected_m4.py            # 写 expected/m4.stage_package.yaml
.venv/bin/python pipeline/corpus/_fixture/mini_ed01/m4/build_expected_m4.py --out DIR  # 写 DIR/expected/m4.stage_package.yaml
```

## SHA 冻结

`m4/SHA256SUMS` 记录六个文件（四个输入金标 + `candidate_set.yaml` +
`expected/m4.stage_package.yaml`）的 sha256，条目路径**相对本 fixture 目录**
（`pipeline/corpus/_fixture/mini_ed01/`），按路径排序。`verify.sh` 的 V9
在 fixture 目录内复算比对。

## 性质（P7）

本 ACT 为独占 ACT，**金标不由 impl-05 实现方生成**（不得 import/运行 impl-05 代码）。
m4 下人工裁决/签发类金标均为**测试合成**（`synthetic_fixture: true`，`actor_ref`
为 fixture 作者 `fixture:mini_ed01`）：**仅供验收宿主，不计入真实 `expert_verified`、
不得进入任何发布级别判定**，验收与实现不得把它当作真实人工决定。
