#!/usr/bin/env bash
# qianyuan_ed01_text fixture 自校验脚本（ACT 16 二；电子文本路线）
#
# 用法：bash verify.sh
# 环境变量：
#   FIXTURE_DIR        待校验的 fixture 根目录（默认本脚本所在目录）
#
# 与 mini_ed01/verify.sh 的差别：**不要求任何页图**（电子文本路线没有 OcrPage /
# source_asset_page 概念，ACT 14 背景实测：真书账本里这两类 artifact 计数均为 0），
# 因此不读 FIXTURE_ASSET_ROOT。校验的是本路线的宿主事实：
#   1) manifest.yaml 声明的每个底本资产的磁盘字节 sha256 与清单一致；
#   2) spans.yaml 顶层 evidence_level 为 offset_level；
#   3) 每条 span 的偏移落在宿主文本范围内、宽度等于文本长度、互不重叠且有序。
#
# 两点口径说明（供复核者）：
#   - span 偏移在**清洗文本**坐标系里（M2 会删字符：实测宿主 17735 字 → 清洗后 17181 字），
#     因此这里只校验「落界 + 宽度 == 文本长度 + 有序不重叠」，**不**用原始文本切片比对
#     span.text（两者本就不相等）；
#   - 宿主文本长度在这里是上界。
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

PY="$REPO_ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "BLOCKED_ENV .venv missing"
  exit 3
fi

export FIXTURE_DIR REPO_ROOT

"$PY" - <<'PY'
import hashlib
import os
import sys

import yaml

FIX = os.environ["FIXTURE_DIR"]

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
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(rel):
    with open(os.path.join(FIX, rel), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


# ---------------------------------------------------------------- 宿主文件齐备
host_missing = [
    rel for rel in ("manifest.yaml", "spans.yaml")
    if not os.path.isfile(os.path.join(FIX, rel))
]
if host_missing:
    emit("BLOCKED_ENV", "host_files", "宿主文件缺失: %s" % ", ".join(host_missing))
    print("FIXTURE BLOCKED: %d" % len(host_missing))
    sys.exit(3)

manifest = load_yaml("manifest.yaml")
spans_doc = load_yaml("spans.yaml")
assets = manifest.get("source_assets") or []

# ------------------------------------------------- V1 底本字节 sha256 与清单一致
asset_files = {}
v1_bad = []
v1_missing = []
for item in assets:
    path = os.path.join(FIX, os.path.basename(item["path_ref"]))
    if not os.path.isfile(path):
        v1_missing.append(item["path_ref"])
        continue
    actual = sha256_file(path)
    if actual != item["sha256"]:
        v1_bad.append(
            "%s sha256 %s != 清单 %s" % (item["path_ref"], actual, item["sha256"])
        )
        continue
    asset_files[item["page"]] = path

if v1_missing:
    for ref in v1_missing:
        emit("BLOCKED_SOURCE_ASSET_MISSING", ref)
    blocked += len(v1_missing)
elif v1_bad:
    fail("source_asset_sha256", "; ".join(v1_bad))
else:
    emit("PASS", "source_asset_sha256", "assets=%d" % len(assets))

# --------------------------------------------------- V2 evidence_level 为 offset
if spans_doc.get("evidence_level") != "offset_level":
    fail("evidence_level", "顶层 evidence_level=%r，期望 offset_level" % (spans_doc.get("evidence_level"),))
else:
    emit("PASS", "evidence_level", "offset_level")

# -------------------------------------------- V3 span 偏移落在宿主文本范围内
spans = spans_doc.get("spans") or []
text = "".join(
    open(path, encoding="utf-8").read() for path in asset_files.values()
) if asset_files else ""

v3_bad = []
if spans_doc.get("span_count") != len(spans):
    v3_bad.append("span_count %r != 实际 %d" % (spans_doc.get("span_count"), len(spans)))
cursor = 0
for span in spans:
    start = span["start_offset"]
    end = span["end_offset"]
    if not (0 <= start <= end <= len(text)):
        v3_bad.append("%s 偏移 [%d,%d) 越出文本范围 0..%d" % (span["span_id"], start, end, len(text)))
        break
    if len(span["text"]) != end - start:
        v3_bad.append("%s 文本长度 %d != 偏移宽度 %d" % (span["span_id"], len(span["text"]), end - start))
        break
    if start < cursor:
        v3_bad.append("%s 与前段重叠/乱序: start=%d < 前段 end=%d" % (span["span_id"], start, cursor))
        break
    cursor = end
if v3_bad:
    fail("span_offsets", v3_bad[0])
else:
    emit("PASS", "span_offsets", "spans=%d text_chars=%d" % (len(spans), len(text)))

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
