"""
文档翻译服务 - 简单版本备份
这是修改为两步翻译流程之前的原始版本
提供文本和文件的翻译功能,支持断点续传
"""
import hashlib
import re
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.utils.ai_client import OllamaClient
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


def split_markdown_by_heading_simple(md_text: str, max_chars: int = 1500) -> list:
    """
    按标题分割Markdown文本，并在句末进行分片（改进版本）
    
    Args:
        md_text: Markdown文本内容
        max_chars: 每段最大字符数（默认1500，保证语句完整性）
        
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


def build_simple_translate_messages(content: str) -> dict:
    """构建简单翻译的消息（原始版本）"""
    system_prompt = """你是一位精通简体中文的专业翻译专家，擅长将学术论文和技术文档翻译成准确、流畅、易懂的中文。

# 核心能力
- 准确传达原文的专业信息和学术背景
- 保持科普风格，通俗易懂但不失严谨
- 精通中英文术语对照和专业表达

# 翻译原则
- 忠实原文：准确传达事实、数据和观点
- 通俗易懂：用简洁明了的中文表达复杂概念
- 保持专业：维护学术严谨性和专业术语的准确性

# 翻译规则

## 格式要求
- 输入和输出均为 Markdown 格式，必须保留原始格式和结构
- 保留标题层级、列表、代码块等所有 Markdown 元素

## 术语处理
- 保留专业英文术语（如 FLAC、JPEG、API 等），并在首次出现时提供中文注释
- 保留公司名称和专有名词（如 Microsoft、Amazon、Red Hat）
- 技术术语在其前后加空格，例如："中 API 文"、"不超过 10 秒"

## 引用处理
- 保留文献引用格式，如 [20]
- 保留图表引用并翻译，如 Figure 1 → 图 1

## 标点符号
- 使用中文标点符号
- 全角括号改为半角括号，左括号前加空格，右括号后加空格
- 示例：错误 "（示例）" → 正确 " (示例) "

## 数字和单位
- 数字使用阿拉伯数字
- 保留原文的度量单位，必要时提供中文说明"""

    user_prompt = f"""请翻译以下 Markdown 内容为中文：

---
{content}
---

请严格遵循上述翻译规则，直接输出翻译结果，无需任何解释或说明。"""

    return {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }


def translate_text_simple(text: str, model: OllamaClient) -> str:
    """
    翻译单个文本块（原始简单版本 - 单步翻译）
    
    Args:
        text: 待翻译的文本内容
        model: AI 客户端实例
        
    Returns:
        翻译后的文本
    """
    try:
        # 使用简单的提示词
        messages = build_simple_translate_messages(text)
        
        # 调用模型进行翻译
        result = model.respond_chat(messages)
        return result
    
    except Exception as e:
        logger.error(f"翻译模型调用异常: {e}")
        return ""


def translate_file_simple(
    md_path: Path,
    md_zh_path: Path,
    model: OllamaClient,
    task_id: Optional[int] = None,
    db_session: Optional[Session] = None,
    max_chars: int = 1500,
    progress_callback=None,
    should_stop_callback=None
) -> bool:
    """
    翻译 Markdown 文件,支持断点续传（原始简单版本 - 单步翻译）
    翻译进度记录在数据库中
    
    Args:
        md_path: 输入Markdown文件路径
        md_zh_path: 输出翻译文件路径
        model: AI客户端实例
        task_id: 任务ID（用于数据库存储进度）
        db_session: 数据库会话（可选）
        max_chars: 每段最大字符数
        progress_callback: 进度回调函数，签名为 callback(current, total, percentage)
        should_stop_callback: 停止检查回调函数，返回True表示应该停止
        
    Returns:
        翻译是否成功
    """
    try:
        # 读取原文
        with open(md_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        chunks = split_markdown_by_heading_simple(md_text, max_chars=max_chars)
        translated_chunks = []
        translated_count = 0
        
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
            
            # 简单翻译（单步）
            translated = translate_text_simple(chunk, model)
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


# 使用说明
"""
这是简单翻译版本（已改进分片逻辑），特点：

1. 单步翻译：直接翻译，不经过理解、评审、改进步骤
2. 中等分片：默认 1500 字符（vs 增强版 1000）
3. 智能分片：按标题分割 + 句末分片（✅ 已改进，与增强版相同）
4. 更快速度：每段只需 1 次 AI 调用（vs 增强版 4 次）
5. 中等质量：没有评审和改进环节，但句子完整性好

版本更新：
- ✅ 已添加句末分片逻辑（避免句子被截断）
- ✅ 支持中英文句末标记识别
- ✅ 智能查找分割点（±200字符范围内）
- ✅ 保持与增强版相同的分片质量

对比增强版本：
- 速度：快 3-4 倍（1次调用 vs 4次调用）
- 质量：中等（无评审改进环节）
- 分片：相同（都在句末分片）
- 适用：快速翻译、预览、草稿

如果需要切换回简单版本：
1. 在 task_processor.py 中导入这个文件
2. 替换 translate_file 为 translate_file_simple

示例代码：
```python
from app.services.translate_simple_backup import translate_file_simple

# 在 _process_translate_task_internal 中
success = translate_file_simple(
    md_path, 
    md_zh_path, 
    model=model,
    task_id=task_id,
    db_session=db,
    max_chars=1500,  # 可调整分片大小
    progress_callback=progress_callback,
    should_stop_callback=should_stop
)
```

推荐使用场景：
✅ 文档预览（快速了解翻译效果）
✅ 草稿翻译（后续人工修改）
✅ 时间紧迫（需要快速产出）
✅ 简单文档（专业术语少）
✅ 资源受限（降低 AI 调用成本）
"""

