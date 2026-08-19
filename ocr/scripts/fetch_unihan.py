# 下载 Unihan 离线库（生僻字读音/部首/笔画/释义数据）到 data/unihan/
# 执行: PYTHONPATH=src python scripts/fetch_unihan.py [--force]
import os
import sys
import urllib.request
import zipfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from gujiorc.core.paths import get_root  # noqa: E402

URL = "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip"
REQUIRED = ["Unihan_Readings.txt", "Unihan_RadicalStrokeCounts.txt"]


def main() -> int:
    force = "--force" in sys.argv
    dest = Path(get_root()) / "data" / "unihan"
    dest.mkdir(parents=True, exist_ok=True)

    if not force and all((dest / name).exists() for name in REQUIRED):
        print("已存在，跳过")
        return 0

    print(f"下载 {URL} ...")
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(data)
    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not name.startswith("Unihan_") or not name.endswith(".txt"):
                    continue
                target = dest / name
                target.write_bytes(zf.read(info))
                print(f"{target.name}  ({target.stat().st_size // 1024}KB)")
    finally:
        tmp_path.unlink(missing_ok=True)

    missing = [name for name in REQUIRED if not (dest / name).exists()]
    if missing:
        print(f"错误：缺少必需文件 {missing}")
        return 1

    print("提示：Unihan 数据文件体积较大，请勿提交 git（data_work/ 已在 .gitignore）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())