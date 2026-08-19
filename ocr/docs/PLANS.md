# PLANS：古籍 OCR 识别与人工校对工作台 — 实施计划

> 版本：v0.1（草案）
> 日期：2026-08-04
> 上游：ocr/docs/PRD.md（需求基线）
> 状态：技术选型已定，待评审开工

---

## 1. 已定技术选型（冻结）

| 环节 | 选型 | 状态 | 理由 |
|---|---|---|---|
| 云端识别引擎 | **PaddleOCR（PP-OCRv6, lang=ch）**，运行于 **Colab** | ✅ 已定 | 2026-08-04 实测：竖排正文置信度 0.9+，质量远超 Apple Vision；Colab 免费 GPU 可跑 |
| 云端运行环境 | Google Colab（免费 GPU T4） | ✅ 已定 | 全部识别工作在 Colab 完成，本地不跑识别模型 |
| Colab 远程监控 | **Google Drive 总线 + progress.json 心跳**（主）；cloudflared 隧道实时面板（可选） | ✅ 已定 | 见 §2.4；免费、断点续传、分钟级延迟可接受 |
| 结果数据格式 | 每页一个 JSON（底图 + 逐字框 + 字 + 置信度 + 方向角） | ✅ 已定 | 见 PRD §4.1 |
| 数据存储 | **双轨：JSON 主存储（每页一文件，git 可 diff）+ SQLite 派生索引（检索/统计，FTS5）** | ✅ 已定 | 见 §4.2；JSON 保 git 可回滚，SQLite 供跨页查询 |
| 方向检测 | 旋转候选 + 识别置信度择优（OCR 自验证，不引入额外模型） | ✅ 已定 | 零额外依赖；斜向字多来自星盘图曲线排布，逐字旋转后对比置信度 |
| 单字切分 | 列内投影法二次切分（竖排按行投影）为主，det 单字框为辅 | ⚠️ 待验证 | M2 实验确认 |
| 本地工作台形态 | **Python + FastAPI + 浏览器 Web UI**（本机 localhost） | ✅ 已定 | 手动框选/旋转/编辑需要鼠标交互，TUI 无法胜任；Web UI 复用 macOS 自带浏览器 |
| 本地绘图 | Pillow（PIL） | ✅ 已定 | 已实测：中文标签用 STHeiti 字体渲染正常 |
| 生僻字查询 | macOS Dictionary.app（CJK）+ Unihan 离线库 | ✅ 已定 | 全离线，无需网络 |
| 生僻字拆解 | Unihan kRSUnicode（部首）+ GlyphWiki 字形分解（离线） | ✅ 已定 | 可拆部首/部件 |
| 数据持久化 | JSON 文件 + git 版本管理（复用 learn_system 仓库） | ✅ 已定 | 与仓库 AGENTS.md 铁律一致 |

---

## 2. 需求拆解（WBS）

### 2.1 用户明确提出的需求（PRD R1-R9）

| 需求 | 子任务 | 交付物 |
|---|---|---|
| R1 云端全量识别 | 1a Colab 环境搭建（装 paddleocr/opencv）<br>1b 输入管线：单图/批量图目录<br>1c 预处理开关（自适应二值化/去栏线，实测非必需，保留） | colab/ocr_pipeline.ipynb |
| R2 逐字框选 | 2a 文本检测（det）→ 行/列框<br>2b 单字切分（投影法/单字框）<br>2c 逐字方向角估计 | chars[].box（单字粒度，含 angle） |
| R3 数据留存 | 3a JSON schema 落地<br>3b 底图复制到 output/ 目录 | page_*.json + 底图 |
| R4 原图复原 | 4a 叠加绘制：底图 + 框 + 字（可开关）<br>4b 导出复原预览图 | 本地 Web UI 视图 / overlay.png |
| R5 方向调正 | 5a 框上旋转操作（滑块/输入角度/拖动）<br>5b 旋转预览 + 保存 angle | Web UI 交互 |
| R6 漏选补标 | 6a 画布上手动画框<br>6b 标注 status=unrecognized，可补录文字 | JSON 回写 |
| R7 错误改正 | 7a 点击框编辑文字<br>7b 状态流转 pending→corrected→verified | JSON 回写 |
| R8 生僻字查询 | 8a 调用 macOS Dictionary<br>8b 调用 Unihan 离线数据 | Web UI 面板 |
| R9 生僻字拆解 | 9a Unihan kRSUnicode 部首提取<br>9b GlyphWiki 字形分解（离线库下载+解析） | Web UI 面板 |

