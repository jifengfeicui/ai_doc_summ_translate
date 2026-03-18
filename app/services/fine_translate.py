"""
精翻服务模块
实现多步骤的精细化翻译流程：
1. AI 阅读全文并理解文章内容
2. 针对目标读者群体提供翻译思路
3. 基于讨论结果进行全文翻译
4. （可选）对翻译结果打分并提供改进意见
5. （可选）基于改进意见进行二次修正
"""
import json
import os
import re
from pathlib import Path
from typing import Optional, Callable, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.utils.ai_client import OllamaClient
from app.utils.logger import logger


class FineTranslatePrompts:
    """精翻提示词配置"""
    
    @staticmethod
    def get_comprehension_prompt(content: str) -> dict:
        """步骤1: 请 AI 阅读并理解文章"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": """你是一位资深的文本分析专家，擅长快速理解和评价各类文章。
请仔细阅读文章并给出你的专业认知和评价。"""
                },
                {
                    "role": "user",
                    "content": f"""请阅读下面这篇文章并提供你的认知和评价：

---
{content}
---

请从以下几个方面进行分析：
1. **文章类型**：这是什么类型的文章（学术论文、技术文档、科普文章、叙事散文等）
2. **核心主题**：文章的中心思想是什么
3. **写作风格**：作者的写作特点（专业严谨、通俗易懂、幽默风趣等）
4. **目标受众**：原文面向的读者群体
5. **关键特征**：文章中的专业术语、数据、引用等重要元素
6. **整体评价**：你对这篇文章的总体印象和质量评估

请详细阐述你的分析。"""
                }
            ]
        }
    
    @staticmethod
    def get_strategy_prompt(content: str, target_audience: str, comprehension: str) -> dict:
        """步骤2: 请 AI 提供翻译策略"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": """你是一位经验丰富的翻译专家，精通中英文翻译理论和实践。
你擅长根据不同的文本类型和目标读者制定最佳的翻译策略。"""
                },
                {
                    "role": "user",
                    "content": f"""基于你对这篇文章的理解：

{comprehension}

---

我现在要把它翻译成中文，目标读者群体是：{target_audience}

请提供详细的翻译策略和操作思路，包括：

1. **翻译风格定位**：应该采用什么样的翻译风格才能最适合目标读者
2. **术语处理策略**：专业术语应该如何处理（直接保留、音译、意译、加注释等）
3. **句式调整建议**：是否需要调整句式结构以符合中文表达习惯
4. **文化适配方案**：是否需要对某些文化背景内容进行本地化处理
5. **难点预判**：翻译中可能遇到的难点和建议的处理方式
6. **质量标准**：如何评判翻译质量是否达到最佳效果

请给出你认为最好的翻译方案。"""
                }
            ]
        }
    
    @staticmethod
    def get_translation_prompt(content: str, comprehension: str, strategy: str) -> dict:
        """步骤3: 基于理解和策略进行翻译"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"""你是一位专业的翻译专家，精通中英文互译。

你已经理解了这篇文章的内容和特点：
{comprehension}

你已经制定了翻译策略：
{strategy}

现在请严格按照这些理解和策略进行高质量翻译。"""
                },
                {
                    "role": "user",
                    "content": f"""请将以下内容翻译成中文：

---
{content}
---

翻译要求：
1. 严格遵循之前制定的翻译策略
2. 保持原文的 Markdown 格式和结构
3. 确保翻译准确、流畅、符合中文表达习惯
4. 注意专业术语的一致性
5. 保持原文的语气和风格

