"""
文档总结服务
提供文本和文件的总结功能
"""
from pathlib import Path

from app.utils.ai_client import OllamaClient
from app.utils.prompts import PromptBuilder
from app.utils.logger import logger

# 最大字符长度
MAX_TOTAL = 15_000


def summarize_file(md_path: Path, md_summ_path: Path, model: OllamaClient) -> bool:
    """
    总结Markdown文件
    
    Args:
        md_path: 输入Markdown文件路径
        md_summ_path: 输出总结文件路径
        model: AI客户端实例
        
    Returns:
        总结是否成功
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        result = summarize_text(md_text, model)
        
        if result:
            md_summ_path.parent.mkdir(parents=True, exist_ok=True)
            with open(md_summ_path, 'w', encoding='utf-8') as f:
                f.write(result)
            logger.info(f"总结完成: {md_summ_path}")
            return True
        else:
            logger.error("总结结果为空")
            return False
    
    except Exception as e:
        logger.error(f"总结文件失败: {e}")
        return False


def summarize_text(text: str, model: OllamaClient) -> str:
    """
    总结文本内容
    
    Args:
        text: 待总结的文本内容
        model: AI 客户端实例
        
    Returns:
        总结后的文本
    """
    try:
        if len(text) == 0:
            return ""
        
        # 使用优化的提示词构建器
        messages = PromptBuilder.build_summarize_messages(text, max_length=MAX_TOTAL)
        
        # 调用模型进行总结
        result = model.respond_chat(messages)
        return result
    
    except Exception as e:
        logger.error(f"总结模型调用异常: {e}")
        return ""