### 2.2 用户未明确提到、但必须存在的功能（F 系列）

| 编号 | 功能 | 为什么必须有 | 解决方案 |
|---|---|---|---|
| F1 | **批量页面管理** | 一本书几十上百页，逐页手开 JSON 不现实 | Web UI 页面列表 + 上/下页导航 + 批处理状态面板 |
| F2 | **低置信度优先队列** | 置信度 <0.6 的字几乎必然错，人工应优先校对它们 | 按 conf 排序筛选，标红显示低置信度框 |
| F3 | **校对进度追踪** | 否则无法知道校对到哪、还剩多少 | 每页统计 verified/corrected/unrecognized 计数 + 总进度条 |
| F4 | **撤销/重做** | 手动编辑难免误操作，不可回退会毁数据 | 本地内存操作栈（JSON 快照 + git 提交点） |
| F5 | **自动保存 + git 提交点** | 防丢失；仓库铁律要求每完成子任务提交 | 每次编辑后 debounce 写盘；每页完成时提示 commit |
| F6 | **双页对照（原文 vs 复原）** | 校对必须看到底图原字，光看框内字无法判断 | Web UI 双栏/悬浮放大：框选字时同步显示原图局部裁剪放大 |
| F7 | **图像局部放大镜** | 古籍小字放大后才能看清笔画判断对错 | 鼠标悬浮放大 / 点击放大镜模式 |
| F8 | **数据导出格式** | 校对成果要能被下游（知识编译、检索）消费 | 导出 JSON / 纯文本（按页按列序）/ TSV（字、坐标、置信度） |
| F9 | **异常字符防护** | 识别出乱码（如"务房安房"类）应能快速标记作废而非逐个改 | 批量标记 unrecognized + 低置信度批量操作 |
| F10 | **页序与列序还原** | 竖排古籍阅读顺序（列右→左、列内上→下）必须保留，否则导出文本顺序错 | 结果 JSON 带列分组 + 排序字段；导出按阅读序拼接 |
| F11 | **旋转方向统一约定** | angle 的符号/零点若不统一，跨页复原会乱 | 约定：angle∈[-180,180)，0=正直，逆时针为正，写进 schema 注释 |

### 2.3 信息管理 / 编辑层功能（M 系列，聚焦生僻字能力链）

**范围决策（2026-08-04 用户确认，2026-08-05 更新）：** 运行环境为 **Google Colab**（识别+生僻字圈划+索引全部 Colab 端执行）。只保留生僻字相关功能 + 全字索引。已移除：M6 版本快照（不需要）、M10 备份策略（不需要）、M11 玄学技法分组（不需要）、M12 技法维度统计（不需要，进度汇报保留见 §2.4）。M1 书目元数据简化保留（页↔原图映射），M2 字框 ID 稳定、M3 审计、M9 校验为核心支撑。**M5 全字索引恢复（重要）**——发现某字识别错，可查它在全书所有出现位置。新增生僻字自动圈划（Colab 端）。