请直接输出翻译结果，不要添加任何解释或说明。"""
                }
            ]
        }
    
    @staticmethod
    def get_review_prompt(original: str, translation: str, target_audience: str) -> dict:
        """步骤4: 评审翻译质量并提供改进意见"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": """你是一位严谨的翻译评审专家，擅长评估翻译质量并提供建设性的改进意见。"""
                },
                {
                    "role": "user",
                    "content": f"""请评审以下翻译质量：

【原文】
{original}

【译文】
{translation}

【目标读者】
{target_audience}

请从以下维度进行打分和评价：

## 1. 评分（每项满分10分）
- **准确性**（X/10）：译文是否准确传达原文含义，有无误译、漏译
- **流畅性**（X/10）：译文是否符合中文表达习惯，读起来是否自然
- **专业性**（X/10）：专业术语处理是否恰当，行业规范是否准确
- **适配性**（X/10）：是否符合目标读者的阅读习惯和理解水平
- **格式规范**（X/10）：Markdown 格式、标点符号等是否符合规范
- **总体质量**（X/10）：综合评价

## 2. 具体问题指出
请列出发现的具体问题，每个问题包括：
- 位置：第X段/第X句
- 原文片段：...
- 当前译文：...
- 问题描述：...
- 改进建议：...

## 3. 改进重点
总结最需要改进的3-5个方面

## 4. 总体评语
给出100-200字的总体评价和建议

请详细、客观地进行评审。"""
                }
            ]
        }
    
    @staticmethod
    def get_refinement_prompt(original: str, translation: str, review: str, strategy: str) -> dict:
        """步骤5: 基于评审意见进行二次修正"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"""你是一位专业的翻译专家，现在需要根据评审意见对译文进行精细化修正。

原定翻译策略：
{strategy}

评审意见：
{review}

请认真对待每一条改进意见，对译文进行细致的修正。"""
                },
                {
                    "role": "user",
                    "content": f"""请基于评审意见改进以下翻译：

【原文】
{original}

【当前译文】
{translation}

改进要求：
1. 逐条落实评审意见中指出的问题
2. 保持整体翻译策略的一致性
3. 确保改进后的译文更加准确、流畅、专业
4. 保持 Markdown 格式完整
5. 对于有争议的地方，选择最适合目标读者的方案

