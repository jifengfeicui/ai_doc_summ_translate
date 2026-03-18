"""
任务队列管理器
确保同一时间只执行一个任务
"""
import asyncio
from typing import Optional, Callable
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus, TaskType
from app.utils.logger import logger


class TaskQueueManager:
    """任务队列管理器 - 单例模式"""
    
    _instance: Optional['TaskQueueManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._processing_task_id: Optional[int] = None
        self._processing_lock = asyncio.Lock()
        self._queue_lock = asyncio.Lock()
        logger.info("任务队列管理器初始化完成")
    
    @property
    def is_processing(self) -> bool:
        """检查是否有任务正在处理"""
        return self._processing_task_id is not None
    
    @property
    def current_task_id(self) -> Optional[int]:
        """获取当前正在处理的任务ID"""
        return self._processing_task_id
    
    async def can_start_task(self, task_id: int) -> bool:
        """
        检查任务是否可以开始执行
        
        Args:
            task_id: 任务ID
            
        Returns:
            True表示可以开始,False表示需要等待
        """
        async with self._queue_lock:
            # 如果没有任务在处理,或者就是这个任务,则可以开始
            if not self.is_processing or self._processing_task_id == task_id:
                return True
            return False
    
    async def start_task(self, task_id: int) -> bool:
        """
        标记任务开始处理
        
        Args:
            task_id: 任务ID
            
        Returns:
            True表示成功获取执行权限,False表示有其他任务正在执行
        """
        async with self._processing_lock:
            if self.is_processing and self._processing_task_id != task_id:
                logger.warning(f"任务 {task_id} 无法开始: 任务 {self._processing_task_id} 正在执行")
                return False
            
            self._processing_task_id = task_id
            logger.info(f"任务 {task_id} 开始执行")
            return True
    
    async def finish_task(self, task_id: int):
        """
        标记任务执行完成
        
        Args:
            task_id: 任务ID
        """
        async with self._processing_lock:
            if self._processing_task_id == task_id:
                self._processing_task_id = None
                logger.info(f"任务 {task_id} 执行完成")
            else:
                logger.warning(f"任务 {task_id} 尝试结束,但当前处理的是任务 {self._processing_task_id}")
    
    def get_next_pending_task(self, db: Session) -> Optional[Task]:
        """
        获取下一个等待执行的任务
        
        Args:
            db: 数据库会话
            
        Returns:
            下一个待执行的任务,如果没有则返回None
        """
        if self.is_processing:
            return None
        
        # 查找最早创建的等待中任务
        task = db.query(Task).filter(
            Task.status == TaskStatus.PENDING
        ).order_by(Task.created_at.asc()).first()
        
        return task
    
    def get_queue_status(self, db: Session) -> dict:
        """
        获取队列状态信息
        
        Args:
            db: 数据库会话
            
        Returns:
            包含队列状态的字典
        """
        pending_count = db.query(Task).filter(
            Task.status == TaskStatus.PENDING
        ).count()
        
        processing_task = None
        if self._processing_task_id:
            processing_task = db.query(Task).filter(
                Task.id == self._processing_task_id
            ).first()
        
        return {
            "is_processing": self.is_processing,
            "current_task_id": self._processing_task_id,
            "current_task": processing_task,
            "pending_count": pending_count,
            "queue_length": pending_count
        }


# 全局任务队列管理器实例
task_queue_manager = TaskQueueManager()


def get_task_queue_manager() -> TaskQueueManager:
    """获取任务队列管理器实例"""
    return task_queue_manager


