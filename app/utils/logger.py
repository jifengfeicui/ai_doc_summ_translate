"""
日志配置模块
提供统一的日志记录接口
"""
import logging
import sys
from pathlib import Path

from app.core.config import LOG_DIR

# 确保日志目录存在
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# 创建 Logger 对象
logger = logging.getLogger("summ_translate")
logger.setLevel(logging.DEBUG)

# 创建控制台 Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
console_handler.setFormatter(console_formatter)

# 创建文件 Handler
log_file = Path(LOG_DIR) / "app.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(file_formatter)

# 添加 Handler (避免重复添加)
if not logger.hasHandlers():
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

