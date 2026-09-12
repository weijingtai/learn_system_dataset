"""M5 校验异常类型。

- ``ValidationError``：M5 校验异常基类；
- ``ValidationRefused``：``begin_step_run`` 之前的拒绝（输入不可用、非
  ``succeeded`` 上游包、M5 已封存等），表示「未开始即拒绝」，Ledger 不得
  新增任何写入。
"""


class ValidationError(Exception):
    """M5 校验异常基类（不携带 §8.2 错误码，表外语义）。"""


class ValidationRefused(ValidationError):
    """``begin_step_run`` 之前的拒绝（输入不可用、非 succeeded 上游、重复执行）。"""
