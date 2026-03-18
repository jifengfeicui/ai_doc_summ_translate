"""
任务处理器 - 面向对象设计
提供任务队列管理和任务执行功能
"""
import threading
import shutil
import json
from typing import Optional, Callable, Dict, Type
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus, TaskType
from app.services.summarize import summarize_file
from app.services.translate_simple_backup import translate_file_simple as translate_file
from app.services.fine_translate import fine_translate_file
from app.services.pdf_converter import convert_pdf_to_md
from app.core.database import SessionLocal
from app.core.config import OUTPUT_DIR
from app.api.dependencies import get_ai_model
from app.utils.logger import logger


@dataclass
class TaskContext:
    """任务执行上下文"""
    task_id: int
    task: Task
    db: Session
    file_path: Path
    base_name: str
    local_md_dir: Path
    md_path: Path


class BaseTaskHandler(ABC):
    """任务处理器基类 - 策略模式"""
    
    def __init__(self, processor: 'TaskProcessor'):
        self.processor = processor
    
    @abstractmethod
    def get_output_filename(self, base_name: str) -> str:
        """获取输出文件名"""
        pass
    
    @abstractmethod
    def execute_task(self, ctx: TaskContext, model: str) -> bool:
        """执行具体任务"""
        pass
    
    def process(self, ctx: TaskContext) -> None:
        """处理任务的通用流程"""
        try:
            # 初始化任务状态
            self.processor._init_task_processing(ctx.task, ctx.db)
            
            # 确保文件已转换为MD
            ctx.md_path = self.processor._ensure_md_converted(
                ctx.task, ctx.task.file, ctx.md_path, ctx.db
            )
            
            # 执行具体任务
            ctx.task.progress = 30
            ctx.db.commit()
            
            output_path = ctx.local_md_dir / "auto" / self.get_output_filename(ctx.base_name)
            model = self.processor._ai_model_getter()
            
            success = self.execute_task(ctx, model)
            
            if not success:
                if self.processor._check_task_stop_requested(ctx.task_id, ctx.db):
                    ctx.task.status = TaskStatus.CANCELLED
                    ctx.task.error_message = "用户取消了任务"
                    ctx.db.commit()
                    logger.info(f"任务已取消: {ctx.task_id}")
                    return
                raise Exception(f"任务执行失败")
            
            # 更新任务状态为已完成
            ctx.task.status = TaskStatus.COMPLETED
            ctx.task.progress = 100
            ctx.task.output_path = str(output_path)
            ctx.db.commit()
            
            logger.info(f"任务完成: {ctx.task_id}, 输出文件: {output_path}")
            
        except Exception as e:
            # 检查是否是因为停止请求导致异常
            if "用户取消" in str(e) or self.processor._check_task_stop_requested(ctx.task_id, ctx.db):
                ctx.task.status = TaskStatus.CANCELLED
                ctx.task.error_message = "用户取消了任务"
                logger.info(f"任务已取消: {ctx.task_id}")
            else:
                logger.error(f"任务异常: {ctx.task_id}, 错误: {str(e)}")
                ctx.task.status = TaskStatus.FAILED
                ctx.task.error_message = str(e)
            ctx.db.commit()


class SummarizeTaskHandler(BaseTaskHandler):
    """总结任务处理器"""
    
    def get_output_filename(self, base_name: str) -> str:
        return f"{base_name}_summarize.md"
    
    def execute_task(self, ctx: TaskContext, model: str) -> bool:
        output_path = ctx.local_md_dir / "auto" / self.get_output_filename(ctx.base_name)
        
        # 检查停止请求
        if self.processor._check_task_stop_requested(ctx.task_id, ctx.db):
            return False
        
        return summarize_file(ctx.md_path, output_path, model=model)