| 编号 | 功能 | 为什么重要 | 解决方案/状态 |
|---|---|---|---|
| M1 | **书籍/卷/页元数据** | 没有书目信息，页面 JSON 是一堆孤儿文件 | 顶层 book.json：书名、版本、页映射（page_001 ↔ 原图路径） |
| M2 | **字框 ID 稳定性** | 后续检索/去重要有稳定标识 | chars[].id 规则：`{book}_{page}_{seq}`，永不重用 |
| M3 | **校对历史审计** | 谁改了什么、何时改、改前值是什么——知识工程要可追溯 | 每字操作记录 append 到 audit 数组（时间戳、字段、旧值→新值） |
| M4 | **生僻字自动圈划** ★ | 输入整本书 → 程序自动识别出哪些是生僻字并在原图用红框圈出高亮 | Colab 端：识别全部字 → 用《通用规范汉字表》（或系统字符集）判定不在常用字表的字 → 标记为生僻字 + 在原图叠加红框，输出标记图 + 生僻字清单 JSON |
| M5 | **全字全文索引** ★ | 发现某字识别错，能查出它在全书所有出现位置（不只生僻字） | SQLite FTS5 `index.db`：全部字索引（含 page/id/box/char/status），`SELECT ... WHERE char=:c` 秒返回全部出现位置 |
| M6_ | **未识别字库（自定义字典）** | 生僻字查过一次就应记住，下次直接显示 | 本地 user_dict.json：字 → 读音/释义/部首，查词优先命中再查系统 |
| M7_ | **质量报告** | 校对完要知道整体质量（未识别率、低置信度占比、错误修正数） | 每页/每书汇总统计，导出 report.md |
| M8_ | **异常输入校验** | Colab 输出的 JSON 可能有缺失字段，本地直接读会崩 | 加载时 schema 校验（必填字段、坐标范围、类型），报错定位到文件 |
| M9_ | **Colab 远程监控 + 进度汇报** | 本地要能看到远端识别进度 | 本地监控/日志页读 progress.json；**识别进度按百分比隔段汇报**：每 ≥5% 输出一次"已识别 x%，当前页 Y/total"，或进度条 |
| M10_ | **生僻字截图** | 框选生僻字 → 按 box 坐标从底图裁剪存 PNG，建立字形样本库；同一字多页可存多张样本 | 裁剪图存 `data/glyph_samples/{char_or_id}_{page}_{seq}.png`，与字框 ID 关联 |
| M11_ | **重复字统计表** | 一本书生僻字大量重复，需要知道哪些字重复、重复在哪 | SQLite `GROUP BY char HAVING COUNT(*)>1` 出表：字\|次数\|位置列表（页+框ID+坐标） |
| M12_ | **生僻字分组归并** ★ | 100 个未识别字形，拖拽/点击分组（认为相同则同组）；查到字义/建 TTF 后只改组引用，组内全部自动生效 | `data/glyph_groups.json` 组实体（见 §4.2 详细设计）；展板页 + 组管理列表 |

**依赖链：** M4 判定生僻字（字表反向筛选）→ M10_ 截图（字形样本）→ M12_ 分组归并（展板）；M5 全字索引（检索定位特定字）→ M11_ 重复统计（分布）；M2 字框 ID 稳定服务全文索引与检索。

---

## 2.4 Colab 远程监控方案（详细）

**背景：** 识别在远端 Colab 运行，本地需要知道进度、结果何时可用、是否出错。Colab 免费版限制：会话最长 12h、空闲 90min 断开、重启后环境清空（但 Drive 挂载保留）。

### 方案 A：Google Drive 总线 + progress.json 心跳（主方案，推荐）

```text
[Colab]
  ├─ 挂载 Google Drive (/content/drive/MyDrive/ocr_batch/)
  ├─ 每处理一页:
  │    ├─ 写 page_XXX.png + page_XXX.json 到 Drive
  │    └─ 更新 progress.json:
  │         { batch_id, total, done, current_page, errors[], start_time, last_update, status }
  └─ 全部完成 → progress.json status=done

[本地]
  ├─ Drive 桌面版 / rclone 同步 ocr_batch/ 到本地目录
  ├─ 监控脚本(或 Web UI 监控页) 每 N 分钟读 progress.json
  └─ 显示: 进度条 / 当前页 / 错误列表 / 预计剩余
```

优点：免费、稳定、断点续传（文件落在 Drive 不丢）；Colab 重启后从 progress.json 续跑。
缺点：同步有分钟级延迟，非实时。

