import os
import sys
import datetime
from loguru import logger as _loguru_logger

# 标志：确保只初始化一次
_initialized = False


def _setup_logger():
    """
    配置日志系统 (使用 loguru)
    内部函数，模块加载时自动调用一次
    """
    global _initialized
    if _initialized:
        return

    # 确保logs目录存在
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # 移除默认的 handler
    _loguru_logger.remove()

    # 定义日志格式
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # 添加控制台 handler
    _loguru_logger.add(sys.stderr, format=log_format, level="INFO", colorize=True)

    # 添加文件 handler
    log_file_path = os.path.join(
        "logs", f'app_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    _loguru_logger.add(
        log_file_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="1 week",
        encoding="utf-8",
    )

    _initialized = True


# 模块加载时自动初始化
_setup_logger()

# 导出配置好的 logger 供其他模块使用
logger = _loguru_logger

__all__ = ["logger"]
