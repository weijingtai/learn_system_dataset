# NC-015 独立验收

当前：NOT_EXECUTED。

1. ACT 审查：未参与编写者做 wjt-react 四查；另按 TASKS 要求做**攻击/故障场景审查**（契约 §3～§6 对：中间人替换会话公钥、重放旧信封、跨账号密文投递、过期授权、吊销后残留会话、中转对象未删、接收端崩溃于 ACK 前、哈希碰撞式篡改），每个场景给出契约中的对应防线或标注缺口。
2. 范围：learn_system 恰 2 个提交，只含 `fixtures/private_sync/` 15 文件与 `tools/` 两文件；契约未改。
3. 重跑 TDD §1 全部命令；`nc015_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时副本）：① 把 `envelope_valid.json` 的 `content_hash` 与 `content_hash_cases.json` 第一个 case 逐字比对；② 在契约副本删掉 `## 6.` 标题、删掉 `D-NC015-04`、插入 `待定`，检查器各自退出 1；③ 样例副本改 `expected` 为 `authorised`（拼写）退出 1；④ `relay_ttl.json` 副本改 299 退出 1；⑤ 删除任一样例文件退出 1。
5. 作弊扫描：自测无 `skip`、永真断言；检查器不含硬编码「通过」分支。
6. 通过后：NC-015 `ACCEPTED`，解锁 NC-016（实现）；NC-017/018 按 v1.6 准备。