### 方案 B：cloudflared 隧道实时面板（可选增强）

```text
[Colab] pip install cloudflared
        → 启动 FastAPI 状态服务(:8080, 读 progress.json)
        → cloudflared tunnel --url http://localhost:8080
        → 得到 https://xxx.trycloudflare.com 公网 URL
[本地] 浏览器直接打开 URL 看实时进度
```

优点：实时刷新。
缺点：免费隧道每次会话重启 URL 变化；Colab 网络策略可能阻止出站隧道（需实测）。

### 决策

- v0.1 实现**方案 A**（可靠优先）；方案 B 作为可选开关，M6 联调时验证可行性。
- progress.json 由 Colab 端每页原子写入（先写临时文件再 rename，避免半写状态）。
- 本地监控并入 Web UI 作为独立页（M8_）。

---

## 3. 数据流总览

```text
[古籍扫描图]
    │
    ▼
[Colab: PaddleOCR 检测 → 单字切分 → 方向估计 → 识别]   ← 全部识别工作在此
    │
    ├─ 底图 (page_XXX.png)
    ├─ 数据 (page_XXX.json: 逐字框/字/conf/angle/status)
    └─ 预览 (page_XXX.overlay.png, 可选)
    │
    ▼ 回传到本地
[本地 Web UI 校对工作台]
    │ 复原显示 → 手动框选补标 → 旋转调正 → 改字 → 生僻字查询/拆解
    ▼
[校对后 JSON + audit 历史]  →  git 提交 → 导出(JSON/TXT/TSV) → 下游知识编译
```

---

## 4. 目录结构（定稿）

```text
ocr/
├── docs/
│   ├── PRD.md            # 需求基线（已提交）
│   └── PLANS.md          # 本文档
├── colab/
│   ├── ocr_pipeline.ipynb
│   ├── requirements.txt  # paddleocr, opencv-python-headless
│   └── output/           # 底图 + JSON + overlay
├── local/
│   ├── app.py            # FastAPI 入口
│   ├── static/           # 前端 (HTML/JS, 单页)
│   ├── schemas.py        # JSON schema 校验
│   ├── dictionary.py     # 生僻字查询/拆解 (Dictionary/Unihan/GlyphWiki)
│   ├── export.py         # JSON/TXT/TSV 导出
│   ├── audit.py          # 审计日志
│   └── user_dict.json    # 自定义字库
├── book.json             # 书目元数据（书→页映射）
└── data/                 # 校对后的页面 JSON（每页一个）
```

### book.json 数据模型（简化版，无技法分组）

```json
{
  "books": [
    {
      "id": "book_qt01",
      "title": "新刻琴堂五星",
      "version": "明万历31年胡文焕刻本（山东省图书馆藏）",
      "pages": ["page_001", "page_002"]
    }
  ],
  "pages": {
    "page_001": {
      "book": "book_qt01",
      "image": "raw_books/.../page_001.png",
      "result": "data/page_001.json"
    }
  }
}
```

> 注：原技法分组（techniques 数组）因 M11 已裁撤而移除；本书版 v0.1 以"书→页"为最小映射，足够生僻字检索/截图/分组归并使用。

---

## 4.2 识别信息数据结构（层级框模型）

**核心：一个字一个框（最细粒度），也可按列/行/词聚合（一句话一框）。不设两套结构，用 level 字段 + 父子层级解决。**（参考 PAGE XML 标准设计）

### 单字框（level=char，最细粒度）

```json
{
  "id": "p001c0001",
  "level": "char",
  "parent": "p001l0003",
  "box": {"x": 531, "y": 140, "w": 36, "h": 151},
  "angle": -12.5,
  "char": "貴",
  "conf": 0.99,
  "source": "ocr",
  "status": "verified",
  "glyph": null
}
```

### 列/行框（level=line，一句话一框）

```json
{
  "id": "p001l0003",
  "level": "line",
  "parent": "p001cl0001",
  "box": {"x": 531, "y": 140, "w": 36, "h": 632},
  "angle": 0,
  "text": "得善星來照視晚招一對定應多孛主女",
  "children": ["p001c0001", "p001c0002", "p001c0003"],
  "conf": 0.97
}
```

