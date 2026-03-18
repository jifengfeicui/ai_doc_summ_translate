"""
任务相关数据模型
使用SQLAlchemy ORM
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship

from app.core.database import Base


# 任务类型枚举
class TaskType(str, Enum):
    SUMMARIZE = "summarize"  # 总结任务
    TRANSLATE = "translate"  # 翻译任务
    FINE_TRANSLATE = "fine_translate"  # 精翻任务（多步骤深度翻译）


# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"      # 等待执行
    PROCESSING = "processing"  # 正在执行
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


# 文件模型
class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, index=True)  # 文件名
    file_path = Column(String)              # 原始文件路径
    file_md5 = Column(String(32), index=True, nullable=True)  # 文件MD5哈希(用于去重)
    md_path = Column(String, nullable=True)  # 转换后的Markdown路径
    file_size = Column(BigInteger, nullable=True)  # 文件大小(字节)
    file_type = Column(String, nullable=True)  # 文件类型(扩展名)
    upload_time = Column(DateTime, default=datetime.now)  # 上传时间
    md_converted = Column(Boolean, default=False)  # 是否已转换为Markdown
    md_convert_progress = Column(Integer, default=0)  # Markdown转换进度(0-100)
    
    # 关联任务 (一对多)
    tasks = relationship("Task", back_populates="file", cascade="all, delete-orphan")


# 任务模型
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))  # 关联文件
    task_type = Column(SQLEnum(TaskType))   # 任务类型
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)  # 任务状态
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间
    error_message = Column(Text, nullable=True)  # 错误信息
    output_path = Column(String, nullable=True)  # 输出文件路径
    progress = Column(Integer, default=0)        # 进度百分比(0-100)
    
    # 翻译任务的段落进度
    current_paragraph = Column(Integer, default=0)  # 当前段落
    total_paragraphs = Column(Integer, default=0)   # 总段落数
    
    # 精翻任务的配置 (JSON格式字符串)
    fine_translate_config = Column(Text, nullable=True)  # 精翻配置：target_audience, enable_review, enable_refinement, max_iterations
    
    # 任务停止标志
    stop_requested = Column(Boolean, default=False)  # 是否请求停止任务
    
    # OCR选项
    use_ocr = Column(Boolean, default=False)  # 是否使用OCR模式进行PDF转换
    
    # 关联文件
    file = relationship("File", back_populates="tasks")
    
    # 关联任务结果
    results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")


# 任务结果模型
class TaskResult(Base):
    __tablename__ = "task_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    output_file = Column(String)           # 输出文件路径
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联任务
    task = relationship("Task", back_populates="results")


# 翻译进度模型（用于存储分块翻译进度）
class TranslateProgress(Base):
    __tablename__ = "translate_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), index=True)
    chunk_index = Column(Integer)              # 分块索引
    chunk_hash = Column(String(32))            # 分块内容的MD5哈希（用于验证）
    translated_content = Column(Text)          # 翻译后的内容
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联任务
    task = relationship("Task", foreign_keys=[task_id])


# 兼容性别名 (暂时保留，用于平滑过渡)
FileTask = Task

