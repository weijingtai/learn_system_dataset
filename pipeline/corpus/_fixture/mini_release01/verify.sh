#!/usr/bin/env bash
# mini_release01 fixture 自校验脚本（act/impl-07/20，INC-F）
#
# 用法：bash verify.sh
# 环境变量：
#   FIXTURE_DIR   待校验的 fixture 根目录（默认本脚本所在目录）
#
# 与 mini_ed01/verify.sh 的差别：**不要求任何页图**（本夹具的版次视图锚定
# mini_ed01 的 spans.yaml，不锚定页素材），因此不读 FIXTURE_ASSET_ROOT。
# 退出码语义与 mini_ed01/verify.sh 对齐：
#   任一 FAIL → 1；无 FAIL 但有 BLOCKED → 3；否则 0（末行 FIXTURE OK）。
#
# 检查项（每条打印 PASS/FAIL/BLOCKED 前缀）：
#   V1 host_files            宿主文件齐备（含返工版次 ed01r2 与三轮决定集）
#   V2 manifest_sha256       manifest.files[] 每项 sha256 与实际逐字节一致
#   V3 span_anchor           全部版次（含返工）证据链锚定 mini_ed01 金标 span
#   V4 views_validate        全部版次视图过 M7 的 model 校验纯函数
#   V5 expected_goldens      r1 == 创世引擎现算输出；r2/r3 == 增量引擎实跑产出（含决定集）；
#                            identity_delta_r3 与实跑一致；knowledge_sha256 一致
#   V6 no_page_assets        本目录无 png/jpg/jpeg/pdf，且不依赖任何页素材
set -u
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

FIXTURE_DIR="${FIXTURE_DIR:-$SCRIPT_DIR}"
if [ ! -d "$FIXTURE_DIR" ]; then
  echo "FAIL fixture_dir fixture 目录不存在: $FIXTURE_DIR"
  exit 1
fi
FIXTURE_DIR="$(cd "$FIXTURE_DIR" && pwd)"

PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "BLOCKED_ENV .venv missing"
  exit 3
fi

export FIXTURE_DIR REPO_ROOT PYTHONPATH="$REPO_ROOT"

"$PY" - <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

FIX = Path(os.environ["FIXTURE_DIR"])
REPO = Path(os.environ["REPO_ROOT"])
MINI_ED01_SPANS = REPO / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"

fails = []
blocked = 0


def emit(status, name, detail=""):
    print(("%s %s %s" % (status, name, detail)).strip())


def fail(name, detail):
    fails.append(name)
    emit("FAIL", name, detail)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ V1 宿主齐备
required = ["manifest.yaml"]
for edition in ("ed01", "ed99", "ed01r2"):
    for name in ("candidate_set.json", "reviewed_edition.json", "reviewed_edition_package.json"):
        required.append("%s/%s" % (edition, name))
for edition in ("ed99", "ed01r2"):
    required.append("%s/decisions.json" % edition)
required += [
    "expected/snapshot_r1.json",
    "expected/snapshot_r2.json",
    "expected/snapshot_r3.json",
    "expected/identity_delta_r3.json",
    "expected/snapshot_revisions.yaml",
]

missing = [rel for rel in required if not (FIX / rel).is_file()]
if missing:
    emit("BLOCKED_ENV", "host_files", "宿主文件缺失: %s" % ", ".join(missing))
    print("FIXTURE BLOCKED: %d" % len(missing))
    sys.exit(3)
emit("PASS", "host_files", "files=%d" % len(required))

manifest = yaml.safe_load((FIX / "manifest.yaml").read_text(encoding="utf-8"))
spans_doc = yaml.safe_load(MINI_ED01_SPANS.read_text(encoding="utf-8"))
spans = {s["span_id"]: s for s in spans_doc["spans"]}

# --------------------------------------------------------- V2 manifest 哈希一致
v2_bad = []
for item in manifest.get("files", []):
    raw = (FIX / item["path"]).read_bytes()
    actual = sha256_bytes(raw)
    if actual != item["sha256"]:
        v2_bad.append("%s sha256 %s != 清单 %s" % (item["path"], actual, item["sha256"]))
if v2_bad:
    fail("manifest_sha256", "; ".join(v2_bad))
else:
    emit("PASS", "manifest_sha256", "files=%d" % len(manifest.get("files", [])))

# ------------------------------------------------------------- V3 证据 span 锚定
anchor = manifest["span_anchor"]
anchor_sha = sha256_bytes(MINI_ED01_SPANS.read_bytes())
v3_bad = []
if anchor["sha256"] != anchor_sha:
    v3_bad.append("manifest.span_anchor.sha256 %s != 实际 %s" % (anchor["sha256"], anchor_sha))
if anchor.get("evidence_level") != spans_doc.get("evidence_level"):
    v3_bad.append("evidence_level %r != 金标 %r" % (anchor.get("evidence_level"), spans_doc.get("evidence_level")))