### 层级关系

```text
page
 └─ column (列, 可选, 竖排书通常直接是列)
     └─ line (行/句)
         └─ char (字)  ← 最细粒度
```

- 每个子框有 `parent` 指针；每个父框有 `children` 列表
- **粒度切换 = 前端按 level 过滤**：只看 `char` 就是一字一框；折叠到 `line` 就是一句一框；两者并存同一文件
- Colab 端一次产出全部层级（det 得列框 → 切分得字框 → 聚合得行框），本地无需重算

### 生僻字 / 未识别字处理

```json
{
  "id": "p001c0042",
  "level": "char",
  "box": {"x": 900, "y": 300, "w": 40, "h": 40},
  "angle": 0,
  "char": "",                 // 未识别 → 空；识别但生僻 → 存 Unicode 字符
  "conf": 0.31,               // 低置信度
  "source": "ocr",
  "status": "unrecognized",   // 人工确认前标记
  "glyph": null               // 本地拆解后填: {"radical": "艹", "parts": ["十","日","十"], "note": "…"}
}
```

流程：
1. Colab 识别失败/低置信 → `char` 留空或存候选 + `status=pending` + `conf` 低值
2. 本地低置信度队列优先展示（F2）
3. 生僻字查询（Dictionary/Unihan）→ 人工确认 → 回填 `char`，`status=verified`
4. 需要拆解 → 本地拆解填入 `glyph` 字段

### 存储双轨（JSON + SQLite）

| 用途 | 存储 | 说明 |
|---|---|---|
| 主存储 | `data/page_XXX.json`（每页一文件，含全部层级框） | git 可 diff/回滚；符合仓库铁律 |
| 派生索引 | `index.db`（SQLite + FTS5） | 跨页全文检索/统计/进度聚合；可从 JSON 重建，不进 git（.gitignore） |
| 元数据 | `book.json`（书→页映射） | 见 §4.1 |

- 加载：book.json → 定位页 → 读 page JSON（内存建父子索引）
- 写入：编辑后原子写 JSON（tmp+rename）；同步更新 SQLite（可延迟批量）
- 校验：schema 校验 page JSON（必填字段/坐标范围/父子引用完整性）

### 生僻字自动圈划（M4 详细）★核心需求

**目标：** 输入整本书 → 程序自动识别出哪些字是生僻字，并在原图用红框圈出高亮。

**判定"生僻字"方法（反向筛选）：**
1. 建**常用字集合**：加载《通用规范汉字表》(8105 字) 或《现代汉语常用字表》，再加古籍常用虚字/星曜专名白名单（避免"孛/罗/计/炁"这类术数常用字被误判）
2. 对 PaddleOCR 识别出的每个字 `char`：
   - `char` ∈ 常用字集合 → 非生僻
   - `char` ∉ 常用字集合 → 标记为生僻字
   - `char` 为空/低置信（<0.6）→ 标记为"待确认"（结合置信度辅助，避免漏判形变字）
3. 在原图像素坐标叠加红框（PIL/OpenCV 画框），生僻字用红色、待确认用黄色

**输出（每页）：**
- `page_XXX.marked.png`：原图 + 生僻字红框标记图
- `page_XXX.json`：每条生僻字框带 `is_rare: true` + `rare_reason`（"not_in_common_set" / "low_conf"）

**输出（整书汇总）：**
- `rare_characters.json`：生僻字清单 {字, 出现次数, 所有位置[页+框ID+坐标], 备注}
- 供 M10_ 截图（字形样本）、M11_ 重复统计、M12_ 分组归并直接消费

**实现位置：** Colab 端（随识别流水线一起跑，无需本地）。

### 全字全文索引（M5 详细）★核心需求

**目标：** 发现某字识别错，可查它在全书所有出现位置（不只生僻字）。

**实现：** SQLite FTS5 索引 `index.db`，建表：

