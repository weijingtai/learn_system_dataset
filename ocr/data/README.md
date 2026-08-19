# data/ — gujiorc 数据文件

| 文件/目录 | 作用 | 说明 |
|---|---|---|
| `common_hanzi.txt` | 生僻字判定用「常用字表」 | 生产建议放入《通用规范汉字表》(8105字)。若缺省，代码内置小型常用字集 + 术数白名单兜底保证可运行。格式：连续排列或一字一行均可（程序按字符读入集合） |
| `unihan/` | Unihan 离线字库（读音/部首/笔画/释义） | 可选。放入 `unihan.json`（key=码点如 "4E16" 或字，value=字段 dict。字段样例 `kMandarin`/`kRSUnicode`/`kTotalStrokes`/`kDefinition`）。缺省则生僻字查询/拆解退化为只读码点 |

## 如何获取《通用规范汉字表》

- 教育部 2013 发布，8105 字。网上有公开文本。
- 下载为纯文本、连续排列的 `common_hanzi.txt` 放本目录即可，程序用 `detector.build_common_set()` 加载。

## 如何获取 Unihan

- Unicode Consortium 官方发布，含 `Unihan_Readings.txt`、`Unihan_IRGSources.txt`、`Unihan_RadicalStrokeCounts.txt` 等。
- 可用 Python 库 `unicodedata`（内置，字段少）替代大部分查询。
- 精简版 `unihan.json` 可从社区项目下载，或自行聚合 txt 字段转 json。