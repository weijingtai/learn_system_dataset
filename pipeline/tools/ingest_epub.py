#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_epub.py —— EPUB 入库转换（OPERATOR_MANUAL 第 5A 章 EPUB 路线的确定性实现）

用法：
    python3 tools/ingest_epub.py <epub路径> <corpus输出目录>

行为：
1. 解包 EPUB，按 spine 顺序抽取正文 XHTML；
2. 去标签、还原实体；h1–h4 标题保留为 Markdown 标题并作为"伪页"边界——
   电子书无页码，用章节序号充当 span 编号里的 p 值：第 n 个标题节 = <!-- p000n -->；
3. 输出 source/transcript_v1.md；同时输出 sections.yaml（伪页号 → 标题路径 对照表）；
4. 只做结构转换，不改一个字；转换器自身的 sha256 记入 manifest 由调用方完成。

确定性：同一 EPUB 输入永远产出相同输出（无时间戳、无随机性）。
"""

import html
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container",
      "opf": "http://www.idpf.org/2007/opf"}


def spine_files(z):
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = container.find(".//c:rootfile", NS).get("full-path")
    opf_dir = str(Path(opf_path).parent)
    opf = ET.fromstring(z.read(opf_path))
    manifest = {i.get("id"): i.get("href")
                for i in opf.find("opf:manifest", NS)}
    order = []
    for ref in opf.find("opf:spine", NS):
        href = manifest.get(ref.get("idref"))
        if href and href.endswith((".xhtml", ".html", ".htm")):
            order.append(f"{opf_dir}/{href}" if opf_dir != "." else href)
    return order

HEAD_RE = re.compile(r"<h([1-4])[^>]*>(.*?)</h\1>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
SKIP_FILES = re.compile(r"(nav|toc|title|about|cover|copyright)", re.I)


def clean(fragment):
    text = TAG_RE.sub("", fragment)
    text = html.unescape(text)
    return re.sub(r"[ \t　]+", "", text)  # 去空格但保留换行结构


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    epub, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    src_dir = out_dir / "source"
    src_dir.mkdir(parents=True, exist_ok=True)

    z = zipfile.ZipFile(epub)
    lines, sections, page = [], [], 0
    path_stack = {}

    for f in spine_files(z):
        if SKIP_FILES.search(Path(f).name):
            continue
        content = z.read(f).decode("utf-8")
        # 按标题切块：交替得到 [前导文本, (级别,标题), 文本, ...]
        pos = 0
        for m in HEAD_RE.finditer(content):
            body = clean(content[pos:m.start()])
            if body.strip():
                lines.append(body.strip("\n"))
            level = int(m.group(1))
            title = clean(m.group(2)).strip()
            if title:
                page += 1
                path_stack[level] = title
                for deeper in [k for k in path_stack if k > level]:
                    del path_stack[deeper]
                full_path = " / ".join(path_stack[k] for k in sorted(path_stack))
                sections.append({"page": page, "level": level,
                                 "title": title, "path": full_path})
                lines.append(f"\n<!-- p{page:04d} -->")
                lines.append("#" * level + " " + title)
            pos = m.end()
        tail = clean(content[pos:])
        if tail.strip():
            lines.append(tail.strip("\n"))

    text = "\n".join(lines).strip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    (src_dir / "transcript_v1.md").write_text(text, encoding="utf-8")
    yaml.dump({"sections": sections},
              open(src_dir / "sections.yaml", "w"), allow_unicode=True, sort_keys=False)
    body_chars = len(re.sub(r"<!--.*?-->|\s|#", "", text))
    print(f"完成：{page} 个标题节（伪页），正文约 {body_chars} 字")
    print(f"输出：{src_dir}/transcript_v1.md ＋ sections.yaml")


if __name__ == "__main__":
    main()