```sql
CREATE VIRTUAL TABLE char_index USING fts5(
    book, page, char_id, char, status, box  -- 每字一条
);
-- 查询某字全部出现位置
SELECT page, char_id, box FROM char_index
WHERE char = :target_char;
```

- 索引**全部字**（不只生僻字），含任一识别结果 `char` + `status`（pending/verified/corrected/unrecognized）
- 从每页 JSON 重建（可全量重建，M2 字框 ID 保证稳定）
- 用途：发现错字后，一条 SQL 秒返回所有出现位置（页+框ID+坐标），人工决定逐处改还是批量改（配合 M11_ 批量操作）
- `index.db` 不进 git（.gitignore），可从 JSON 随时重建

### 生僻字截图（M10_ 详细）

- 触发：校对时框选一个生僻字 → 点击"截图存档"
- 实现：从底图按 `box` 坐标裁剪（PIL crop，可外扩 2-4px 留边）
- 存储：`data/glyph_samples/{char}_{page}_{seq}.png`；同一字在不同页出现 → 多张样本，文件名的 `{seq}` 递增
- 关联：字框 JSON 增加 `sample_img` 字段指向裁剪图路径；反向索引（按 char 找全部样本）由 SQLite 提供
- 用途：字形样本库——比对异体/俗字在不同页的写法，供拆解与人工判断

### 重复字统计（M11_ 详细）

- 触发：本地 Web UI "重复字"面板（按书筛选）
- SQL：`SELECT char, COUNT(*) cnt, GROUP_CONCAT(page||':'||id) positions FROM chars WHERE status!='unrecognized' GROUP BY char HAVING cnt>1 ORDER BY cnt DESC`
- 展示表格：字 | 次数 | 位置列表（页+框ID+坐标）
- 交互：点击某行 → 跳转到该字任一出现处（复原视图）；可批量标记/批量改字（如某字全页皆同一误识）
- 价值：一本书生僻字大量重复时，一次看清重复分布，决定"逐处校"还是"批量校"

### 生僻字分组归并（M12_ 详细）★核心需求

**问题：** 一本书可能有 100 个未识别生僻字形样本，逐个处理不现实；但其中大量是同一字的重复/变体。人工识别"哪些是同一个字"比"这个字是什么"容易得多。

**功能：**
1. **字形展板页**：展示该书全部未识别生僻字的字形样本（M10_ 截图，网格/瀑布流排列）
2. **拖拽/点击分组**：把"我认为是同一个字"的样本拖入同一组；每组可自定义组名（如"生僻字A"）；同一样本只能在一个组
3. **组级统一定义**：某天查到字义 / 创建 TTF 字体 → 只需修改**组的代表引用**（char + 字体名）→ 组内所有字框自动更新为该字，无需逐个改

**数据结构（组是独立实体）：**

```json
// data/glyph_groups.json
{
  "groups": [
    {
      "id": "grp_A",
      "name": "生僻字A",
      "char": null,               // 未定义前为空；定义后填目标字
      "font": null,               // 找到 TTF 后填字体名
      "note": "疑似'孛'的异体，待查",
      "samples": ["p001c0042", "p012c0108", "p033c0205"],  // 组内字形样本（字框ID）
      "created": "2026-08-04",
      "updated": null
    }
  ]
}
```

- 字框本身保持 `status=unrecognized`、`char=""` 不变（**原始识别结果永不销毁**）
- 组定义后：展示/导出时按组映射（`char ← groups[].char`），底层数据仍可回退
- 导出文本时：组内所有字框输出组的 char；未入组的未识别字输出占位符（如 □）
- Web UI：展板页（分组操作） + 组管理列表（改引用/改字体/备注）
- 批量操作：组可整体标记为"已处理"；某组定义错误可整体撤销（样本退回未分组池）

**价值：** 100 个生僻字 → 人工只需分组 + 每组定义一次 → 全书自动生效。工作量从"逐个处理 100 字"降为"分组几十组 + 定义几十次"。

### 4.3 区块切分方法（定稿：基于 OCR 框 y 间隙）

