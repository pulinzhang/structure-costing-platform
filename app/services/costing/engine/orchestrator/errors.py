"""引擎 Run 生命周期异常。"""


class RunDeletedError(Exception):
    """Run 已被用户删除，Worker 应安静退出。"""
