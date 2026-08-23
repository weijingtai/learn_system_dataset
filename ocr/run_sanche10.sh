#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== 1. 清除旧数据 ==="
rm -rf data_work/data data_work/glyph_samples data_work/index.db data_work/logs data_work/rare data_work/book.db data_work/index.db-journal
echo "清除完成"

echo ""
echo "=== 2. 重新识别三辰通载前10页 ==="
mkdir -p data_work/sanche_pages
PDF="$HOME/Downloads/三辰通载三十卷 (宋) 錢如璧 撰 影宋鈔本.PDF"
if [ ! -f "$PDF" ]; then
  echo "错误: PDF 不存在: $PDF"
  exit 1
fi

OCR_ROOT=data_work PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py run data_work/sanche_pages --segment
echo "识别完成"

echo ""
echo "=== 3. 启动 Web UI ==="
pkill -f "python.*local/app.py" 2>/dev/null || true
sleep 1
OCR_ROOT=data_work PYTHONPATH=src .venv/bin/python local/app.py &
sleep 2
echo "Web UI 已启动: http://127.0.0.1:8000"
echo "浏览器 Cmd+Shift+R 刷新"