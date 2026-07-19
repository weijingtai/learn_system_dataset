#!/usr/bin/env python3
"""
================================================================================
入库脚本：raw_books 原始文件 → pipeline/corpus/ 版本化目录
================================================================================

## 背景

本脚本是整个术数文献知识编译流水线的第一步——"入库"（ingestion）。

在流水线中有两种文件：
  raw_books/  —— 用户提供的原始电子本，是"未登记的外部材料"，不受流水线保护
  corpus/     —— 版本化语料库，是"已登记的原始凭证"，一旦入库就只读、不可修改

把 raw_books 里的文件"入库"，意味着：
  1. 建立确定性的文件快照（sha256 哈希），此后任何人改动都能被检测到
  2. 生成统一的逐字转录（transcript_v1.md），加页标记，一字不改
  3. 记录完整的来源元信息（manifest.yaml）：底本性质、版权状态、版本说明

为什么要这样设计？
  - AI agent 做后续切分/标注时，必须从 corpus/ 里复制粘贴原文，不能凭记忆手打
  - 校验程序会对比 sha256，保证 agent 没有悄悄改原文或简繁转换
  - 同一个作品可能有多个版本（ed01/ed02），各自独立登记，互不混淆

## 作用

本脚本一次性完成流水线步骤 1—3：

  步骤 1：原样复制 raw 文件
    raw_books/xxx.md → pipeline/corpus/<术数>/<作品>_ed<NN>/raw/<原文件名>
    使用 Python shutil.copy2，保留原始文件时间戳

  步骤 2：生成逐字转录 transcript_v1.md
    pipeline/corpus/<术数>/<作品>_ed<NN>/source/transcript_v1.md
    内容 = <!-- p0001 --> + 原文全文（逐字一致，含空行）
    如果原书有页码就逐个标 p0002、p0003...；只有一个 raw 文件就整篇一个 p0001

  步骤 3：生成来源清单 manifest.yaml
    pipeline/corpus/<术数>/<作品>_ed<NN>/manifest.yaml
    登记 source_id、作品名、术数类别、版权状态、版本说明、各文件的 sha256
    source_id 自动从目录名推断（yanbo_ed02 → src_yanbo_ed02）

## 目录结构

执行后的 corpus 目录结构：

  pipeline/corpus/<术数>/<作品>_ed<NN>/
  ├── manifest.yaml          # 来源清单：source_id、sha256、版本说明
  ├── raw/
  │   └── <原文件名>          # 原样复制，一字不改
  └── source/
      └── transcript_v1.md   # 逐字转录，开头加 <!-- p0001 -->

## 依赖

  - Python 3.x（已在 pipeline/.venv/ 中预装）
  - pyyaml（已在 pipeline/.venv/ 中预装）
  - 必须用 pipeline/.venv/bin/python3 执行（系统 Python 可能缺少 yaml）

## 用法示例

  # 最简用法（权利状态用默认值 public_domain）
  pipeline/.venv/bin/python3 pipeline/runner/ingest_raw.py \\
      --raw-file raw_books/qimendunjia/yanbodiaosou.md \\
      --corpus-dir qimen/yanbo_ed02 \\
      --work-title "煙波釣叟歌" \\
      --technique-id qimen \\
      --edition-note "用户提供的简体通行电子本，无影像底本，文字未核对，异文按本文件原样记录"

  # 指定权利状态
  ... --rights-status "copyrighted_approved"

  # 强制覆盖已有 corpus 目录
  ... --force

## 注意事项

  1. 目标 corpus 目录已存在时，脚本会拒绝写入并报错，防止误覆盖。
     确认要覆盖时加 --force。
  2. --force 只覆盖 raw/ 和 source/ 下的同名文件并重写 manifest.yaml，
     不会删除原目录中其他已有文件（如后续任务产出的 output/）。
  3. transcript 生成时会自动在原文前加 <!-- p0001 --> 页标记。
     如果原始文件本身已有页标记，请检查是否重复。
  4. 保持原文件名的意义：raw 目录下的文件名沿用原文件名，便于追溯来源。
  5. 本脚本只负责入库，不启动下游任务。入库后需参照 HANDBOOK.md 继续执行后续步骤。

## 在流水线中的位置

  raw_books/（外部材料）
     │
     └── 本脚本（入库）──→ corpus/<术数>/<作品>_ed<NN>/
                              │
                              ├── 步骤 4：建任务包（手动/AI）
                              ├── 步骤 5：语义切分→output/draft_opencode.yaml
                              ├── 步骤 6：归档→python3 runner/run_task.py --model manual
                              └── 步骤 7：校验→python3 validators/check_segments.py
"""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