if len(manifest.get("editions", [])) < 2:
    v3_bad.append("版次数 %d < 2" % len(manifest.get("editions", [])))

# 全部视图块：两版次 + 返工版次（ed01r2 与 ed01 同 source，单列在 manifest.rework）
view_blocks = list(manifest["editions"]) + [manifest["rework"]]
link_count = 0
for edition in view_blocks:
    cset = json.loads((FIX / edition["views_dir"] / "candidate_set.json").read_text(encoding="utf-8"))
    reviewed = json.loads((FIX / edition["views_dir"] / "reviewed_edition.json").read_text(encoding="utf-8"))
    if cset["source_id"] != edition["source_id"]:
        v3_bad.append("%s candidate_set.source_id 与 manifest 不符" % edition["edition_key"])
    links = []
    for a in cset.get("assertions", []):
        links.extend(a.get("evidence", []))
    links.extend(reviewed.get("evidence_links", []))
    for link in links:
        link_count += 1
        span = spans.get(link["source_span_id"])
        if span is None:
            v3_bad.append("证据 span 未锚定金标: %s" % link["source_span_id"])
            continue
        if link["start_offset"] != span["start_offset"] or link["end_offset"] != span["end_offset"]:
            v3_bad.append("%s 偏移与金标 span 不符" % link["source_span_id"])
        if link["quote_sha256"] != sha256_bytes(span["text"].encode("utf-8")):
            v3_bad.append("%s quote_sha256 与金标 span 文本不符" % link["source_span_id"])
if v3_bad:
    fail("span_anchor", "; ".join(v3_bad[:3]))
else:
    emit("PASS", "span_anchor", "links=%d spans_sha256=%s" % (link_count, anchor_sha[:12]))

# --------------------------------------------------------------- V4 视图过 model
from pipeline.assembly.model import (  # noqa: E402
    validate_candidate_set,
    validate_reviewed_edition,
    validate_reviewed_package,
    validate_snapshot_knowledge,
)

decisions_by_round = {
    row["round"]: json.loads((FIX / row["file"]).read_text(encoding="utf-8"))["decisions"]
    for row in manifest.get("decisions", [])
}

