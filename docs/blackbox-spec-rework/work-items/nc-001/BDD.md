# NC-001-01 可观察行为

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 当前计划新建客户端、父目录存在、建包归 NC-004 | 校验 local | 通过且只报告 LOCAL_PREPARATION_PASS，不报告运行就绪 |
| B02 | 同一快照含空设备/账号、未跑测试 | 校验 integrated | 非零并逐项列出缺证，不跳过 |
| B03 | 删除client、sdk、dependencies、repositories任一必填字段 | 校验 | 非零、字段路径明确、无成功标志 |
| B04 | PLANNED_NEW缺创建责任或父目录不存在 | 校验local | 拒绝，不创建目录 |
| B05 | 将client改为EXISTING但无pubspec/lib，或Flutter版本证据不存在 | 校验local | 拒绝存在性冒充，不修改外部文件 |
| B06 | 只将NOT_RUN改为PASSED而无command/exit_code/count/evidence | 校验integrated | 拒绝伪造通过 |
| B07 | 将私密笔记配置为新随机身份体系，或启用本轮书籍工作 | 校验local | 拒绝与批准边界不符 |
| B08 | 提供错误JSON或未知profile | 执行校验 | 退出2，给输入错误，不输出Traceback或成功 |
| B09 | 使用测试临时目录构造完整联调证据结构 | 校验integrated | 结构可通过，但只报告结构校验，不声明真实云已验收 |
| B10 | 校验结束 | 比较输入/外部目录 | 内容与目录均未被更改 |
| B11 | 注销来源未验证且所有字段完整登记为 null | 校验 local / integrated | local 可过；integrated 拒绝 integration.account_deletion.status，不阻断其他模块的本地文稿准备 |
| B12 | 注销状态 VERIFIED 但缺来源、送达语义或执行证据 | 校验 integrated | 指出缺字段，不承认仅改状态的通过 |
| B13 | 注销事件填写 sign_out 或未知送达语义 | 校验 | 拒绝将退出登录冒充删除账号 |
