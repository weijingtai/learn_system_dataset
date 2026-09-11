#!/usr/bin/env bash
# mini_ed01 fixture 自校验脚本（D-15）
#
# 用法：bash verify.sh
# 环境变量：
#   FIXTURE_DIR        待校验的 fixture 根目录（默认本脚本所在目录）
#   FIXTURE_ASSET_ROOT 页图素材根目录（默认 ocr/data_work/sanche_pages，相对仓库根）
#
# 退出码：任一 FAIL → 1；无 FAIL 但有 BLOCKED → 3；否则 0（末行 FIXTURE OK）。
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

ASSET_ROOT_IN="${FIXTURE_ASSET_ROOT:-ocr/data_work/sanche_pages}"
case "$ASSET_ROOT_IN" in
  /*) ASSET_ABS="$ASSET_ROOT_IN" ;;
  *)  ASSET_ABS="$REPO_ROOT/$ASSET_ROOT_IN" ;;
esac

PY="$REPO_ROOT/.venv/bin/python"
CJS="$REPO_ROOT/.venv/bin/check-jsonschema"
SCHEMA="$REPO_ROOT/openspec/schemas/stage_package.schema.json"

if [ ! -x "$PY" ] || [ ! -x "$CJS" ]; then
  echo "BLOCKED_ENV .venv missing"
  exit 3
fi

export FIXTURE_DIR ASSET_ABS REPO_ROOT SCHEMA CJS

"$PY" - <<'PY'
import hashlib
import json
import os
import re
import struct
import subprocess
import sys

import yaml

FIX = os.environ["FIXTURE_DIR"]
ASSET_ROOT = os.environ["ASSET_ABS"]
SCHEMA = os.environ["SCHEMA"]
CJS = os.environ["CJS"]

fails = []
blocked = 0


def emit(status, name, detail=""):
    if detail:
        print("%s %s %s" % (status, name, detail))
    else:
        print("%s %s" % (status, name))


def fail(name, detail):
    fails.append(name)
    emit("FAIL", name, detail)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(rel):
    with open(os.path.join(FIX, rel), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_json(rel):
    with open(os.path.join(FIX, rel), encoding="utf-8") as fh:
        return json.load(fh)


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def transcript_blocks(path):
    """返回 {page: 该页文本块}；块 = 该节各行以 "\\n" 连接（不含节标题，尾部空行剔除）。"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    blocks = {}
    cur = None
    buf = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if cur is not None:
                while buf and buf[-1] == "":
                    buf.pop()
                blocks[cur] = "\n".join(buf)
            cur = line[3:].strip()
            buf = []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        while buf and buf[-1] == "":
            buf.pop()
        blocks[cur] = "\n".join(buf)
    return blocks


# ---------------------------------------------------------------- 读取 fixture
manifest = None
try:
    manifest = load_yaml("manifest.yaml")
except Exception as exc:  # noqa: BLE001
    fail("manifest_sha256", "manifest.yaml 不可读: %s" % exc)

if manifest is None:
    for name in ("ids", "coverage", "anchors", "expected_schema", "expected_hash", "assets"):
        fail(name, "前置缺失: manifest.yaml 不可读")
    emit("PASS", "no_images", "(空目录)")
    print("FIXTURE FAILURES: %d" % len(fails))
    sys.exit(1)

page_names = [a["page"] for a in manifest["source_assets"]]
asset_sha = {a["page"]: a["sha256"] for a in manifest["source_assets"]}

# ---------------------------------------------------------- V1 manifest_sha256
v1_bad = []
for item in manifest.get("files", []):
    target = os.path.join(FIX, item["path"])
    if not os.path.exists(target):
        v1_bad.append("%s 缺失" % item["path"])
    elif sha256_file(target) != item["sha256"]:
        v1_bad.append("%s sha256 不符" % item["path"])
if v1_bad:
    fail("manifest_sha256", "; ".join(v1_bad))
else:
    emit("PASS", "manifest_sha256", "files=%d" % len(manifest.get("files", [])))

# ---------------------------------------------------------------- V2 ids
ID_RULES = (
    ("src_", re.compile(r"^src_[a-z0-9]+_ed[0-9]{2}$")),
    ("ss_", re.compile(r"^ss_[a-z0-9]+_ed[0-9]{2}_p[0-9]{4}_s[0-9]{2}$")),
    ("art_", re.compile(r"^art_[0-9a-f]{32}$")),
    ("rev_", re.compile(r"^rev_[0-9a-f]{32}$")),
    ("pkg_m", re.compile(r"^pkg_m[1-8]_[0-9a-f]{32}$")),
    ("prun_", re.compile(r"^prun_[0-9a-f]{32}$")),
    ("srun_", re.compile(r"^srun_[0-9a-f]{32}$")),
)
ID_KEYS = (
    "source_id",
    "span_id",
    "artifact_id",
    "artifact_revision_id",
    "stage_package_id",
    "processing_run_id",
    "step_run_id",
    "configuration_artifact_revision_id",
    "input_artifact_revision_ids",
    "output_artifact_revision_ids",
    "edition_part_artifact_id",
)


def collect_ids(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ID_KEYS:
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, list):
                    out.extend([x for x in v if isinstance(x, str)])
            collect_ids(v, out)
    elif isinstance(node, list):
        for x in node:
            collect_ids(x, out)


def rule_for(value):
    for probe, rx in ID_RULES:
        if value.startswith(probe):
            return rx
    return None


v2_bad = []
v2_seen = 0
for rel, node in (
    ("manifest.yaml", manifest),
    ("spans.yaml", None),
    ("expected/m1.stage_package.yaml", None),
    ("expected/m2.stage_package.yaml", None),
    ("expected/m3.stage_package.yaml", None),
):
    try:
        doc = node if node is not None else load_yaml(rel)
    except Exception as exc:  # noqa: BLE001
        v2_bad.append("%s 不可读: %s" % (rel, exc))
        continue
    found = []
    collect_ids(doc, found)
    for value in found:
        v2_seen += 1
        rx = rule_for(value)
        if rx is None:
            v2_bad.append("%s 中 %s 无已登记前缀" % (rel, value))
        elif not rx.match(value):
            v2_bad.append("%s 中 %s 格式非法" % (rel, value))
if v2_bad:
    fail("ids", "; ".join(v2_bad[:5]))
else:
    emit("PASS", "ids", "checked=%d" % v2_seen)

# ---------------------------------------------------------------- V3 coverage
try:
    spans_doc = load_yaml("spans.yaml")
    spans = spans_doc["spans"]
except Exception as exc:  # noqa: BLE001
    spans = None
    fail("coverage", "spans.yaml 不可读: %s" % exc)

try:
    blocks = transcript_blocks(os.path.join(FIX, "source/transcript_v1.md"))
except Exception as exc:  # noqa: BLE001
    blocks = None
    if spans is not None:
        fail("coverage", "transcript 不可读: %s" % exc)

try:
    anomalies = load_yaml("anomalies.yaml")
except Exception as exc:  # noqa: BLE001
    anomalies = None

if spans is not None:
    v3_bad = []
    for page in ("page_001", "page_003"):
        block = (blocks or {}).get(page)
        if block is None:
            v3_bad.append("%s transcript 缺节" % page)
            continue
        page_spans = sorted([s for s in spans if s["page"] == page], key=lambda s: s["start_offset"])
        pos = 0
        for i, sp in enumerate(page_spans):
            if sp["start_offset"] != pos:
                v3_bad.append("%s span %s start_offset=%d 期望 %d（有缺口或重叠）" % (page, sp["span_id"], sp["start_offset"], pos))
                break
            if block[sp["start_offset"]:sp["end_offset"]] != sp["text"]:
                v3_bad.append("%s span %s 的 offset 未严格切出 text" % (page, sp["span_id"]))
                break
            pos = sp["end_offset"]
            if i < len(page_spans) - 1:
                if pos >= len(block) or block[pos] != "\n":
                    v3_bad.append("%s span %s 之后不是行分隔符" % (page, sp["span_id"]))
                    break
                pos += 1
        else:
            if pos != len(block):
                v3_bad.append("%s 覆盖未到块尾: %d != %d" % (page, pos, len(block)))
            if "\n".join(sp["text"] for sp in page_spans) != block:
                v3_bad.append("%s lines.join(\"\\n\") != transcript 块" % page)
    if not [s for s in spans if s["page"] == "page_002"]:
        pass
    else:
        v3_bad.append("page_002 不应有 span")
    p2_states = [e.get("terminal_state") for e in (anomalies or {}).get("entries", []) if e.get("page") == "page_002"]
    if p2_states != ["known_unrecognizable"]:
        v3_bad.append("page_002 终态不是 known_unrecognizable")
    if v3_bad:
        fail("coverage", v3_bad[0])
    else:
        emit("PASS", "coverage", "spans=%d" % len(spans))

# ---------------------------------------------------------------- V4 anchors
if spans is not None:
    v4_bad = []
    page_docs = {}
    for page in page_names:
        try:
            page_docs[page] = load_json("pages/%s.json" % page)
        except Exception as exc:  # noqa: BLE001
            v4_bad.append("pages/%s.json 不可读: %s" % (page, exc))
    if not v4_bad:
        for sp in spans:
            doc = page_docs.get(sp["page"])
            if doc is None:
                v4_bad.append("%s 无对应页 JSON" % sp["span_id"])
                break
            anchor = sp["source_anchor"]
            if anchor["image_sha256"] != asset_sha.get(sp["page"]):
                v4_bad.append("%s image_sha256 与 manifest 资产不符" % sp["span_id"])
                break
            line = None
            for ln in doc["lines"]:
                if ln["id"] == anchor["line_id"]:
                    line = ln
                    break
            if line is None:
                v4_bad.append("%s line_id %s 不在页 JSON 中" % (sp["span_id"], anchor["line_id"]))
                break
            if anchor["bbox"] != line["box"]:
                v4_bad.append("%s bbox 与 lines[i].box 不符" % sp["span_id"])
                break
            expect_chars = [c for c in doc["chars"] if c["parent"] == anchor["line_id"]]
            if len(expect_chars) != len(anchor["chars"]):
                v4_bad.append("%s chars 数量 %d != %d" % (sp["span_id"], len(anchor["chars"]), len(expect_chars)))
                break
            for got, want in zip(anchor["chars"], expect_chars):
                if got["char_index"] >= len(doc["chars"]) or doc["chars"][got["char_index"]] is not want:
                    v4_bad.append("%s char_index %s 指向错误字" % (sp["span_id"], got["char_index"]))
                    break
                if got["glyph_id"] != want["id"] or got["char"] != want["char"] or got["box"] != want["box"]:
                    v4_bad.append("%s 字框锚点 %s 与 chars 数组不一致" % (sp["span_id"], got["glyph_id"]))
                    break
            if v4_bad:
                break
    if v4_bad:
        fail("anchors", v4_bad[0])
    else:
        emit("PASS", "anchors", "spans=%d" % len(spans))

# ------------------------------------------------------- V5 expected_schema
v5_bad = []
for stage in ("m1", "m2", "m3"):
    rel = "expected/%s.stage_package.yaml" % stage
    target = os.path.join(FIX, rel)
    if not os.path.exists(target):
        v5_bad.append("%s 缺失" % rel)
        continue
    proc = subprocess.run(
        [CJS, "--schemafile", SCHEMA, target],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        first = proc.stdout.decode("utf-8", "replace").strip().split("\n")[0]
        v5_bad.append("%s: %s" % (rel, first))
if v5_bad:
    fail("expected_schema", "; ".join(v5_bad))
else:
    emit("PASS", "expected_schema", "m1/m2/m3")

# --------------------------------------------------------- V6 expected_hash
v6_bad = []
try:
    page_paths = {}
    for page in page_names:
        page_paths[page] = os.path.join(FIX, "pages/%s.json" % page)
    manifest_txt = os.path.join(FIX, "manifest.yaml")
    spans_txt = os.path.join(FIX, "spans.yaml")
    m1_hash = sha256_file(manifest_txt)
    m2_hash = hashlib.sha256(
        ("\n".join(sha256_file(page_paths[p]) for p in sorted(page_paths)) + "\n").encode("utf-8")
    ).hexdigest()
    m3_hash = sha256_file(spans_txt)

    lines_total = 0
    chars_total = 0
    for page in page_names:
        doc = json.load(open(page_paths[page], encoding="utf-8"))
        lines_total += len(doc["lines"])
        chars_total += len(doc["chars"])

    actual_counts = {
        "m1": {"pages": len(manifest["edition_part"]["pages"]), "source_assets": len(manifest["source_assets"])},
        "m2": {
            "ocr_pages": len(page_names),
            "lines": lines_total,
            "chars": chars_total,
            "anomalies": len((anomalies or {}).get("entries", [])),
        },
        "m3": {"spans": len(spans), "batches": len({s["batch_id"] for s in spans})},
    }
    expected_hashes = {"m1": m1_hash, "m2": m2_hash, "m3": m3_hash}

    for stage in ("m1", "m2", "m3"):
        doc = load_yaml("expected/%s.stage_package.yaml" % stage)
        if doc["manifest"]["content_sha256"] != expected_hashes[stage]:
            v6_bad.append("%s content_sha256 不符" % stage)
        if doc["manifest"]["counts"] != actual_counts[stage]:
            v6_bad.append("%s counts %s != %s" % (stage, doc["manifest"]["counts"], actual_counts[stage]))
        if doc["stage"] != stage:
            v6_bad.append("%s stage 字段为 %s" % (stage, doc["stage"]))
except Exception as exc:  # noqa: BLE001
    v6_bad.append("重算失败: %s" % exc)
if v6_bad:
    fail("expected_hash", "; ".join(v6_bad))
else:
    emit("PASS", "expected_hash", "m1/m2/m3")

# ---------------------------------------------------------------- V7 assets
v7_bad = []
for item in manifest["source_assets"]:
    path = os.path.join(ASSET_ROOT, os.path.basename(item["path_ref"]))
    if not os.path.exists(path):
        print("BLOCKED_SOURCE_ASSET_MISSING %s" % item["path_ref"])
        blocked += 1
        continue
    if sha256_file(path) != item["sha256"]:
        v7_bad.append("%s sha256 不符" % item["path_ref"])
        continue
    size = png_size(path)
    if size is None:
        v7_bad.append("%s 不是可解析 PNG" % item["path_ref"])
        continue
    if size != (item["width"], item["height"]):
        v7_bad.append("%s 尺寸 %s != (%d, %d)" % (item["path_ref"], size, item["width"], item["height"]))
if v7_bad:
    fail("assets", "; ".join(v7_bad))
elif blocked == 0:
    emit("PASS", "assets", "3/3")

# ------------------------------------------------------------- V8 no_images
banned = []
for root, _dirs, files in os.walk(FIX):
    for name in files:
        if os.path.splitext(name)[1].lower() in (".png", ".jpg", ".jpeg", ".pdf"):
            banned.append(os.path.relpath(os.path.join(root, name), FIX))
if banned:
    fail("no_images", "fixture 内含图像文件: %s" % ", ".join(banned[:5]))
else:
    emit("PASS", "no_images", "0")

# ---------------------------------------------------------------- 退出码
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
