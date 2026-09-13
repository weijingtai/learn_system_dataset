"""M4 外部形态 Adapter。

Adapter 只负责把外部形态（任务管线草稿、Contract Registry canon 目录、legacy
工作台库）转成提交件或运行级 ``technique_profile``；其产物必须先登记进 Ledger，
M4 核心只读 Ledger 冻结修订。
"""
