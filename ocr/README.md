# gujiorc — 古籍 OCR 识别与生僻字校对工作台

> 位置：`learn_system/ocr/`
> 环境：Python 3.11+（本项目 venv 已在 `ocr/.venv/`）
> 数据根：由 `OCR_ROOT` 环境变量决定，默认 `ocr/data_work/`

## 一句话

输入古籍扫描图 → PaddleOCR 识别 → 本地 Web UI 逐字校对（改字/补框/旋转）→ 导出 transcript + manifest 进入 pipeline 知识编译。

## 目录地图

```
ocr/
├── src/gujiorc/
│   ├── core/        # paths/models/storage/export/audit/anomaly/report
│   ├── rare/        # 生僻字判定/字典/分组归并
│   ├── index/       # 全字索引 + 检索 + 重复统计
│   └── ocr/         # PaddleOCR 封装 + 切分 + 方向估计
├── scripts/
│   └── ocr_workbench.py   # 主 CLI（所有命令入口）
├── local/
│   ├── app.py             # FastAPI Web UI 入口（localhost:8000）
│   └── static/            # 前端页面
├── colab/                 # Colab 一键全流程（未冻结）
├── docs/                  # PRD / PLANS / HANDOFF / 任务书
├── experiments/           # spike 原型（星盘曲线字切分等）
└── tests/                 # 37+ 单元测试
```

## 快速开始

```bash
cd ocr && source .venv/bin/activate
export OCR_ROOT=$(pwd)/data_work   # 或设你自己路径
export PYTHONPATH=src
```

### 1) 识别 + 单字切分（Colab/本地通用）

```bash
PYTHONPATH=src python scripts/ocr_workbench.py run --segment <图片或目录>
```

- `--gap` 区块切分阈值（默认 40px）
- `--conf` OCR 置信度阈值（默认 0.6）
- `--report-every N` 每隔 N 秒汇报一次进度
- `--bleed-thresh` **抹除背面透印字**的灰度阈值（默认 110，`0` 关闭）

输出在 `$OCR_ROOT/data/`，每页一个 `page_*.json`。

**背面透印字（bleed-through）**：薄纸影印本背面的字会透到正面，OCR 会一视同仁地
检测+识别它们。后果不只是正文混进背面内容——幽灵笔画和真笔画落进同一个检测框，
**连真字的识别一起被拖垮**（实测「卷第七」被读成「卷第七吧」）。
`run` 默认在识别前把亮于 `--bleed-thresh` 的像素推成纯白，整块抹掉透印。
《三辰通载》前10页实测：幽灵字框 531→0，正常页均置信度 0.69~0.96 → 全部 0.95~0.97。

阈值 110 取自真墨（墨迹灰度 32~88）与透印（116~240）之间的空隙。
**淡印本/褪色本必须调低或用 `0` 关闭**，否则会连正文一起抹掉——每页会打印
「残留真墨 x%」，低于 1% 时告警（正常页实测 5.0%~12.3%）。
Web UI 显示的仍是原图，所以透印肉眼可见但不再被当成内容。

### 2) 生僻字圈划 + 清单

```bash
PYTHONPATH=src python scripts/ocr_workbench.py rare <图片或目录>
```

### 3) 查某字全书位置

```bash
PYTHONPATH=src python scripts/ocr_workbench.py query 孛
```

### 4) 改字（保留 orig_char + mapping）

```bash
PYTHONPATH=src python scripts/ocr_workbench.py fix page_003 all 凡 --from-char 凢
```

改字会自动写入 `logs/audit.jsonl`（审计日志，append-only）。

### 5) 分组归并（生僻字归并）

```bash
# 查看
PYTHONPATH=src python scripts/ocr_workbench.py groups list

# 创建组
PYTHONPATH=src python scripts/ocr_workbench.py groups create --name "组A" --samples p001c01 p001c02

# 向组里加样本
PYTHONPATH=src python scripts/ocr_workbench.py groups add --id grp_001 --samples p002c03

# 定义组里统一显示的字
PYTHONPATH=src python scripts/ocr_workbench.py groups define --id grp_001 --char 龍

# 移除样本
PYTHONPATH=src python scripts/ocr_workbench.py groups remove --id grp_001 --samples p002c03
```

### 6) 导出（JSON/TXT/TSV/transcript + corpus manifest）

```bash
# 常规导出
PYTHONPATH=src python scripts/ocr_workbench.py export --book mybook --formats json,txt,tsv,transcript

# corpus 模式（对接 pipeline）
PYTHONPATH=src python scripts/ocr_workbench.py export --corpus-out /path/to/corpus \
  --work-title "新刻琴堂五星" --technique-id wuxing --edition 1 \
  --edition-note "用户扫描本，已人工校对" --rights-status public_domain
```

