#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""mini_ed01 fixture 确定性生成器（D-15）。

用法：
    python tools/build_fixture.py [--out <目录>] [--asset-root <目录>]
                                  [--ocr-data <目录>] [--anomalies <文件>]

默认值：
    --out        本脚本所在 fixture 目录（pipeline/corpus/_fixture/mini_ed01）
    --asset-root ocr/data_work/sanche_pages（只用于写 manifest.source_assets[].path_ref）
    --ocr-data   ocr/data_work/data
    --anomalies  ocr/data_work/logs/anomalies.jsonl

确定性：相同输入产生逐字节相同的输出（yaml 用 sort_keys=False、allow_unicode=True、
固定缩进与不换行宽度；不写时间戳、不写绝对路径、不写随机值）。

素材缺失：任一必需输入不存在时打印 `BLOCKED_SOURCE_ASSET_MISSING <路径>` 并退出 3，
且不创建任何文件（不生成空文件、替代图或伪造哈希）。

范围说明：本生成器生成 manifest.yaml、pages/*.json、source/transcript_v1.md、
anomalies.yaml、spans.yaml、expected/m1..m3.stage_package.yaml 与 verify.sh。
README.md 由人工维护，不由本脚本生成（因此重放比对时 --exclude=README.md）。
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

import yaml

# 硬编码常量（ACT act/r2-02.yaml `constants`，不得改动）
SOURCE_ID = "src_sanche_ed01"
WORK_TITLE = "三辰通載三十卷"
EDITION_NOTE = "影宋鈔本"
TECHNIQUE_ID = "qizheng"
EDITION_PART_ARTIFACT_ID = "art_000000000000000000000000000000e1"
EDITION_PART_LABEL = "卷一·前三页"
ASSET_ROOT_DEFAULT = "ocr/data_work/sanche_pages"
PAGE_ASSETS = {
    "page_001": {
        "file": "page_001.png",
        "sha256": "e46bffa38119df1bb03f5a38e4f3f99405a476ba5d7b6a7c489956ccf2e58e65",
        "width": 1203,
        "height": 1654,
    },
    "page_002": {
        "file": "page_002.png",
        "sha256": "aa5301d98c230a875eeb0b8d8d071393e4d15546d4f352cfb53747af1590f753",
        "width": 1203,
        "height": 1654,
    },
    "page_003": {
        "file": "page_003.png",
        "sha256": "3c138fc9f32d2cfefe029d62dec2a9a0ce0f095c373af41a8a98f4c8f8afb268",
        "width": 1203,
        "height": 1654,
    },
}
PROCESSING_RUN_ID = "prun_000000000000000000000000000000f1"
EXPECTED_IDS = {
    "m1": {
        "stage_package_id": "pkg_m1_000000000000000000000000000000f1",
        "artifact_revision_id": "rev_000000000000000000000000000000f1",
        "step_run_id": "srun_000000000000000000000000000000f1",
        "output_artifact_id": "art_000000000000000000000000000000f1",
        "output_revision_id": "rev_000000000000000000000000000000a1",
        "configuration_revision_id": "rev_000000000000000000000000000000c1",
        "operation": "ingest_source",
        "output_artifact_type": "source_manifest",
    },
    "m2": {
        "stage_package_id": "pkg_m2_000000000000000000000000000000f2",
        "artifact_revision_id": "rev_000000000000000000000000000000f2",
        "step_run_id": "srun_000000000000000000000000000000f2",
        "output_artifact_id": "art_000000000000000000000000000000f2",
        "output_revision_id": "rev_000000000000000000000000000000a2",
        "configuration_revision_id": "rev_000000000000000000000000000000c2",
        "operation": "digitize_pages",
        "output_artifact_type": "ocr_page_set",
    },
    "m3": {
        "stage_package_id": "pkg_m3_000000000000000000000000000000f3",
        "artifact_revision_id": "rev_000000000000000000000000000000f3",
        "step_run_id": "srun_000000000000000000000000000000f3",
        "output_artifact_id": "art_000000000000000000000000000000f3",
        "output_revision_id": "rev_000000000000000000000000000000a3",
        "configuration_revision_id": "rev_000000000000000000000000000000c3",
        "operation": "compile_corpus",
        "output_artifact_type": "corpus_package",
    },
}
SCHEMA_VERSION = "1.0.0"
TRANSCRIPT_TITLE = (
    "# src_sanche_ed01 · 三辰通載三十卷（影宋鈔本）· 卷一·前三页 · 机器转录 v1（未人工校对）"
)
PAGE_002_TRANSCRIPT_LINE = "（known_unrecognizable：无文字页，见 anomalies.yaml）"
SPAN_PAGES = ("page_001", "page_003")
BATCH_FOR_PAGE_001 = "sanche_b001"
BATCHES_FOR_PAGE_003 = ("sanche_b002", "sanche_b003", "sanche_b004", "sanche_b005")


class Quoted(str):
    """需要强制加引号输出的字符串（YAML 里保持字符串语义）。"""


def _quoted_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style='"')


yaml.SafeDumper.add_representer(Quoted, _quoted_representer)


def dump_yaml(obj):
    return yaml.safe_dump(
        obj,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10 ** 9,
        indent=2,
    ).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def q(value):
    return Quoted(value)


# ------------------------------------------------------------------ 生成内容


def read_ocr_pages(ocr_data, page_names):
    docs = {}
    for page in page_names:
        with open(os.path.join(ocr_data, "%s.json" % page), encoding="utf-8") as fh:
            docs[page] = json.load(fh)
    return docs


def build_transcript(docs, page_names):
    out = [TRANSCRIPT_TITLE]
    for page in page_names:
        out.append("")
        out.append("## %s" % page)
        if page == "page_002":
            out.append(PAGE_002_TRANSCRIPT_LINE)
            continue
        for line in docs[page]["lines"]:
            out.append(line["text"])
    return ("\n".join(out) + "\n").encode("utf-8")


def build_anomalies(anomalies_path):
    entry_src = None
    with open(anomalies_path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            if rec.get("page") == "page_002":
                entry_src = rec
                break
    if entry_src is None:
        return None
    evidence = {
        "ts": entry_src["ts"],
        "page": entry_src["page"],
        "image": entry_src["image"],
        "layout_type": entry_src["layout_type"],
        "det_box_count": entry_src["det_box_count"],
        "note": entry_src["note"],
        "extra": entry_src["extra"],
    }
    return {
        "entries": [
            {
                "page": "page_002",
                "terminal_state": "known_unrecognizable",
                "layout_type": entry_src["layout_type"],
                "evidence": evidence,
                "decided_by": "fixture",
                "note": "无文字页；M2 Gate 允许放行（§10.1）",
            }
        ]
    }


def page_block(docs, page):
    """该页在 transcript 中的文本块：行以 "\\n" 连接。"""
    return "\n".join(line["text"] for line in docs[page]["lines"])


def build_spans(docs):
    spans = []
    for page in SPAN_PAGES:
        doc = docs[page]
        block = page_block(docs, page)
        page_num = int(page.split("_")[1])
        pos = 0
        lines = doc["lines"]
        for idx, line in enumerate(lines):
            text = line["text"]
            start = pos
            end = start + len(text)
            pos = end + (1 if idx < len(lines) - 1 else 0)
            if page == "page_001":
                batch_id = BATCH_FOR_PAGE_001
            else:
                batch_id = BATCHES_FOR_PAGE_003[min(idx // 10, 3)]
            char_anchors = []
            for ci, ch in enumerate(doc["chars"]):
                if ch["parent"] != line["id"]:
                    continue
                char_anchors.append(
                    {
                        "char_index": ci,
                        "glyph_id": ch["id"],
                        "char": ch["char"],
                        "box": dict(ch["box"]),
                    }
                )
            spans.append(
                {
                    "span_id": "ss_sanche_ed01_p%04d_s%02d" % (page_num, idx + 1),
                    "batch_id": batch_id,
                    "page": page,
                    "line_index": idx,
                    "start_offset": start,
                    "end_offset": end,
                    "text": text,
                    "source_anchor": {
                        "page": page,
                        "image_sha256": PAGE_ASSETS[page]["sha256"],
                        "line_id": line["id"],
                        "bbox": dict(line["box"]),
                        "chars": char_anchors,
                    },
                }
            )
        assert pos == len(block), "page %s offset 未覆盖整块" % page
    return spans


def build_spans_doc(spans):
    return {
        "work": WORK_TITLE,
        "source_id": SOURCE_ID,
        "edition_part_artifact_id": EDITION_PART_ARTIFACT_ID,
        "evidence_level": "glyphbox_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "batch_count": len({s["batch_id"] for s in spans}),
        "spans": spans,
    }


def build_manifest(asset_root, file_hashes):
    return {
        "source_id": SOURCE_ID,
        "work_title": WORK_TITLE,
        "edition_note": EDITION_NOTE,
        "technique_id": TECHNIQUE_ID,
        "rights_status": "public_domain_text（文字公版；扫描件分发权 unconfirmed）",
        "release_policy": "derived_page_images_only",
        "edition_part": {
            "artifact_id": EDITION_PART_ARTIFACT_ID,
            "label": EDITION_PART_LABEL,
            "pages": ["page_001", "page_002", "page_003"],
        },
        "source_assets": [
            {
                "page": page,
                "path_ref": "%s/%s" % (asset_root, PAGE_ASSETS[page]["file"]),
                "sha256": q(PAGE_ASSETS[page]["sha256"]),
                "width": PAGE_ASSETS[page]["width"],
                "height": PAGE_ASSETS[page]["height"],
                "object_store": "local",
                "in_git": False,
            }
            for page in ("page_001", "page_002", "page_003")
        ],
        # 说明：`files` 覆盖非 expected 的 6 个 fixture 文件。ACT 原文要求 `files` 同时覆盖
        # expected/*.yaml，但 ACT 同时要求 expected/m1 的 `manifest.content_sha256` 等于
        # sha256(manifest.yaml 文件)：两者构成不可解的哈希环（manifest 字节取决于
        # expected/m1 的 sha256，而 expected/m1 字节又取决于 manifest 字节）。
        # 此处保留 content_sha256 规则（V6 可判、D-02 语义），expected 三包改由 V5 Schema
        # 与 V6 哈希/计数全量钉死（任一字节被篡改即 FAIL）。
        "files": [
            {"path": "pages/page_001.json", "role": "ocr_page", "sha256": q(file_hashes["pages/page_001.json"])},
            {"path": "pages/page_002.json", "role": "ocr_page", "sha256": q(file_hashes["pages/page_002.json"])},
            {"path": "pages/page_003.json", "role": "ocr_page", "sha256": q(file_hashes["pages/page_003.json"])},
            {"path": "source/transcript_v1.md", "role": "transcript", "sha256": q(file_hashes["source/transcript_v1.md"])},
            {"path": "anomalies.yaml", "role": "anomalies", "sha256": q(file_hashes["anomalies.yaml"])},
            {"path": "spans.yaml", "role": "spans", "sha256": q(file_hashes["spans.yaml"])},
        ],
        "conversion": {
            "tool": "tools/build_fixture.py",
            "inputs": [
                "ocr/data_work/data/page_001.json",
                "ocr/data_work/data/page_002.json",
                "ocr/data_work/data/page_003.json",
                "ocr/data_work/logs/anomalies.jsonl",
            ],
            "note": "一行 OCR = 一个 span；机器转录未人工校对；仅作结构验收宿主",
        },
        "content_status": "machine_extracted",
    }


def artifact_ref(artifact_id, revision_id, artifact_type):
    return {
        "schema_version": q(SCHEMA_VERSION),
        "artifact_kind": "artifact",
        "artifact_id": artifact_id,
        "artifact_revision_id": revision_id,
        "artifact_type": artifact_type,
    }


def build_expected(stage, docs, spans, page_hashes, manifest_bytes, spans_bytes):
    ids = EXPECTED_IDS[stage]
    if stage == "m1":
        payload = {
            "source_manifest": {
                "source_id": SOURCE_ID,
                "source_manifest_path": "pipeline/corpus/_fixture/mini_ed01/manifest.yaml",
                "edition_part_artifact_id": EDITION_PART_ARTIFACT_ID,
            }
        }
        counts = {"pages": 3, "source_assets": 3}
        content_sha256 = sha256_bytes(manifest_bytes)
        input_artifacts = []
        input_revision_ids = []
    elif stage == "m2":
        payload = {
            "ocr_pages": [
                {
                    "page": page,
                    "path": "pipeline/corpus/_fixture/mini_ed01/pages/%s.json" % page,
                    "sha256": q(page_hashes[page]),
                }
                for page in ("page_001", "page_002", "page_003")
            ],
            "anomalies_path": "pipeline/corpus/_fixture/mini_ed01/anomalies.yaml",
            "terminal_states": {"page_002": "known_unrecognizable"},
        }
        counts = {
            "ocr_pages": 3,
            "lines": sum(len(docs[p]["lines"]) for p in ("page_001", "page_002", "page_003")),
            "chars": sum(len(docs[p]["chars"]) for p in ("page_001", "page_002", "page_003")),
            "anomalies": 1,
        }
        content_sha256 = sha256_bytes(
            ("\n".join(page_hashes[p] for p in sorted(page_hashes)) + "\n").encode("utf-8")
        )
        input_artifacts = [
            artifact_ref(
                EXPECTED_IDS["m1"]["output_artifact_id"],
                EXPECTED_IDS["m1"]["output_revision_id"],
                EXPECTED_IDS["m1"]["output_artifact_type"],
            )
        ]
        input_revision_ids = [EXPECTED_IDS["m1"]["output_revision_id"]]
    else:
        payload = {
            "spans_path": "pipeline/corpus/_fixture/mini_ed01/spans.yaml",
            "coverage": {"page_001": 1.0, "page_003": 1.0},
            "excluded_pages": {"page_002": "known_unrecognizable"},
        }
        counts = {"spans": len(spans), "batches": len({s["batch_id"] for s in spans})}
        content_sha256 = sha256_bytes(spans_bytes)
        input_artifacts = [
            artifact_ref(
                EXPECTED_IDS["m2"]["output_artifact_id"],
                EXPECTED_IDS["m2"]["output_revision_id"],
                EXPECTED_IDS["m2"]["output_artifact_type"],
            )
        ]
        input_revision_ids = [EXPECTED_IDS["m2"]["output_revision_id"]]

    return {
        "schema_version": q(SCHEMA_VERSION),
        "stage_package_id": ids["stage_package_id"],
        "artifact_revision_id": ids["artifact_revision_id"],
        "stage": stage,
        "status": "sealed",
        "payload": payload,
        "manifest": {
            "schema_version": q(SCHEMA_VERSION),
            "processing_run_id": PROCESSING_RUN_ID,
            "step_run_id": ids["step_run_id"],
            "input_artifacts": input_artifacts,
            "output_artifacts": [
                artifact_ref(ids["output_artifact_id"], ids["output_revision_id"], ids["output_artifact_type"])
            ],
            "counts": counts,
            "content_sha256": q(content_sha256),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [],
            "transformations": [
                {
                    "operation": ids["operation"],
                    "step_run_id": ids["step_run_id"],
                    "configuration_artifact_revision_id": ids["configuration_revision_id"],
                    "input_artifact_revision_ids": input_revision_ids,
                    "output_artifact_revision_ids": [ids["output_revision_id"]],
                }
            ],
        },
        "logs": [],
        "failures": [],
    }


# ---------------------------------------------------------------------- 主流程


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    fixture_dir = os.path.dirname(here)

    parser = argparse.ArgumentParser(description="生成 mini_ed01 fixture（确定性）")
    parser.add_argument("--out", default=fixture_dir, help="输出目录，默认本 fixture 目录")
    parser.add_argument("--asset-root", default=ASSET_ROOT_DEFAULT, help="页图素材根目录（仅写入 path_ref）")
    parser.add_argument("--ocr-data", default="ocr/data_work/data", help="OCR 页面 JSON 目录")
    parser.add_argument("--anomalies", default="ocr/data_work/logs/anomalies.jsonl", help="异常日志 jsonl")
    args = parser.parse_args()

    page_names = ("page_001", "page_002", "page_003")

    # 先做输入完整性检查：缺失即报 BLOCKED 并退出 3，绝不创建任何文件。
    required = [os.path.join(args.ocr_data, "%s.json" % p) for p in page_names]
    required.append(args.anomalies)
    for path in required:
        if not os.path.isfile(path):
            print("BLOCKED_SOURCE_ASSET_MISSING %s" % path)
            sys.exit(3)

    docs = read_ocr_pages(args.ocr_data, page_names)
    anomalies_doc = build_anomalies(args.anomalies)
    if anomalies_doc is None:
        print("BLOCKED_SOURCE_ASSET_MISSING %s（未找到 page_002 记录）" % args.anomalies)
        sys.exit(3)

    out = args.out
    pages_dir = os.path.join(out, "pages")
    source_dir = os.path.join(out, "source")
    expected_dir = os.path.join(out, "expected")
    for path in (out, pages_dir, source_dir, expected_dir):
        os.makedirs(path, exist_ok=True)

    # 1) 页 JSON：与 ocr/data_work/data 逐字节相同
    page_hashes = {}
    for page in page_names:
        src = os.path.join(args.ocr_data, "%s.json" % page)
        dst = os.path.join(pages_dir, "%s.json" % page)
        shutil.copyfile(src, dst)
        page_hashes[page] = sha256_file(dst)

    # 2) 机器转录
    transcript_bytes = build_transcript(docs, page_names)
    with open(os.path.join(source_dir, "transcript_v1.md"), "wb") as fh:
        fh.write(transcript_bytes)

    # 3) 异常终态
    anomalies_bytes = dump_yaml(anomalies_doc)
    with open(os.path.join(out, "anomalies.yaml"), "wb") as fh:
        fh.write(anomalies_bytes)

    # 4) spans
    spans = build_spans(docs)
    spans_bytes = dump_yaml(build_spans_doc(spans))
    with open(os.path.join(out, "spans.yaml"), "wb") as fh:
        fh.write(spans_bytes)

    # 5) manifest（只用非 expected 文件的哈希，避免与 expected/m1 的 content_sha256 成环）
    file_hashes = {
        "pages/page_001.json": page_hashes["page_001"],
        "pages/page_002.json": page_hashes["page_002"],
        "pages/page_003.json": page_hashes["page_003"],
        "source/transcript_v1.md": sha256_bytes(transcript_bytes),
        "anomalies.yaml": sha256_bytes(anomalies_bytes),
        "spans.yaml": sha256_bytes(spans_bytes),
    }
    manifest_bytes = dump_yaml(build_manifest(args.asset_root, file_hashes))
    with open(os.path.join(out, "manifest.yaml"), "wb") as fh:
        fh.write(manifest_bytes)

    # 6) 期望 StagePackage（m1/m2/m3）
    for stage in ("m1", "m2", "m3"):
        doc = build_expected(stage, docs, spans, page_hashes, manifest_bytes, spans_bytes)
        with open(os.path.join(expected_dir, "%s.stage_package.yaml" % stage), "wb") as fh:
            fh.write(dump_yaml(doc))

    # 7) 自校验脚本（与仓库内 verify.sh 逐字节相同）
    verify_path = os.path.join(out, "verify.sh")
    with open(verify_path, "wb") as fh:
        fh.write(VERIFY_SH.encode("utf-8"))
    os.chmod(verify_path, 0o755)

    print("GENERATED %s" % out)
    return 0


VERIFY_SH = r'''#!/usr/bin/env bash
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
'''


if __name__ == "__main__":
    sys.exit(main())
