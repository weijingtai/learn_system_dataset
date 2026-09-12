# NC-017 可观察行为

ID 与契约 `private_export.md` §8 一一对应，期望逐字以契约为准。测试一律 `flutter test test/export/export_bundle_test.dart`；仓库用临时目录真实 Drift 文件库；附件经内存 `AttachmentBytesSource` 替身；随机源注入。

| ID | Given | When | Then |
|---|---|---|---|
| E01 | 契约 §7 口令与 16 个 0x01 盐 | `deriveExportKey` | 32 字节等于 K |
| E02 | §7 清单字段 | `digestHex()`、`encode()` | 等于 D 与 §7 头部 536 字节字面量 |
| E03 | §7 记录与第 0 块种子 16 个 0x02 | 拼出完整文件 | 明文 764 B 摘要、nonce、块 792 B 摘要、文件 1344 B 与文件摘要均等于字面量 |
| E04 | E03 的文件 | `decodeExportFile` 用原口令 | 1 笔记 1 修订 0 附件，JSON 深相等 |
| E05 | 含独特标题、正文片段、附件标记字节的笔记 | 写入器导出后读原始字节 | 不含三者 UTF-8 子序列、不含笔记 ID 与 ownerScope |
| E06 | 3 块文件 | 错口令、改 1 字节、交换两块、删末块、追加一块 | 五种都抛 `ExportUndecryptable`，`toString()` 相同，无部分内容 |
| E07 | 合法文件 | 改头部不改 digest、改 memory_kib 并重算 digest、改 magic | 均 `ExportFormatError` |
| E08 | 2 MiB 与 2 MiB+1 字节明文 | 分块加密后解密 | 2 块 / 3 块，往返逐字节相等 |
| E09 | active（3 修订含 restored_from、change_summary、两父）、trashed、purge_pending 三条笔记，pending_op 非 none | 导出并解码 | 2 条笔记；修订 13 字段一致；无 pending_op、owner_scope 键 |
| E10 | debugHook 在 `after_chunk:0` 抛异常 | 导出 | 异常上抛；目标不存在；`.partial` 存在 |
| E11 | debugHook 在 `before_verify` 翻转一个字节 | 导出 | `ExportWriteVerificationFailed`；目标与 `.partial` 均不存在 |
| E12 | 目标已存在 / 空口令 / 附件缺失 / 附件摘要不符 | 导出 | 各自异常；目标不被创建或覆盖；附件两种 `.partial` 已删 |
| E13 | 2 条笔记 | 导出 | 进度 (1,2)、(2,2)；结果 `fileSha256` 等于落盘文件重算值；计数一致 |
| E14 | 以 `café`（预组合）导出 | 用分解形式 `café` 解码 | `ExportUndecryptable`；原口令成功 |