**问题：** 古籍页常有上下多个独立段落（目录页两段、正文页上中下三栏、星盘图上下分区）。旧方法用**图像像素空白带**（行密度 < 阈值）切区块——实测不可靠：顶部留白/底部留白被误判为区块边界（编号错位），栏线/印章/噪点干扰检测，图.PNG 星盘图甚至检测不到空白带（整页图形密集）。

**定稿方法（2026-08-04 实测，三图全通过）：**

```
1. PaddleOCR 识别出全部文本框（rec_polys）
2. 按 y_min 排序所有框
3. 计算相邻框间隙 gap = 当前框.y_min - 前框.y_max
4. gap >= 阈值(40px) → 切分点，区块号+1
5. 区块内：按 x 聚列（col_gap_thresh=30）→ 列右→左 → 列内 y 上→下
```

**为什么基于 OCR 框而不是图像：**
- 框是识别结果的直接映射，内容块边界 = 框间隙，天然对齐
- 顶部/底部留白没有框 → 不会产生空区块
- 不受栏线/印章/像素噪点影响
- 星盘图等图形密集页也能正确切分（图.PNG 实测 1 切分点 → 2 区块）

**实测对照：**

| 图片 | 图像空白带法 | OCR框间隙法 |
|---|---|---|
| 目录.PNG | 4 块，顶部留白误判，编号错位（无区块1） | 2 块（卷第二/卷第三）✓ |
| 图.PNG（星盘） | 检测不到空白带，整页一块 | 2 块（星曜歌诀/凶格）✓ |
| Snipaste 正文 | 1 块（勉强） | 3 块 ✓ |

**阈值说明：** gap_thresh=40px 为默认；页面字号大时可调大。实现见 colab/ 端 `paddle_ocr_bands.py`（原型 /tmp/paddle_ocr_bands.py）。

---

## 5. 里程碑（细化）

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| M1 | Colab 流水线：整行/整列框 + 识别 + JSON | ✅ 完成（run 命令） | 能对《三辰通载》目录页生成 page_*.json，列序正确 |
| M2 | 单字切分 + 方向估计 | ✅ 完成（projection，细框合并） | chars[].box 为单字粒度，angle 字段有效；星盘图曲线字角度合理（曲线字仍待优化） |
| M3 | 本地 Web UI：加载/复原/导航/放大镜/低置信度筛选 | ✅ 完成（FastAPI+前端查看+编辑） | 打开一页 → 看到底图 + 全部字框 + 字标签；生僻字/低置信标色 |
| M4 | 编辑能力：手动框选补标/改字/旋转调正/撤销 | ✅ 完成（Web端 fix/segment-new/rotate + CLI fix/show，orig_char全保留） | JSON 回写正确；原始识别 orig_char 永不覆盖 |
| M5 | 生僻字自动圈划 + 全字全文索引 + 生僻字查询/拆解 | ✅ 完成（rare/query/dict） | 输入书 → 自动红框圈出生僻字；发现错字一条 SQL 查全位置；框选生僻字出读音/释义/部首 |
| M6 | 元数据 + 审计 + 进度汇报 + 质量报告 + 导出 + 远程监控 | ✅ 完成（report/进度实做；审计=orig_char+mapping；远程监控=progress.json） | book.json 管理全书；质量报告 report.md 生成；Colab 识别进度按 ≥5% 间隔汇报 |
| M7 | 端到端：选一本古籍全流程跑通 | ✅ 完成 | 琴堂五星 3 页全流程：识别→单字切分→生僻圈划→索引→检索→改字→质量报告 |

---

## 6. 与 pipeline/ 知识编译的衔接（本任务完成后的接入）

**背景：** learn_system 已有完整的知识编译管线（`pipeline/`，AGENT_GUIDE.md 定六条铁律），它把 `corpus/` 的转录文本切分为知识单元（units/），由 Claude Code / OpenCode 执行、校验器强制把关。**当前缺口在 corpus/（转录文本）依赖人工手打/模型转录**——本 OCR 系统正是这个缺口的上游。

