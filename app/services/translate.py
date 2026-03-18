"""
文档翻译服务
提供文本和文件的翻译功能,支持断点续传
"""
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.utils.ai_client import OllamaClient
from app.utils.prompts import PromptBuilder
from app.utils.logger import logger


def calculate_chunk_hash(chunk: str) -> str:
    """
    计算文本块的MD5哈希
    
    Args:
        chunk: 文本块内容
        
    Returns:
        MD5哈希值（32位十六进制字符串）
    """
    return hashlib.md5(chunk.encode('utf-8')).hexdigest()


def split_markdown_by_heading(md_text: str, max_chars: int = 1000) -> list:
    """
    按标题分割Markdown文本，并在句末进行分片
    
    Args:
        md_text: Markdown文本内容
        max_chars: 每段最大字符数 (默认1000，比之前更小以适配新的翻译流程)
        
    Returns:
        分割后的文本段列表
    """
    parts = []
    current_chunk = ""
    sections = re.split(r'(?=^#{1,6} )', md_text, flags=re.M)
    
    # 定义句末标记（中英文句号、问号、感叹号、换行等）
    sentence_endings = r'[。！？.!?\n]'
    
    for section in sections:
        if len(current_chunk) + len(section) <= max_chars:
            current_chunk += section
        else:
            # 如果当前chunk不为空，需要检查是否可以在句末分割
            if current_chunk:
                # 尝试将section的一部分加入当前chunk，确保在句末分割
                remaining = max_chars - len(current_chunk)
                if remaining > 100:  # 至少保留100字符的空间
                    # 在section中查找合适的分割点（句末）
                    search_text = section[:remaining + 200]  # 多看一些字符以找到句末
                    matches = list(re.finditer(sentence_endings, search_text))
                    if matches:
                        # 找到最后一个句末位置
                        last_match = matches[-1]
                        split_pos = last_match.end()
                        current_chunk += section[:split_pos]
                        section = section[split_pos:]
                
                parts.append(current_chunk.strip())
                current_chunk = ""
            
            # 如果section本身太长，需要进一步分割
            while len(section) > max_chars:
                # 在max_chars附近找句末
                search_text = section[:max_chars + 200]
                matches = list(re.finditer(sentence_endings, search_text))
                if matches:
                    last_match = matches[-1]
                    split_pos = last_match.end()
                    parts.append(section[:split_pos].strip())
                    section = section[split_pos:]
                else:
                    # 如果找不到句末，直接在max_chars处分割（最后手段）
                    parts.append(section[:max_chars].strip())
                    section = section[max_chars:]
            
            current_chunk = section
    
    if current_chunk:
        parts.append(current_chunk.strip())
    
    return parts


def translate_text(text: str, model: OllamaClient, full_context: str = "") -> str:
    """
    翻译单个文本块 - 新的两步翻译流程
    第一步：理解全文并提供翻译思路
    第二步：翻译后评审并改进
    
    Args:
        text: 待翻译的文本内容
        model: AI 客户端实例
        full_context: 全文内容（用于第一步理解，只在第一次调用时提供）
        
    Returns:
        翻译后的文本
    """
    try:
        # 步骤1：如果提供了全文内容，先让AI理解并提供翻译思路
        translation_strategy = ""
        if full_context:
            logger.info("🔍 步骤1：AI 正在阅读全文并制定翻译策略...")
            strategy_messages = PromptBuilder.build_strategy_messages(full_context)
            translation_strategy = model.respond_chat(strategy_messages)
            logger.info("✅ 翻译策略制定完成")
            logger.info("✅ 翻译策略:",translation_strategy)

        # 步骤2：执行翻译
        logger.info("✍️ 正在翻译...")
        messages = PromptBuilder.build_translate_messages(text, translation_strategy)
        initial_translation = model.respond_chat(messages)
        
        # 步骤3：评审并改进翻译
        logger.info("🔍 正在评审翻译质量...")
        review_messages = PromptBuilder.build_review_messages(text, initial_translation)
        review_result = model.respond_chat(review_messages)
        
        # 步骤4：根据评审意见进行二次修正
        logger.info("🔧 根据评审意见进行二次修正...")
        refine_messages = PromptBuilder.build_refine_messages(text, initial_translation, review_result)
        final_translation = model.respond_chat(refine_messages)
        logger.info("✅ 翻译完成")
        
        return final_translation
    
    except Exception as e:
        logger.error(f"翻译模型调用异常: {e}")
        return ""