v4_bad = []
for edition in view_blocks:
    view = FIX / edition["views_dir"]
    try:
        validate_candidate_set(json.loads((view / "candidate_set.json").read_text(encoding="utf-8")))
        validate_reviewed_edition(json.loads((view / "reviewed_edition.json").read_text(encoding="utf-8")))
        validate_reviewed_package(json.loads((view / "reviewed_edition_package.json").read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001
        v4_bad.append("%s: %s: %s" % (edition["edition_key"], type(exc).__name__, exc))
if v4_bad:
    fail("views_validate", "; ".join(v4_bad))
else:
    emit("PASS", "views_validate", "views=%d" % len(view_blocks))

# ---------------------------------------------------------------- V5 期望产物
from pipeline.assembly.canonical import canonical_json  # noqa: E402
from pipeline.assembly.gate import evaluate_genesis  # noqa: E402
from pipeline.assembly.genesis import assemble_genesis, propose_genesis  # noqa: E402

v5_bad = []
plan = yaml.safe_load((FIX / manifest["expected"]["snapshot_revisions"]).read_text(encoding="utf-8"))
for rev in plan["revisions"]:
    raw = (FIX / rev["knowledge_file"]).read_bytes()
    if sha256_bytes(raw) != rev["knowledge_sha256"]:
        v5_bad.append("%s knowledge_sha256 不符" % rev["knowledge_file"])

ed01 = manifest["editions"][0]
view = FIX / ed01["views_dir"]
cset = json.loads((view / "candidate_set.json").read_text(encoding="utf-8"))
reviewed = json.loads((view / "reviewed_edition.json").read_text(encoding="utf-8"))
prop = propose_genesis(cset, reviewed)
asm = assemble_genesis(cset, reviewed, prop["proposals"], id_range=manifest["id_range"])
if asm["knowledge_bytes"] != (FIX / manifest["expected"]["round1"]).read_bytes():
    v5_bad.append("r1 金标与创世引擎现算输出不一致")
gate = evaluate_genesis(candidate_set=cset, reviewed_edition=reviewed, knowledge=asm["knowledge"])
if not gate["passed"]:
    v5_bad.append("r1 未过创世独立 Gate: %s" % [k for k, v in gate["checks"].items() if not v["passed"]])

r2_raw = (FIX / manifest["expected"]["round2"]).read_bytes()
r2 = json.loads(r2_raw.decode("utf-8"))
try:
    validate_snapshot_knowledge(r2)
except Exception as exc:  # noqa: BLE001
    v5_bad.append("r2 未过 snapshot 校验: %s: %s" % (type(exc).__name__, exc))

# r2 金标必须逐字节等于**增量引擎实跑**的产出（ACT 26 一.1；基底号用计划里的固定常量）
from pipeline.assembly import orchestrate  # noqa: E402

def _view_of(block):
    view_dir = FIX / block["views_dir"]
    return {
        "source_id": block["source_id"],
        "candidate_set": json.loads((view_dir / "candidate_set.json").read_text(encoding="utf-8")),
        "reviewed_edition": json.loads((view_dir / "reviewed_edition.json").read_text(encoding="utf-8")),
    }


ed99 = manifest["editions"][1]
r1_rev = plan["revisions"][0]["snapshot_revision_id"]
r2_rev = plan["revisions"][1]["snapshot_revision_id"]
r3_rev = plan["revisions"][2]["snapshot_revision_id"] if len(plan["revisions"]) > 2 else None
try:
    run = orchestrate.assemble(
        json.loads((FIX / manifest["expected"]["round1"]).read_text(encoding="utf-8")),
        [_view_of(ed99)],
        decisions_by_round.get(2, []),
        incremental=True,
        base_snapshot_revision_id=r1_rev,
    )
except Exception as exc:  # noqa: BLE001
    v5_bad.append("r2 增量实跑失败: %s: %s" % (type(exc).__name__, exc))
else:
    if run["status"] != "complete":
        v5_bad.append("r2 增量实跑未完成合并: status=%s" % run["status"])
    elif run["result"]["knowledge_bytes"] != r2_raw:
        v5_bad.append("r2 金标与增量实跑产出不是字节等价的")
    if run["status"] == "complete" and run["result"]["knowledge"]["meta"]["base_snapshot_revision_id"] != r1_rev:
        v5_bad.append("r2.meta.base_snapshot_revision_id 不是计划里的 r1 修订号")
    # 不可比单元必须如实入册（夹具声明的无 collation_key 单元；不得静默跳过）
    rows = run["result"]["collation"]["not_comparable"] if run["status"] == "complete" else []
    if len(rows) != 1 or rows[0].get("reason") != "missing_collation_key":
        v5_bad.append("collation.not_comparable 与夹具声明不符: %r" % (rows,))

# r3（同书返工）金标必须逐字节等于「r2 → ed01r2」的**增量实跑**产出
if r3_rev is not None:
    rework = manifest["rework"]
    try:
        run3 = orchestrate.assemble(
            json.loads((FIX / manifest["expected"]["round2"]).read_text(encoding="utf-8")),
            [_view_of(rework)],
            decisions_by_round.get(3, []),
            incremental=True,
            base_snapshot_revision_id=r2_rev,
        )
    except Exception as exc:  # noqa: BLE001
        v5_bad.append("r3 返工实跑失败: %s: %s" % (type(exc).__name__, exc))
    else:
        if run3["status"] != "complete":
            v5_bad.append("r3 返工实跑未完成合并: status=%s pending=%r" % (run3["status"], run3.get("pending")))
        else:
            r3_raw = (FIX / manifest["expected"]["round3"]).read_bytes()
            if run3["result"]["knowledge_bytes"] != r3_raw:
                v5_bad.append("r3 金标与返工实跑产出不是字节等价的")
            delta_file = FIX / manifest["expected"]["identity_delta_r3"]
            if canonical_json(run3["result"]["identity_delta"]) != delta_file.read_bytes():
                v5_bad.append("identity_delta_r3 与返工实跑产出不一致")
            changes = sorted(e["change_type"] for e in run3["result"]["identity_delta"]["entries"])
            if changes != ["merged", "retired"]:
                v5_bad.append("返工轮身份变化不符预期（期望 merged+retired）: %r" % (changes,))
            for name, value in (("assembly_seq", 3),):
                if run3["result"]["knowledge"]["meta"].get(name) != value:
                    v5_bad.append("r3.meta.%s != %r" % (name, value))

if v5_bad:
    fail("expected_goldens", "; ".join(v5_bad[:3]))
else:        emit("PASS", "expected_goldens", "rounds=%d r2=实跑产出" % len(plan["revisions"]))

# ---------------------------------------------------------------- V6 无页素材
images = [
    str(p.relative_to(FIX))
    for p in FIX.rglob("*")
    if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf")
]
if images:
    fail("no_page_assets", "本目录出现图像/PDF 文件: %s" % ", ".join(images))
else:
    emit("PASS", "no_page_assets", "本夹具不要求任何页图")

# -------------------------------------------------------------------- 退出码
if fails:
    print("FIXTURE FAILURES: %d" % len(fails))
    sys.exit(1)
if blocked:
    sys.exit(3)
print("FIXTURE OK")
sys.exit(0)
PY

rc=$?
if [ "$rc" -eq 0 ]; then
  exit 0
fi
exit "$rc"