**接入目标：** OCR 识别+校对完成后，导出产物直接进入 pipeline/ 的 corpus/，形成完整链路：

```text
raw_books/ 原书扫描（只读）
   ↓  [本系统] Colab 识别 → 本地校对 → 导出
corpus/{technique}/{book}_edNN/source/transcript_v1.md   ← OCR 产物落位
   ↓  [pipeline] Claude Code/OpenCode 切分任务 (TASKS/)
units/ 知识单元（unit.yaml + provenance.yaml + assertions.yaml）
   ↓  校验器 validators/validate.py（TXT_001 强制引用与原文一致）
knowledge_system/ 产品母稿与决策登记
```

### 6.1 导出格式对齐（本系统必须遵守）

参照 `corpus/qimen/yanbo_ed02/` 实测样例：

1. **transcript_v1.md 格式**：每页以 `<!-- p0001 -->` 注释标记起始，后跟正文文本；文本按古籍阅读序（列右→左、列内上→下）排列；**繁体保持原字形，禁止转简体**（铁律 3：差一字校验 TXT_001 即失败）
2. **manifest.yaml**：必填 `source_id`（`src_{book}_{edNN}`）、`work_title`、`technique_id`、`edition_note`、`rights_status`，`files[].sha256` 记录转录文件哈希（SRC_003 校验用）
3. **目录落位**：`corpus/{technique}/{book}_{edNN}/source/transcript_v1.md` + `manifest.yaml`（+ 可选 `raw/` 原始扫描）
4. **未识别字处理**：导出时按 M12_ 分组映射；未入组未识别字用占位符 □，并在 manifest 的 `edition_note` 中注明"该底本存在 N 个未识别字形待人工补录"——**不得伪造字符**（铁律 4：原文没说的一个字都不许添）

### 6.2 本系统导出模块的职责（新增任务，并入里程碑）

- 导出模块生成：transcript_v1.md（按阅读序）+ manifest.yaml（含 sha256）
- 导出前校验：对照 pipeline 校验器规则自检（页标记完整、无简繁转换、未识别占位已标注）
- 导出位置可配置：默认 `../pipeline/corpus/{technique}/{book}_edNN/`

**里程碑并入：** M7 端到端验收增加一项——导出的 transcript_v1.md 能被 `pipeline/validators/validate.py` 接受（或至少通过 TXT_001 类引用一致性自检）。

---

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 单字切分对曲线文字失败 | R2 核心目标不达标 | M2 先实验；备选：曲线弧段参数化切分（沿圆弧投影） |
| Colab 会话断线/超时 | 批量识别中断 | 分页批处理 + 已生成 JSON 即时下载；Colab 挂 Drive 存中间结果 |
| Web UI 开发成本超预期 | 拖延 M3-M4 | 先用最小可行（单页 JS + 原生 canvas），不做框架 |
| Unihan/GlyphWiki 数据获取受限 | R8/R9 延期 | 备选：macOS Dictionary 足以查音义；拆解可降级为部首搜索 |
| 古籍版权 | 扫描图不能外传 | 全部本地/Colab 私有运行，不上传公开仓库（.gitignore 排除 data/ 与 output/） |

---

## 7. 待办（下一步）

- [ ] M1：编写 colab/ocr_pipeline.ipynb（基于 /tmp/paddle_ocr.py 实测脚本）
- [ ] M2：单字切分 + 方向估计实验（用《图.PNG》星盘图验证曲线文字）
- [ ] M3：本地 Web UI 骨架
- [ ] 将本 PLANS.md 提交 git

---

## 8. 参考资料

- PRD.md（需求基线）
- /tmp/paddle_ocr.py（PaddleOCR 3.x 竖排识别 + 区块分割 + 排序，已实测）
- /tmp/ocr_box_mark.py（画框标记，PIL + STHeiti 中文标签，已实测）
- 2026-08-04 会话实测结论（Vision 失败 / PaddleOCR 正文 0.9+ / 曲线文字乱码）
