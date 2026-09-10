# ACT 01 BDD 场景

## B1 目标文件缺失时自动播种

Given 用户的应用文档目录下不存在 `ge_ju_database.sqlite`，
When 工作台启动并初始化数据库，
Then 数据库文件被正确创建，并从 asset 中播种预置数据。

## B2 目标文件已存在时不被覆盖

Given 用户的应用文档目录下已存在 `ge_ju_database.sqlite`，且本地包含一条新增或修改过的格局记录，
When 工作台重启并重新初始化数据库，
Then 本地的新增或修改数据完整保留，数据库文件未被 asset 覆盖。

## B3 历史审核与失败记录不被冲掉

Given 本地记录了人工审核决定或历史失败记录（满足 §20 第 2、3 条），
When 工作台重启后，
Then 历史审核记录与失败记录原样存在，不发生静默清除。

## B4 单机无第三方服务依赖

Given 本地单机环境，
When 运行持久化检测逻辑，
Then 仅使用标准库 `dart:io` 与已有 `drift`、`path_provider`，不引入额外 pub 依赖。
