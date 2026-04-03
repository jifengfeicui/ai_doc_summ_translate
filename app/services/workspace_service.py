"""
工作区服务
"""
import os
import shutil
import threading
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.models.workspace import Workspace
from app.models.task import File, Task, TaskStatus, TaskType
from app.core.config import UPLOAD_DIR, OUTPUT_DIR
from app.utils.logger import logger
from app.services.task_processor import get_task_processor


def create_workspace(db: Session, name: str, description: str = None) -> Workspace:
    """创建工作区"""
    workspace = Workspace(name=name, description=description)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_workspace(db: Session, workspace_id: int) -> Optional[Workspace]:
    """获取工作区"""
    return db.query(Workspace).filter(Workspace.id == workspace_id).first()


def list_workspaces(db: Session) -> list[Workspace]:
    """获取工作区列表"""
    return db.query(Workspace).order_by(Workspace.created_at.desc()).all()


def update_workspace(db: Session, workspace_id: int, name: str = None, description: str = None) -> Workspace:
    """更新工作区"""
    workspace = get_workspace(db, workspace_id)
    if not workspace:
        raise ValueError(f"工作区 {workspace_id} 不存在")
    
    if name is not None:
        workspace.name = name
    if description is not None:
        workspace.description = description
    
    db.commit()
    db.refresh(workspace)
    return workspace


def delete_workspace(db: Session, workspace_id: int):
    """删除工作区（仅解绑文件，不删除）"""
    workspace = get_workspace(db, workspace_id)
    if not workspace:
        raise ValueError(f"工作区 {workspace_id} 不存在")
    
    # 解绑所有文件
    for file in workspace.files:
        file.workspace_id = None
    
    db.commit()
    
    # 删除工作区
    db.delete(workspace)
    db.commit()


def add_files_to_workspace(db: Session, workspace_id: int, file_ids: list[int]) -> tuple[list[int], list[str]]:
    """向工作区添加文件"""
    workspace = get_workspace(db, workspace_id)
    if not workspace:
        raise ValueError(f"工作区 {workspace_id} 不存在")
    
    success = []
    errors = []
    
    for file_id in file_ids:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            errors.append(f"文件 {file_id} 不存在")
            continue
        
        if file.workspace_id is not None:
            errors.append(f"文件 {file.file_name} 已属于其他工作区")
            continue
        
        file.workspace_id = workspace_id
        success.append(file_id)
    
    db.commit()
    return success, errors


def remove_files_from_workspace(db: Session, workspace_id: int, file_ids: list[int]):
    """从工作区移除文件"""
    for file_id in file_ids:
        file = db.query(File).filter(File.id == file_id, File.workspace_id == workspace_id).first()
        if file:
            file.workspace_id = None
    
    db.commit()


def scan_folder_to_workspace(db: Session, workspace_id: int, folder_path: str) -> dict:
    """扫描文件夹并添加到工作区"""
    import os
    
    workspace = get_workspace(db, workspace_id)
    if not workspace:
        raise ValueError(f"工作区 {workspace_id} 不存在")
    
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"文件夹不存在: {folder_path}")
    
    supported_exts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.md']
    files_to_add = []
    
    for root, dirs, files in os.walk(folder):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in supported_exts:
                files_to_add.append(Path(root) / file)
    
    return {
        "total_files": len(files_to_add),
        "files": [str(f) for f in files_to_add]
    }


def create_tasks_for_files(
    db: Session,
    file_ids: list[int],
    task_type: TaskType,
    use_ocr: bool = False,
    duplicate_handling: str = "skip"
) -> dict:
    """
    批量为文件创建任务（复用逻辑）
    
    Args:
        db: 数据库会话
        file_ids: 文件ID列表
        task_type: 任务类型
        use_ocr: 是否使用OCR
        duplicate_handling: 重复处理方式 (skip/retry/force)
    
    Returns:
        dict: 包含 created_count, skipped_count, error_count, message
    """
    if not file_ids:
        return {"created_count": 0, "skipped_count": 0, "error_count": 0, "message": "没有文件"}
    
    files = db.query(File).filter(File.id.in_(file_ids)).all()
    file_map = {f.id: f for f in files}
    
    existing_task_ids = [fid for fid in file_ids if fid in file_map]
    if existing_task_ids:
        query = db.query(Task).filter(
            Task.file_id.in_(existing_task_ids),
            Task.task_type == task_type,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED])
        )
        existing_tasks = query.all()
        existing_task_map = {t.file_id: t for t in existing_tasks}
    else:
        existing_task_map = {}
    
    tasks_to_create = []
    tasks_to_delete = []
    skipped_count = 0
    error_count = 0
    
    for file_id in file_ids:
        file = file_map.get(file_id)
        if not file:
            error_count += 1
            continue
        
        existing_task = existing_task_map.get(file_id)
        
        if existing_task:
            if duplicate_handling in ["retry", "force"]:
                if duplicate_handling == "force" and existing_task.output_path:
                    try:
                        if os.path.exists(existing_task.output_path):
                            os.remove(existing_task.output_path)
                    except Exception as e:
                        logger.warning(f"删除输出文件失败: {existing_task.output_path}, 错误: {e}")
                tasks_to_delete.append(existing_task)
            else:
                skipped_count += 1
                continue
        
        tasks_to_create.append(Task(
            file_id=file_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            progress=0,
            current_paragraph=0,
            total_paragraphs=0,
            use_ocr=use_ocr
        ))
    
    if tasks_to_delete:
        for task in tasks_to_delete:
            db.delete(task)
        db.commit()
    
    if tasks_to_create:
        db.add_all(tasks_to_create)
        db.commit()
        
        for task in tasks_to_create:
            db.refresh(task)
            logger.info(f"任务已创建: file_id={task.file_id}, task_id={task.id}, type={task_type}")
    
    created_count = len(tasks_to_create)
    
    if created_count > 0:
        try:
            task_processor = get_task_processor()
            first_task = tasks_to_create[0]
            threading.Thread(
                target=task_processor.process_task,
                args=(first_task.id, task_type),
                daemon=True
            ).start()
            logger.info(f"任务队列: 第一个任务 {first_task.id} 开始处理")
        except Exception as e:
            logger.error(f"启动任务处理失败: {e}")
    
    message = f"成功创建 {created_count} 个任务"
    if skipped_count > 0:
        message += f"，跳过 {skipped_count} 个"
    if error_count > 0:
        message += f"，失败 {error_count} 个"
    
    return {
        "created_count": created_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "message": message
    }