corpus 模式下会在目标目录生成：

```
{technique_id}/{book}_edNN/
├── source/
│   └── transcript_v1.md    ← OCR 转录正文（繁体原文，未识别字 □）
└── manifest.yaml           ← source_id / work_title / sha256 / files[...]
```

### 7) 查看异常版面（星盘图/环形图等非横竖排）

星盘、环形图这类**非行列版面**的字沿弧线或放射方向排布，矩形检测框贴合不了，
识别结果基本不可用。`run` 会**自动判定并登记**这类页，交人工处理，不让垃圾识别
静默进入语料。

判定用多信号投票（至少 2 项命中才登记，避免正常页被个别噪声误报）：

| 信号 | 阈值 | 正常竖排页实测 | 盘面页实测(page_010) |
|---|---|---|---|
| `low_conf_lines` 低置信行占比 | >20% | 0~2.0% | 45.4% |
| `many_single_char_boxes` 单字行占比 | >15% | 0~6.1% | 28.6% |
| `mixed_orientation` 横排框占比 | >7% | 0~3.0% | 12.6% |
| `low_mean_conf` 全页均置信 | <0.80 | 0.95~0.97 | 0.63 |

一个字都没识别出的页登记为 `no_text`（可能是空白页，也可能是未处理的纯图页，
需人工确认一眼）。

```bash
# 查看（登记由 run 自动完成）
PYTHONPATH=src python scripts/ocr_workbench.py anomalies
PYTHONPATH=src python scripts/ocr_workbench.py anomalies --page page_010 --last 20

# 也可手工登记
PYTHONPATH=src python -c "
from gujiorc.core.anomaly import register_anomaly
register_anomaly(page='page_003', image='star_chart.png',
                 layout_type='star_chart', det_box_count=206,
                 note='圆弧排布，识别乱序')
"
```

登记文件：`$OCR_ROOT/logs/anomalies.jsonl`（append-only）。判定阈值在
`src/gujiorc/core/anomaly.py` 顶部，Web 端 `GET /api/anomalies`。

### 8) 查看审计日志

```bash
PYTHONPATH=src python scripts/ocr_workbench.py audit
PYTHONPATH=src python scripts/ocr_workbench.py audit --page page_003 --last 20
```

日志文件：`$OCR_ROOT/logs/audit.jsonl`（全量操作链：fix / rotate / segment_new / groups_* / export）。

## Web UI（人工校对）

```bash
cd ocr && source .venv/bin/activate
OCR_ROOT=$(pwd)/data_work PYTHONPATH=src python local/app.py
```

浏览器打开 `http://localhost:8000`

功能：
- 底图 + 字框复原显示
- 点击框改字（保留 orig_char + mapping）
- 手动补框（补标未识别字）
- 旋转预览（调正方向角）
- 生僻字查询 / 拆解
- 低置信度优先列表

## 测试

```bash
cd ocr && source .venv/bin/activate
PYTHONPATH=src pytest tests/ -q       # 40+ passed
```

## 环境变量一览

| 变量 | 默认 | 含义 |
|------|------|------|
| `OCR_ROOT` | `ocr/data_work/` | 数据根目录（JSON / logs / exports 从此下探） |
| `PYTHONPATH=src` | 必须 | 让 `gujiorc` 包可导入 |

## 关键设计（数据铁律）

1. **永不覆盖原始识别**：`orig_char` 只增不改；所有改字写 `char + mapping`
2. **繁体原文 + 未识别占位 □**：导出禁止简繁转换；未识别字一律 □
3. **分层模型**：每层用自己的 model（core=LogicModel, storage=DataModel, UI=UIModel）
4. **git 最小提交**：只提交明确路径，`data_work/` / `.venv/` 在 `.gitignore`

## 已知坑 / 注意事项

- **图画式版面（星盘/环形图）**：当前 PaddleOCR 按横排矩形框识别，弧线排字会「乱序 + 低置信」。遇到这种图请用 `anomalies` 登记，后续接入曲线字切分任务（experiments/curve_segment.py）。
- **PaddleOCR 接口已升至 3.7.0**：新版使用 `predict()` 而非 `ocr()`；项目内已适配。
- **data_work/ 已被 gitignore**：页面 JSON 和模型文件不进版本库，需自行备份。
- **Web UI 改版未完成**：`local/static/index.html` + vendor 重建中，未浏览器验收前勿提交。

## 参考文档

- `docs/PRD.md` — 需求基线
- `docs/PLANS.md` — 实施计划
- `docs/HANDOFF.md` — 交接说明
- `docs/TASKS_ENG_GAPS.md` — 工程缺口任务书（A/B/C/D 四项补齐）