class TranslateTaskHandler(BaseTaskHandler):
    """翻译任务处理器"""
    
    def get_output_filename(self, base_name: str) -> str:
        return f"{base_name}_zh.md"
    
    def execute_task(self, ctx: TaskContext, model: str) -> bool:
        output_path = ctx.local_md_dir / "auto" / self.get_output_filename(ctx.base_name)
        
        # 创建回调函数
        progress_callback = self.processor._create_progress_callback(
            ctx.task_id, ctx.task, ctx.db, 30, 70
        )
        should_stop = self.processor._create_should_stop_callback(ctx.task_id, ctx.db)
        
        return translate_file(
            ctx.md_path,
            output_path,
            model=model,
            task_id=ctx.task_id,
            db_session=ctx.db,
            progress_callback=progress_callback,
            should_stop_callback=should_stop
        )


class FineTranslateTaskHandler(BaseTaskHandler):
    """精翻任务处理器"""
    
    def get_output_filename(self, base_name: str) -> str:
        return f"{base_name}_fine_zh.md"
    
    def execute_task(self, ctx: TaskContext, model: str) -> bool:
        output_path = ctx.local_md_dir / "auto" / self.get_output_filename(ctx.base_name)
        
        # 解析精翻配置
        fine_config = {}
        if ctx.task.fine_translate_config:
            try:
                fine_config = json.loads(ctx.task.fine_translate_config)
            except:
                fine_config = {}
        
        target_audience = fine_config.get("target_audience", "有一定科学素养，对科技感兴趣的读者群体")
        enable_review = fine_config.get("enable_review", False)
        enable_refinement = fine_config.get("enable_refinement", False)
        max_iterations = fine_config.get("max_iterations", 1)
        
        # 创建回调函数
        progress_callback = self.processor._create_progress_callback(
            ctx.task_id, ctx.task, ctx.db, 30, 70
        )
        should_stop = self.processor._create_should_stop_callback(ctx.task_id, ctx.db)
        
        return fine_translate_file(
            ctx.md_path,
            output_path,
            model=model,
            task_id=ctx.task_id,
            db_session=ctx.db,
            target_audience=target_audience,
            enable_review=enable_review,
            enable_refinement=enable_refinement,
            max_iterations=max_iterations,
            progress_callback=progress_callback,
            should_stop_callback=should_stop
        )