import yaml

# ---- 路径常量 ----------------------------------------------------------------

RUNNER_DIR = Path(__file__).resolve().parent          # pipeline/runner/
PIPELINE_DIR = RUNNER_DIR.parent                       # pipeline/
REPO_ROOT = PIPELINE_DIR.parent                        # learn_system/
CORPUS_ROOT = PIPELINE_DIR / "corpus"                  # pipeline/corpus/


# ---- 工具函数 ----------------------------------------------------------------

def sha256_hex(filepath: str | Path) -> str:
    """计算文件的 SHA-256 哈希值，返回十六进制小写字符串。

    用于在 manifest.yaml 中登记文件指纹，确保后续校验程序能检测到
    任何人对源文件的改动（即使是 AI agent 的"顺手简化"也会立刻暴露）。

    Args:
        filepath: 要计算的文件的路径

    Returns:
        64 位十六进制 sha256 字符串
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def make_source_id(corpus_dir_name: str) -> str:
    """从 corpus 目录名推断 source_id。

    规则：在目录名前面加 src_ 前缀。
    例如：
      yanbo_ed02    → src_yanbo_ed02
      ditiansui_ed01 → src_ditiansui_ed01

    这个 source_id 是后续所有标注段（ss_xxx_s01）、知识单元（ku_xxx）等
    编号的前缀来源，确保每个版本的出处可追溯。

    Args:
        corpus_dir_name: corpus 目录名的最后一段（不含父路径）

    Returns:
        完整的 source_id 字符串
    """
    return f"src_{corpus_dir_name}"


# ---- 核心逻辑 ----------------------------------------------------------------

def ingest(args: argparse.Namespace) -> None:
    """执行完整的入库流程：复制→转录→清单。

    三步按顺序执行，任一步失败都会中止并报错，不会残留半成品目录
    （目录创建在第一步之前，文件则是在每步中逐个写入）。

    Args:
        args: argparse 解析后的命名空间，包含以下字段：
            raw_file       - 原始文件路径（相对于 repo 根目录）
            corpus_dir     - 目标 corpus 子目录路径（如 qimen/yanbo_ed02）
            work_title     - 作品名（如 煙波釣叟歌）
            technique_id   - 术数类别标识（如 qimen、bazi、liuren）
            edition_note   - 版本说明，描述底本来历与注意事项
            rights_status  - 权利/版权状态，默认 public_domain
            force          - 是否强制覆盖已存在的 corpus 目录
    """
    # ---- 路径解析与校验 ----
    raw_file = (REPO_ROOT / args.raw_file).resolve()
    if not raw_file.is_file():
        raise SystemExit(f"原始文件不存在: {raw_file}")

    corpus_dir = (CORPUS_ROOT / args.corpus_dir).resolve()
    raw_dir = corpus_dir / "raw"
    source_dir = corpus_dir / "source"

    # 防止误覆盖已有版本
    if corpus_dir.exists() and not args.force:
        raise SystemExit(
            f"目标目录已存在: {corpus_dir}\n"
            f"\n"
            f"这通常意味着该版本已经入库过。如果确认要覆盖，请加 --force 参数。\n"
            f"注意：--force 只覆盖 raw/ 和 source/ 下同名文件并重写 manifest.yaml，\n"
            f"不会删除原目录中其他文件（如后续任务产出的 output/ 目录不受影响）。"
        )

    raw_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    # ---- 步骤 1：原样复制 raw 文件 ----
    # 保持原始文件名，这是追溯来源的重要线索。
    # shutil.copy2 保留文件修改时间戳。
    raw_dest = raw_dir / raw_file.name
    shutil.copy2(raw_file, raw_dest)
    print(f"[1/3] raw 文件已复制: {raw_dest}")

    # ---- 步骤 2：生成逐字转录 transcript_v1.md ----
    # 规则（来自 HANDBOOK.md 工位 1）：
    #   - 与 raw 文件逐字一致，不改一字、不简繁转换、不"修正"错字
    #   - 加页标记：有页码信息就逐个标，没有就整篇开头一个 <!-- p0001 -->
    #   - 保留原空行分节
    # 当前实现：因为没有页图信息，全篇一个 p0001 标记。
    with open(raw_file, encoding="utf-8") as f:
        raw_content = f.read()

    transcript_content = f"<!-- p0001 -->\n{raw_content}"
    transcript_path = source_dir / "transcript_v1.md"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_content)
    print(f"[2/3] transcript 已生成: {transcript_path}")

    # ---- 步骤 3：生成来源清单 manifest.yaml ----
    # 格式继承自 corpus/qimen/yanbo/manifest.yaml（项目中第一个参考实现）。
    # 登记两个文件的 sha256，此后任何校验程序都可以验证文件完整性。
    # raw 文件登记为 raw_ebook（电子书原始文件），transcript 登记为 transcript（逐字转录）。
    raw_sha = sha256_hex(raw_dest)
    transcript_sha = sha256_hex(transcript_path)

    corpus_dir_name = Path(args.corpus_dir).name
    source_id = make_source_id(corpus_dir_name)

    # 使用相对于 corpus 目录的路径（不是绝对路径），便于项目迁移
    raw_rel = str(raw_dest.relative_to(corpus_dir))
    transcript_rel = str(transcript_path.relative_to(corpus_dir))

    manifest = {
        "source_id": source_id,
        "work_title": args.work_title,
        "edition_note": args.edition_note,
        "technique_id": args.technique_id,
        "rights_status": args.rights_status,
        "files": [
            {"path": raw_rel, "role": "raw_ebook", "sha256": raw_sha},
            {"path": transcript_rel, "role": "transcript", "sha256": transcript_sha},
        ],
    }

    manifest_path = corpus_dir / "manifest.yaml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, allow_unicode=True, sort_keys=False)
    print(f"[3/3] manifest 已生成: {manifest_path}")

    # ---- 完成摘要 ----
    print(f"\n{'=' * 60}")
    print(f"入库完成")
    print(f"{'=' * 60}")
    print(f"  source_id:   {source_id}")
    print(f"  raw:         {raw_rel}")
    print(f"    sha256:    {raw_sha}")
    print(f"  transcript:  {transcript_rel}")
    print(f"    sha256:    {transcript_sha}")
    print(f"{'=' * 60}")
    print(f"\n后续步骤（参照 HANDBOOK.md 和 PLAN.md）：")
    print(f"  4. 建任务包 → pipeline/TASKS/task_xxx_seg/")
    print(f"  5. 语义切分 → output/draft_opencode.yaml")
    print(f"  6. 归档    → python3 runner/run_task.py ... --model manual")
    print(f"  7. 校验    → python3 validators/check_segments.py ... --type A")


# ---- 命令行入口 --------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "入库脚本：把 raw_books/ 下的原始文本文件登记到 "
            "pipeline/corpus/ 版本化语料库\n"
            "流水线步骤 1—3：复制 raw 文件 → 生成逐字转录 transcript_v1.md → 生成来源清单 manifest.yaml"
        ),
        epilog=(
            "示例:\n"
            "  # 烟波钓叟歌 ed02 入库\n"
            "  pipeline/.venv/bin/python3 pipeline/runner/ingest_raw.py \\\n"
            "      --raw-file raw_books/qimendunjia/yanbodiaosou.md \\\n"
            "      --corpus-dir qimen/yanbo_ed02 \\\n"
            "      --work-title \"煙波釣叟歌\" \\\n"
            "      --technique-id qimen \\\n"
            "      --edition-note \"用户提供的简体通行电子本，无影像底本，文字未核对\"\n"
            "\n"
            "  # 强制覆盖已存在的版本\n"
            "  pipeline/.venv/bin/python3 pipeline/runner/ingest_raw.py \\\n"
            "      --raw-file ... --corpus-dir ... --work-title ... \\\n"
            "      --technique-id ... --edition-note ... --force\n"
            "\n"
            "相关文档:\n"
            "  pipeline/HANDBOOK.md       — 各工位完整操作手册\n"
            "  pipeline/AGENT_GUIDE.md    — AI agent 六条铁律与标准工作循环\n"
            "  pipeline/README.md         — 项目总览与文件约定\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--raw-file",
        required=True,
        help=(
            "原始文件路径，从 repo 根目录开始的相对路径。\n"
            "例如: raw_books/qimendunjia/yanbodiaosou.md\n"
            "该文件不会被修改，只做原样复制。"
        ),
    )
    parser.add_argument(
        "--corpus-dir",
        required=True,
        help=(
            "目标 corpus 子目录路径，相对于 pipeline/corpus/。\n"
            "命名约定: <术数类别>/<作品短名>_ed<两位版本号>\n"
            "例如: qimen/yanbo_ed02\n"
            "       bazi/ditiansui_ed01\n"
            "该目录会自动创建，已存在时默认拒绝写入（保护已有版本）。"
        ),
    )
    parser.add_argument(
        "--work-title",
        required=True,
        help=(
            "作品完整名称，使用繁体中文原文。\n"
            "例如: 煙波釣叟歌、滴天髓、淵海子平\n"
            "这个名字会写入 manifest.yaml 的 work_title 字段。"
        ),
    )
    parser.add_argument(
        "--technique-id",
        required=True,
        help=(
            "术数类别标识，使用英文小写短名。\n"
            "当前支持的类别: qimen（奇门）、bazi（八字）、liuren（六壬）、ziwei（紫微）\n"
            "如需新增类别，需先在 pipeline/registry/techniques/ 下登记。"
        ),
    )
    parser.add_argument(
        "--edition-note",
        required=True,
        help=(
            "版本说明，描述底本来历、核对状态、注意事项。必填字段。\n"
            "此说明会写入 manifest.yaml，是后续所有 AI agent 了解底本可靠性的\n"
            "唯一来源。推荐包含以下信息：\n"
            "  - 底本来历（用户提供/扫描版/外部转录）\n"
            "  - 文字状态（已核对/未核对/有异文）\n"
            "  - 有无对应影像底本\n"
            "例如: \"用户提供的简体通行电子本，无影像底本，文字未核对，异文按本文件原样记录\""
        ),
    )
    parser.add_argument(
        "--rights-status",
        default="public_domain",
        help=(
            "著作权/版权状态，默认 public_domain（公有领域）。\n"
            "可选值: public_domain（公有领域）| copyrighted_approved（已获授权）|\n"
            "        unknown（待确认）| copyrighted_fair_use（合理使用）\n"
            "默认不写时使用 public_domain。"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "强制写入已存在的 corpus 目录。\n"
            "注意：只覆盖 raw/ 和 source/ 下同名文件并重写 manifest.yaml，\n"
            "不会删除原目录中其他文件（如后续任务产出的 output/ 不受影响）。"
        ),
    )

    args = parser.parse_args()

    try:
        ingest(args)
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