def translate_file(
    md_path: Path,
    md_zh_path: Path,
    model: OllamaClient,
    task_id: Optional[int] = None,
    db_session: Optional[Session] = None,
    max_chars: int = 1000,
    progress_callback=None,
    should_stop_callback=None
) -> bool:
    """
    翻译 Markdown 文件,支持断点续传
    翻译进度记录在数据库中
    使用新的两步翻译流程：先理解全文并制定策略，然后翻译并评审改进
    
    Args:
        md_path: 输入Markdown文件路径
        md_zh_path: 输出翻译文件路径
        model: AI客户端实例
        task_id: 任务ID（用于数据库存储进度）
        db_session: 数据库会话（可选）
        max_chars: 每段最大字符数（默认1000，因为需要同时传原文和译文）
        progress_callback: 进度回调函数，签名为 callback(current, total, percentage)
        should_stop_callback: 停止检查回调函数，返回True表示应该停止
        
    Returns:
        翻译是否成功
    """
    try:
        # 读取原文
        with open(md_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        chunks = split_markdown_by_heading(md_text, max_chars=max_chars)
        translated_chunks = []
        translated_count = 0
        
        # 保存全文内容，用于第一次翻译时制定策略
        full_context = md_text
        
        # 如果提供了 task_id 和 db_session，从数据库加载进度
        if task_id and db_session:
            from app.models.task import TranslateProgress
            
            # 查询已完成的翻译块
            progress_records = db_session.query(TranslateProgress).filter(
                TranslateProgress.task_id == task_id
            ).order_by(TranslateProgress.chunk_index).all()
            
            # 构建已翻译的内容映射
            progress_map = {p.chunk_index: p for p in progress_records}
            
            # 验证并加载已翻译的内容
            for i in range(len(chunks)):
                if i in progress_map:
                    progress = progress_map[i]
                    # 验证哈希值以确保内容一致
                    chunk_hash = calculate_chunk_hash(chunks[i])
                    if progress.chunk_hash == chunk_hash:
                        translated_chunks.append(progress.translated_content)
                        translated_count = i + 1
                    else:
                        # 如果哈希不匹配，说明源文件已更改，需要重新翻译
                        logger.warning(f"⚠️ 第 {i + 1} 段内容已更改，将重新翻译")
                        break
                else:
                    # 遇到未翻译的块，停止加载
                    break
            
            if translated_count > 0:
                logger.info(f"🔄 从数据库恢复进度：已完成 {translated_count}/{len(chunks)} 段")
        
        # 确保输出目录存在
        md_zh_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 开始翻译
        for i in range(translated_count, len(chunks)):
            # 检查是否应该停止
            if should_stop_callback and should_stop_callback():
                logger.info("检测到停止请求，终止翻译")
                return False
            
            chunk = chunks[i]
            logger.info(f"📝 正在翻译第 {i + 1}/{len(chunks)} 段...")
            
            # 只在第一段时传入全文context用于理解和制定策略
            context = full_context if i == translated_count else ""
            translated = translate_text(chunk, model, context)
            translated_chunks.append(translated)
            
            # 每完成一段立即写入文件
            with open(md_zh_path, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(translated_chunks))
            
            # 如果提供了 task_id 和 db_session，保存进度到数据库
            if task_id and db_session:
                from app.models.task import TranslateProgress
                
                # 计算分块哈希
                chunk_hash = calculate_chunk_hash(chunk)
                
                # 检查是否已存在该记录
                existing_progress = db_session.query(TranslateProgress).filter(
                    TranslateProgress.task_id == task_id,
                    TranslateProgress.chunk_index == i
                ).first()
                
                if existing_progress:
                    # 更新现有记录
                    existing_progress.chunk_hash = chunk_hash
                    existing_progress.translated_content = translated
                else:
                    # 创建新记录
                    progress = TranslateProgress(
                        task_id=task_id,
                        chunk_index=i,
                        chunk_hash=chunk_hash,
                        translated_content=translated
                    )
                    db_session.add(progress)
                
                db_session.commit()
            
            # 调用进度回调
            if progress_callback:
                current = i + 1
                total = len(chunks)
                percentage = int((current / total) * 100)
                progress_callback(current, total, percentage)
        
        logger.info(f"\n✅ 翻译完成,已保存到：{md_zh_path}")
        return True
    
    except Exception as e:
        logger.error(f"翻译文件失败: {e}")
        if db_session:
            db_session.rollback()
        return False

