"""
配置管理模块
提供统一的配置访问接口
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()

# 工作空间目录 - 统一存放所有生成数据
WORKSPACE_DIR = os.path.join(ROOT_DIR, "workspace")

# 默认配置
DEFAULT_CONFIG = {
    # 路径配置 - 统一在workspace目录下
    "INPUT_DIR": os.path.join(WORKSPACE_DIR, "input"),
    "OUTPUT_DIR": os.path.join(WORKSPACE_DIR, "output"),
    "TEMP_DIR": os.path.join(WORKSPACE_DIR, "temp"),
    "UPLOAD_DIR": os.path.join(WORKSPACE_DIR, "uploads"),
    "LOG_DIR": os.path.join(WORKSPACE_DIR, "logs"),
    
    # 数据库配置
    "DATABASE_URL": f"sqlite:///{os.path.join(WORKSPACE_DIR, 'data', 'tasks.db')}",
    
    # AI模型配置
    "AI_API_URL": "http://localhost:11434",
    # "AI_API_URL": "http://192.168.3.115:11434",
    # "AI_MODEL_NAME": "qwen2.5:32b-instruct",
    "AI_MODEL_NAME": "glm-4.7-flash:latest",

    # 应用配置
    "APP_HOST": "0.0.0.0",
    "APP_PORT": 8000,
    "DEBUG": False,
}

# 环境变量配置
ENV_CONFIG: Dict[str, Any] = {}

# 加载环境变量
def _load_env_vars():
    """从环境变量加载配置"""
    global ENV_CONFIG
    
    # 遍历默认配置的键
    for key in DEFAULT_CONFIG.keys():
        # 检查环境变量是否存在
        env_value = os.environ.get(key)
        if env_value:
            ENV_CONFIG[key] = env_value

# 加载.env文件（如果存在）
def _load_env_file():
    """从.env文件加载配置"""
    env_path = os.path.join(ROOT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# 初始化配置
_load_env_file()
_load_env_vars()

# 配置访问函数
def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值
    
    Args:
        key: 配置键名
        default: 默认值（如果未找到配置）
        
    Returns:
        配置值
    """
    # 优先级：环境变量 > 默认配置 > 传入的默认值
    return ENV_CONFIG.get(key, DEFAULT_CONFIG.get(key, default))

# 确保目录存在
def ensure_directories():
    """确保所有必要的目录存在"""
    directories = [
        get_config("INPUT_DIR"),
        get_config("OUTPUT_DIR"),
        get_config("TEMP_DIR"),
        get_config("UPLOAD_DIR"),
        get_config("LOG_DIR"),
        os.path.dirname(get_config("DATABASE_URL").replace("sqlite:///", "")),
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# 导出配置常量（方便导入）
INPUT_DIR = get_config("INPUT_DIR")
OUTPUT_DIR = get_config("OUTPUT_DIR")
TEMP_DIR = get_config("TEMP_DIR")
UPLOAD_DIR = get_config("UPLOAD_DIR")
LOG_DIR = get_config("LOG_DIR")
DATABASE_URL = get_config("DATABASE_URL")
AI_API_URL = get_config("AI_API_URL")
AI_MODEL_NAME = get_config("AI_MODEL_NAME")
APP_HOST = get_config("APP_HOST")
APP_PORT = int(get_config("APP_PORT"))
DEBUG = get_config("DEBUG") in (True, "True", "true", "1", 1)

# 初始化目录
ensure_directories()
