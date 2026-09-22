# M4 抽取用片段清单（41 段）重建记录（W8 ACT 19 Q4）

## 1. 缺口

`pipeline/corpus/_fixture/qianyuan_ed01_text/m4/README.md` 记录了 M4 抽取员实际读到的
片段清单 `spans_tianguan_qisha.yaml` 的 sha256：

```
b4240c748ca0cc0883980328d01e4c06effeef7f99bd6924724fea747f9e4cd7
```

但**全盘无此文件**（仓库与 `~/tmux-agents` 均已搜过）。抽取用输入清单丢失意味着：
再想复算两路抽取、或核对「抽取员当时到底看到了哪 41 段」，没有可用的输入物。

> 本件**不声称**该缺口已被「补上原件」——**原件不存在，无法核对**，见 §4。

## 2. 重建来源（两处仍可复现的事实）

| 事实 | 出处 |
|---|---|
| 片段 ID 集合 = 证据引用并集（37）∪ 仅 notes 提及（4）= 41 | 六份已入库提交件 `m4/submission_{assertion,pattern,concept_mention}_{a,b}.yaml` |
| 片段记录（ID / 偏移 / 文本 / 锚点） | 真书账本 `var/ledgers/qianyuan_w8` 的 M3 `corpus_spans` 修订 `rev_a163a3e4162c41b48e6829e676b11b01` |

清单里的片段就是抽取员实际看到的那一批：**被抽中的 + 被点名跳过的**。仅 notes 提及、
未被任何证据引用的 4 段是：

```
ss_qianyuan_ed01_o0008874  ss_qianyuan_ed01_o0009076
ss_qianyuan_ed01_o0009108  ss_qianyuan_ed01_o0009116
```

（分别是「余仿此。」概括语两处、作者按语「此亦得其大概也。」、以及「七煞」标题段——
抽取员在 notes 里逐条说明过为什么跳过，故它们**属于**输入清单。）

## 3. 重建命令与实跑输出

```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export LC_ALL=en_US.UTF-8
python3 pipeline/tools/rebuild_m4_span_list.py            # 落盘
python3 pipeline/tools/rebuild_m4_span_list.py --check-only  # 只核对事实，不落盘
```

实跑输出（逐字）：

```
证据引用片段: 37
仅 notes 提及（未被引用）: 4 -> ['ss_qianyuan_ed01_o0008874', 'ss_qianyuan_ed01_o0009076', 'ss_qianyuan_ed01_o0009108', 'ss_qianyuan_ed01_o0009116']
并集: 41 段
corpus_spans 修订: rev_a163a3e4162c41b48e6829e676b11b01
raw 跨度: [8663, 9397)  字数合计: 734
清洗偏移: 8109..8843 首尾相接
写出: var/ledgers/qianyuan_w8_review/spans_tianguan_qisha.yaml（25705 字节）
sha256: 0ef9f0c082e48c33581473d4466cda59007eb5497f22d00ee5449b60e2af88d7
（README 记录的原文 sha256 b4240c748ca0cc0883980328d01e4c06effeef7f99bd6924724fea747f9e4cd7 无法核对：原文件不存在）
```

核对结果与 ACT 19 Q4 背景给出的四条事实逐条吻合：恰好 **41 段**、清洗偏移**首尾相接
无空洞无重叠**（`8109..8843`，跨度恰 734）、**字数合计 734**、raw 偏移 **`[8663, 9397)`**。

## 4. sha256 状态：**未能核对**（不得声称已核对）

- 仓库记录的原件 sha256：`b4240c748ca0cc0883980328d01e4c06effeef7f99bd6924724fea747f9e4cd7`
- 本重建件 sha256：`0ef9f0c082e48c33581473d4466cda59007eb5497f22d00ee5449b60e2af88d7`

两个值**无从比较**：原件不在盘上。重建件头部注释里也逐字写明了这一点。本重建件的
sha256 只用于此后校验**本文件**未被改动，不代表原件。

## 5. 产物位置与版本库边界

| 路径 | 是否入版本库 | 说明 |
|---|---|---|
| `pipeline/tools/rebuild_m4_span_list.py` | **是**（本件） | 可复算重建脚本；只读账本与提交件 |
| `docs/blackbox-spec-rework/work-items/impl-05-knowledge/M4_SPAN_LIST_REBUILD.md` | **是**（本件） | 本记录 |
| `var/ledgers/qianyuan_w8_review/spans_tianguan_qisha.yaml` | **否** | 生成物，落在运行时账本区；`.gitignore:16` 已排除整个 `var/` |

按主 Agent 2026-09-21 裁决：**`var/` 下一律不入库**（运行时账本区），Q2/Q4 的可交付物
改为「可复算脚本 + 记录文档」。脚本是确定性纯函数（同输入同输出），任何人按 §3 的命令
都能逐字节复算出 `var/` 里的那份生成物。

## 6. 复算时若失败（设计如此）

脚本自带断言：段数不是 41、字数不是 734、raw 跨度不是 `[8663, 9397)`、清洗偏移不连续、
片段 ID 不在账本里、`corpus_spans` 对象字节哈希不符 —— 任一条不成立即打印
`REFUSED …`、退出码 1，且**不写任何文件**（ACT 19 on_fail ③：重建前提错了必须停手上报，
不许产出一份「看起来像」的清单）。
