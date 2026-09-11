"""Artifact Ledger（规格 §17）：本地混合存储与单写入者进程。

本包只使用 Python 标准库；子模块：

- ``ids``    标识生成与校验（规格 §8.1）
- ``states`` Artifact / StepRun 状态机与枚举（规格 §8.2）
- ``errors`` 异常类与 9 个错误码常量
- ``actor``  ActorProvider 与本地实现
"""
