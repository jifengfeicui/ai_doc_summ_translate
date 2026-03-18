"""
API依赖注入
提供常用的依赖项
"""
from app.core.database import get_db
from app.core.config import AI_API_URL, AI_MODEL_NAME
from app.utils.ai_client import OllamaClient


def get_ai_model() -> OllamaClient:
    """获取AI模型实例"""
    return OllamaClient(AI_API_URL, AI_MODEL_NAME)


__all__ = ["get_db", "get_ai_model"]