请直接输出改进后的译文，不要添加任何解释或说明。"""
                }
            ]
        }


def split_markdown_by_heading(md_text: str, max_chars: int = 3000) -> List[str]:
    """
    按标题分割 Markdown 文本
    
    Args:
        md_text: Markdown 文本内容
        max_chars: 每段最大字符数
        
    Returns:
        分割后的文本段列表
    """
    parts = []
    current_chunk = ""
    sections = re.split(r'(?=^#{1,6} )', md_text, flags=re.M)
    
    for section in sections:
        if len(current_chunk) + len(section) <= max_chars:
            current_chunk += section
        else:
            if current_chunk:
                parts.append(current_chunk.strip())
            current_chunk = section
    
    if current_chunk:
        parts.append(current_chunk.strip())
    
    return parts


class FineTranslator:
    """精翻译器 - 实现多步骤精翻流程"""
    
    def __init__(self, model: OllamaClient, target_audience: str = "有一定科学素养，对科技感兴趣的读者群体"):
        """
        初始化精翻译器
        
        Args:
            model: AI 客户端实例
            target_audience: 目标读者群体描述
        """
        self.model = model
        self.target_audience = target_audience
        self.comprehension = ""
        self.strategy = ""
    
    def step1_comprehend(self, content: str) -> str:
        """
        步骤1: 理解文章内容
        
        Args:
            content: 文章内容
            
        Returns:
            AI 对文章的理解和评价
        """
        logger.info("📖 步骤 1/5: AI 正在阅读并理解文章...")
        messages = FineTranslatePrompts.get_comprehension_prompt(content)
        self.comprehension = self.model.respond_chat(messages)
        logger.info("✅ 完成文章理解")
        return self.comprehension
    
    def step2_plan_strategy(self, content: str) -> str:
        """
        步骤2: 制定翻译策略
        
        Args:
            content: 文章内容
            
        Returns:
            翻译策略和操作思路
        """
        logger.info("🎯 步骤 2/5: AI 正在制定翻译策略...")
        messages = FineTranslatePrompts.get_strategy_prompt(
            content, 
            self.target_audience, 
            self.comprehension
        )
        self.strategy = self.model.respond_chat(messages)
        logger.info("✅ 完成策略制定")
        return self.strategy
    
    def step3_translate(self, content: str) -> str:
        """
        步骤3: 执行翻译
        
        Args:
            content: 待翻译内容
            
        Returns:
            翻译结果
        """
        logger.info("✍️ 步骤 3/5: AI 正在进行翻译...")
        messages = FineTranslatePrompts.get_translation_prompt(
            content,
            self.comprehension,
            self.strategy
        )
        translation = self.model.respond_chat(messages)
        logger.info("✅ 完成翻译")
        return translation
    
    def step4_review(self, original: str, translation: str) -> str:
        """
        步骤4: 评审翻译质量（可选）
        
        Args:
            original: 原文
            translation: 译文
            
        Returns:
            评审意见
        """
        logger.info("🔍 步骤 4/5: AI 正在评审翻译质量...")
        messages = FineTranslatePrompts.get_review_prompt(
            original,
            translation,
            self.target_audience
        )
        review = self.model.respond_chat(messages)
        logger.info("✅ 完成质量评审")
        return review
    
    def step5_refine(self, original: str, translation: str, review: str) -> str:
        """
        步骤5: 基于评审进行改进（可选）
        
        Args:
            original: 原文
            translation: 当前译文
            review: 评审意见
            
        Returns:
            改进后的译文
        """
        logger.info("🔧 步骤 5/5: AI 正在改进翻译...")
        messages = FineTranslatePrompts.get_refinement_prompt(
            original,
            translation,
            review,
            self.strategy
        )
        refined = self.model.respond_chat(messages)
        logger.info("✅ 完成翻译改进")
        return refined
    
    def translate_chunk(self, chunk: str, enable_review: bool = False, 
                       enable_refinement: bool = False) -> Dict[str, str]:
        """
        翻译单个文本块（完整流程）
        
        Args:
            chunk: 待翻译的文本块
            enable_review: 是否启用评审步骤
            enable_refinement: 是否启用改进步骤（需要先启用 review）
            
        Returns:
            包含所有步骤结果的字典
        """
        result = {
            "original": chunk,
            "comprehension": "",
            "strategy": "",
            "translation": "",
            "review": "",
            "refined_translation": ""
        }
        
        # 步骤 1 & 2: 理解和策略（只在第一次执行）
        if not self.comprehension:
            result["comprehension"] = self.step1_comprehend(chunk)
        if not self.strategy:
            result["strategy"] = self.step2_plan_strategy(chunk)
        
        # 步骤 3: 翻译
        result["translation"] = self.step3_translate(chunk)
        
        # 步骤 4 & 5: 可选的评审和改进
        if enable_review:
            result["review"] = self.step4_review(chunk, result["translation"])
            
            if enable_refinement:
                result["refined_translation"] = self.step5_refine(
                    chunk, 
                    result["translation"], 
                    result["review"]
                )
        
        return result


def fine_translate_file(
    md_path: Path,
    md_zh_path: Path,
    model: OllamaClient,
    task_id: Optional[int] = None,
    db_session: Optional['Session'] = None,
    target_audience: str = "有一定科学素养，对科技感兴趣的读者群体",
    max_chars: int = 2000,
    enable_review: bool = False,
    enable_refinement: bool = False,
    max_iterations: int = 1,
    progress_callback: Optional[Callable] = None,
    should_stop_callback: Optional[Callable] = None
) -> bool:
    """
    精翻 Markdown 文件，支持断点续传
    翻译进度记录在数据库中
    
    Args:
        md_path: 输入 Markdown 文件路径
        md_zh_path: 输出翻译文件路径
        model: AI 客户端实例
        task_id: 任务ID（用于数据库存储进度）
        db_session: 数据库会话（可选）
        target_audience: 目标读者群体描述
        max_chars: 每段最大字符数
        enable_review: 是否启用评审步骤
        enable_refinement: 是否启用改进步骤
        max_iterations: 最大迭代改进次数（当启用 refinement 时）
        progress_callback: 进度回调函数，签名为 callback(current, total, percentage)
        should_stop_callback: 停止检查回调函数，返回True表示应该停止
        
    Returns:
        翻译是否成功
    """
    try:
        analysis_path = md_zh_path.parent / f"{md_zh_path.stem}_analysis.json"
        
        # 读取原文
        with open(md_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        chunks = split_markdown_by_heading(md_text, max_chars=max_chars)
        
        # 创建精翻译器实例
        translator = FineTranslator(model, target_audience)
        
        translated_chunks = []
        analysis_results = []
        translated_count = 0
        
        # 如果提供了 task_id 和 db_session，从数据库加载进度
        if task_id and db_session:
            from app.models.task import TranslateProgress
            from app.services.translate import calculate_chunk_hash
            
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
        
        # 加载已有的分析结果
        if os.path.exists(analysis_path):
            try:
                with open(analysis_path, 'r', encoding='utf-8') as af:
                    analysis_results = json.load(af)
                    # 恢复翻译器的理解和策略
                    if analysis_results and len(analysis_results) > 0:
                        first_result = analysis_results[0]
                        translator.comprehension = first_result.get("comprehension", "")
                        translator.strategy = first_result.get("strategy", "")
            except:
                analysis_results = []
        
        # 确保输出目录存在
        md_zh_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 开始精翻
        for i in range(translated_count, len(chunks)):
            # 检查是否应该停止
            if should_stop_callback and should_stop_callback():
                logger.info("检测到停止请求，终止精翻")
                return False
            
            chunk = chunks[i]
            logger.info(f"\n{'='*60}")
            logger.info(f"📝 正在精翻第 {i + 1}/{len(chunks)} 段...")
            logger.info(f"{'='*60}\n")
            
            # 执行精翻流程
            result = translator.translate_chunk(
                chunk,
                enable_review=enable_review,
                enable_refinement=enable_refinement
            )
            
            # 如果启用了改进且需要多次迭代
            current_translation = result.get("refined_translation") or result["translation"]
            if enable_refinement and max_iterations > 1:
                for iteration in range(1, max_iterations):
                    logger.info(f"🔄 第 {iteration + 1} 轮改进...")
                    review = translator.step4_review(chunk, current_translation)
                    current_translation = translator.step5_refine(chunk, current_translation, review)
                    result["refined_translation"] = current_translation
                    result["review"] = review
            
            # 使用最终的翻译结果
            final_translation = result.get("refined_translation") or result["translation"]
            translated_chunks.append(final_translation)
            
            # 保存分析结果
            analysis_results.append({
                "chunk_index": i,
                "comprehension": result.get("comprehension") or translator.comprehension,
                "strategy": result.get("strategy") or translator.strategy,
                "review": result.get("review", ""),
                "has_refinement": bool(result.get("refined_translation"))
            })
            
            # 每完成一段立即写入文件
            with open(md_zh_path, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(translated_chunks))
            
            # 保存分析结果
            with open(analysis_path, 'w', encoding='utf-8') as af:
                json.dump(analysis_results, af, ensure_ascii=False, indent=2)
            
            # 如果提供了 task_id 和 db_session，保存进度到数据库
            if task_id and db_session:
                from app.models.task import TranslateProgress
                from app.services.translate import calculate_chunk_hash
                
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
                    existing_progress.translated_content = final_translation
                else:
                    # 创建新记录
                    progress = TranslateProgress(
                        task_id=task_id,
                        chunk_index=i,
                        chunk_hash=chunk_hash,
                        translated_content=final_translation
                    )
                    db_session.add(progress)
                
                db_session.commit()
            
            # 调用进度回调
            if progress_callback:
                current = i + 1
                total = len(chunks)
                percentage = int((current / total) * 100)
                progress_callback(current, total, percentage)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 精翻完成！")
        logger.info(f"📄 译文已保存到：{md_zh_path}")
        logger.info(f"📊 分析结果已保存到：{analysis_path}")
        logger.info(f"{'='*60}\n")
        return True
    
    except Exception as e:
        logger.error(f"精翻文件失败: {e}")
        if db_session:
            db_session.rollback()
        import traceback
        logger.error(traceback.format_exc())
        return False