class TaskProcessor:
    """
    任务处理器 - 负责任务队列管理和任务执行
    
    职责：
    1. 管理任务队列状态（单例模式）
    2. 协调任务执行（确保单任务串行）
    3. 处理不同类型的任务（策略模式）
    4. 提供任务停止和恢复功能
    """
    
    def __init__(self, session_factory: Optional[Callable] = None, 
                 ai_model_getter: Optional[Callable] = None):
        """
        初始化任务处理器
        
        Args:
            session_factory: 数据库会话工厂函数，默认为 SessionLocal
            ai_model_getter: AI模型获取函数，默认为 get_ai_model
        """
        self._processing_task_id: Optional[int] = None
        self._queue_lock = threading.Lock()
        self._session_factory = session_factory or SessionLocal
        self._ai_model_getter = ai_model_getter or get_ai_model
        
        # 初始化任务处理器策略
        self._handlers: Dict[TaskType, BaseTaskHandler] = {
            TaskType.SUMMARIZE: SummarizeTaskHandler(self),
            TaskType.TRANSLATE: TranslateTaskHandler(self),
            TaskType.FINE_TRANSLATE: FineTranslateTaskHandler(self),
        }
    
    # ==================== 公共接口 ====================
    
    @property
    def is_processing(self) -> bool:
        """检查是否有任务正在处理"""
        return self._processing_task_id is not None
    
    @property
    def current_task_id(self) -> Optional[int]:
        """获取当前正在处理的任务ID"""
        return self._processing_task_id
    
    def can_start_task(self) -> bool:
        """检查是否可以开始新任务"""
        with self._queue_lock:
            return not self.is_processing
    
    def process_task(self, task_id: int, task_type: TaskType) -> None:
        """
        处理任务（在队列中）
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
        """
        db = self._session_factory()
        
        try:
            # 检查是否可以开始
            if not self.can_start_task():
                logger.warning(f"任务 {task_id} 加入队列,等待当前任务完成")
                return
            
            # 标记开始处理
            self._set_processing_task(task_id)
            
            # 执行任务
            self._execute_task(task_id, task_type, db)
            
        except Exception as e:
            logger.error(f"任务 {task_id} 处理异常: {str(e)}")
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = f"处理异常: {str(e)}"
                db.commit()
        finally:
            # 释放队列
            self._set_processing_task(None)
            db.close()
            
            # 尝试处理下一个任务
            self._process_next_pending_task()
    
    def resume_pending_tasks(self) -> None:
        """
        系统启动时恢复等待中和处理中的任务
        
        处理逻辑：
        1. 将所有处理中(PROCESSING)的任务重置为等待中(PENDING)
        2. 启动第一个等待中的任务
        """
        db = self._session_factory()
        try:
            # 1. 查找所有处理中的任务
            processing_tasks = db.query(Task).filter(
                Task.status == TaskStatus.PROCESSING
            ).all()
            
            if processing_tasks:
                logger.warning(f"发现 {len(processing_tasks)} 个处理中的任务，将重置为等待中")
                for task in processing_tasks:
                    task.status = TaskStatus.PENDING
                    task.stop_requested = False
                    task.error_message = "服务重启，任务已重新加入队列"
                    logger.info(f"任务 {task.id} 已重置为等待中")
                db.commit()
            
            # 2. 统计等待中的任务
            pending_count = db.query(Task).filter(
                Task.status == TaskStatus.PENDING
            ).count()
            
            if pending_count > 0:
                logger.info(f"发现 {pending_count} 个等待中的任务")
                self._process_next_pending_task()
            else:
                logger.info("没有等待中的任务")
                
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    # ==================== 私有方法 ====================
    
    def _set_processing_task(self, task_id: Optional[int]) -> None:
        """设置正在处理的任务ID"""
        with self._queue_lock:
            self._processing_task_id = task_id
            if task_id:
                logger.info(f"任务队列: 开始处理任务 {task_id}")
            else:
                logger.info("任务队列: 任务处理完成,队列空闲")
    
    def _process_next_pending_task(self) -> None:
        """处理下一个等待中的任务"""
        if not self.can_start_task():
            return
        
        db = self._session_factory()
        try:
            # 查找最早创建的等待中任务
            next_task = db.query(Task).filter(
                Task.status == TaskStatus.PENDING
            ).order_by(Task.created_at.asc()).first()
            
            if next_task:
                logger.info(f"任务队列: 发现等待任务 {next_task.id}, 开始处理")
                # 在新线程中处理下一个任务
                threading.Thread(
                    target=self.process_task,
                    args=(next_task.id, next_task.task_type),
                    daemon=True
                ).start()
        finally:
            db.close()
    
    def _execute_task(self, task_id: int, task_type: TaskType, db: Session) -> None:
        """执行任务"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        db_file = task.file
        if not db_file:
            logger.error(f"文件不存在: task_id={task_id}")
            task.status = TaskStatus.FAILED
            task.error_message = "关联文件不存在"
            db.commit()
            return
        
        # 获取任务处理器
        handler = self._handlers.get(task_type)
        if not handler:
            logger.error(f"不支持的任务类型: {task_type}")
            task.status = TaskStatus.FAILED
            task.error_message = f"不支持的任务类型: {task_type}"
            db.commit()
            return
        
        # 准备任务上下文
        ctx = self._prepare_task_context(task_id, task, db_file, db)
        
        # 执行任务
        handler.process(ctx)
    
    def _prepare_task_context(self, task_id: int, task: Task, db_file, db: Session) -> TaskContext:
        """准备任务执行上下文"""
        file_path = Path(db_file.file_path)
        base_name = file_path.stem
        
        # 创建输出目录
        local_md_dir = Path(OUTPUT_DIR) / base_name
        local_md_dir.mkdir(parents=True, exist_ok=True)
        (local_md_dir / "auto").mkdir(exist_ok=True)
        
        # 生成MD路径
        md_path = local_md_dir / "auto" / f"{base_name}.md"
        
        return TaskContext(
            task_id=task_id,
            task=task,
            db=db,
            file_path=file_path,
            base_name=base_name,
            local_md_dir=local_md_dir,
            md_path=md_path
        )
    
    def _check_task_stop_requested(self, task_id: int, db: Session) -> bool:
        """检查任务是否被请求停止"""
        db.expire_all()
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.stop_requested:
            logger.info(f"检测到任务停止请求: {task_id}")
            return True
        return False
    
    def _ensure_md_converted(self, task: Task, db_file, md_path: Path, db: Session) -> Path:
        """
        确保文件已转换为Markdown格式
        
        Args:
            task: 任务对象
            db_file: 文件对象
            md_path: 目标MD路径
            db: 数据库会话
            
        Returns:
            Path: 实际的MD文件路径
        """
        # 检查是否已转换
        if db_file.md_converted and db_file.md_path:
            source_md_path = Path(db_file.md_path)
            if source_md_path.exists():
                # 如果MD文件不在目标位置，复制过去
                if source_md_path != md_path:
                    md_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(source_md_path), str(md_path))
                    logger.info(f"已复制MD文件: {source_md_path} -> {md_path}")
                    return md_path
                else:
                    return source_md_path
            else:
                logger.warning(f"MD文件不存在: {source_md_path}，将重新转换")
        
        # 需要转换
        file_path = Path(db_file.file_path)
        logger.info(f"转换文件到Markdown: {file_path}, use_ocr={task.use_ocr}")
        task.progress = 10
        db.commit()
        
        # 检查停止请求
        if self._check_task_stop_requested(task.id, db):
            task.status = TaskStatus.CANCELLED
            task.error_message = "用户取消了任务"
            db.commit()
            raise Exception("用户取消了任务")
        
        res = convert_pdf_to_md(file_path, md_path, use_ocr=task.use_ocr)
        if not res:
            raise Exception("文件转Markdown失败")
        
        # 更新文件MD转换状态
        db_file.md_converted = True
        db_file.md_path = str(md_path)
        db_file.md_convert_progress = 100
        db.commit()
        
        return md_path
    
    def _init_task_processing(self, task: Task, db: Session) -> None:
        """初始化任务处理状态"""
        task.status = TaskStatus.PROCESSING
        task.progress = 0
        task.stop_requested = False
        db.commit()
        
        # 检查停止请求
        if self._check_task_stop_requested(task.id, db):
            task.status = TaskStatus.CANCELLED
            task.error_message = "用户取消了任务"
            db.commit()
            raise Exception("用户取消了任务")
    
    def _create_progress_callback(
        self, 
        task_id: int, 
        task: Task, 
        db: Session, 
        start_progress: int = 30, 
        progress_range: int = 70
    ) -> Callable:
        """创建进度回调函数"""
        def progress_callback(current: int, total: int, percentage: float):
            # 检查停止请求
            if self._check_task_stop_requested(task_id, db):
                raise Exception("用户取消了任务")
            
            task.current_paragraph = current
            task.total_paragraphs = total
            task.progress = start_progress + int(percentage * (progress_range / 100))
            db.commit()
        
        return progress_callback
    
    def _create_should_stop_callback(self, task_id: int, db: Session) -> Callable:
        """创建停止检查回调函数"""
        def should_stop() -> bool:
            return self._check_task_stop_requested(task_id, db)
        return should_stop


# ==================== 全局单例实例 ====================

_global_task_processor: Optional[TaskProcessor] = None
_processor_lock = threading.Lock()


def get_task_processor() -> TaskProcessor:
    """获取全局任务处理器实例（线程安全的单例）"""
    global _global_task_processor
    if _global_task_processor is None:
        with _processor_lock:
            if _global_task_processor is None:
                _global_task_processor = TaskProcessor()
    return _global_task_processor
