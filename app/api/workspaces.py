"""
工作区 API 路由
"""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.task import File, Task, TaskStatus, TaskType
from app.core.database import get_db
from app.core.config import UPLOAD_DIR, get_workzone_files_dir, get_workzone_output_dir, ensure_workzone_directories
from app.services.workspace_service import (
    create_workspace, get_workspace, list_workspaces,
    update_workspace, delete_workspace, add_files_to_workspace,
    remove_files_from_workspace, scan_folder_to_workspace,
    create_tasks_for_files
)
from app.services.export_service import export_workspace_summaries
from app.utils.logger import logger


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    file_count: int = 0
    
    class Config:
        from_attributes = True


class WorkspaceDetailResponse(WorkspaceResponse):
    files: List[dict] = []
    page: int = 1
    page_size: int = 20
    total: int = 0


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AddFilesRequest(BaseModel):
    file_ids: List[int]


class ScanFolderRequest(BaseModel):
    folder_path: str


class CreateWorkspaceTasksRequest(BaseModel):
    task_type: TaskType
    use_ocr: bool = False
    duplicate_handling: str = "skip"


class CreateWorkspaceTasksResponse(BaseModel):
    created_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    message: str = ""


@router.post("/", response_model=WorkspaceResponse)
def create_workspace_endpoint(
    request: CreateWorkspaceRequest,
    db: Session = Depends(get_db)
):
    workspace = create_workspace(db, request.name, request.description)
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
        "file_count": 0
    }


@router.get("/", response_model=List[WorkspaceResponse])
def list_workspaces_endpoint(db: Session = Depends(get_db)):
    workspaces = list_workspaces(db)
    result = []
    for ws in workspaces:
        result.append({
            "id": ws.id,
            "name": ws.name,
            "description": ws.description,
            "created_at": ws.created_at.isoformat(),
            "updated_at": ws.updated_at.isoformat(),
            "file_count": len(ws.files)
        })
    return result


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
def get_workspace_endpoint(workspace_id: int, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    from collections import defaultdict
    
    workspace = get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作区不存在")
    
    total = len(workspace.files)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_files = workspace.files[start:end]
    
    file_ids = [f.id for f in paginated_files]
    all_tasks = db.query(Task).filter(Task.file_id.in_(file_ids)).all() if file_ids else []
    tasks_map = defaultdict(list)
    for task in all_tasks:
        tasks_map[task.file_id].append(task)
    
    files_data = []
    for file in paginated_files:
        tasks = tasks_map.get(file.id, [])
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                "id": task.id,
                "task_type": task.task_type.value,
                "status": task.status.value,
                "progress": task.progress
            })
        
        files_data.append({
            "id": file.id,
            "file_name": file.file_name,
            "file_size": file.file_size,
            "file_type": file.file_type,
            "tasks": tasks_data
        })
    
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
        "file_count": total,
        "files": files_data,
        "page": page,
        "page_size": page_size,
        "total": total
    }


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace_endpoint(
    workspace_id: int,
    request: UpdateWorkspaceRequest,
    db: Session = Depends(get_db)
):
    workspace = update_workspace(db, workspace_id, request.name, request.description)
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
        "file_count": len(workspace.files)
    }


@router.delete("/{workspace_id}")
def delete_workspace_endpoint(workspace_id: int, db: Session = Depends(get_db)):
    delete_workspace(db, workspace_id)
    return {"message": "工作区删除成功"}


@router.post("/{workspace_id}/files")
def add_files_endpoint(
    workspace_id: int,
    request: AddFilesRequest,
    db: Session = Depends(get_db)
):
    success, errors = add_files_to_workspace(db, workspace_id, request.file_ids)
    return {
        "success": success,
        "errors": errors,
        "added_count": len(success)
    }


@router.delete("/{workspace_id}/files")
def remove_files_endpoint(
    workspace_id: int,
    request: AddFilesRequest,
    db: Session = Depends(get_db)
):
    remove_files_from_workspace(db, workspace_id, request.file_ids)
    return {"message": "文件已从工作区移除"}


@router.post("/{workspace_id}/scan-folder")
def scan_folder_endpoint(
    workspace_id: int,
    request: ScanFolderRequest,
    db: Session = Depends(get_db)
):
    from app.utils.file_utils import calculate_file_md5
    import shutil
    
    folder = Path(request.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="文件夹不存在")
    
    supported_exts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.md']
    added_files = []
    skipped_files = []
    
    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue
        
        ext = file_path.suffix.lower()
        if ext not in supported_exts:
            continue
        
        try:
            file_md5 = calculate_file_md5(str(file_path))
        except Exception as e:
            logger.warning(f"计算 MD5 失败: {file_path}, 错误: {str(e)}")
            skipped_files.append({"file": str(file_path), "reason": "计算 MD5 失败"})
            continue
        
        existing = db.query(File).filter(File.file_md5 == file_md5).first()
        if existing:
            if existing.workspace_id is None:
                existing.workspace_id = workspace_id
                added_files.append({"id": existing.id, "name": existing.file_name, "status": "added"})
            elif existing.workspace_id != workspace_id:
                skipped_files.append({"file": str(file_path), "reason": "已属于其他工作区"})
            else:
                skipped_files.append({"file": str(file_path), "reason": "已在此工作区中"})
            continue
        
        try:
            upload_dir = Path(get_workzone_files_dir(workspace_id))
            ensure_workzone_directories(workspace_id)
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            target_path = upload_dir / file_path.name
            counter = 1
            while target_path.exists():
                target_path = upload_dir / f"{file_path.stem}_{counter}{ext}"
                counter += 1
            
            shutil.copy2(str(file_path), str(target_path))
            file_size = target_path.stat().st_size
            
            db_file = File(
                file_name=file_path.name,
                file_path=str(target_path),
                file_md5=file_md5,
                file_size=file_size,
                file_type=ext,
                workspace_id=workspace_id,
                md_converted=False,
                md_convert_progress=0
            )
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            
            # 处理 Markdown 文件
            if ext == '.md':
                try:
                    output_dir = Path(get_workzone_output_dir(workspace_id)) / target_path.stem / "auto"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    md_target_path = output_dir / target_path.name
                    shutil.copy2(str(target_path), str(md_target_path))
                    db_file.md_path = str(md_target_path)
                    db_file.md_converted = True
                    db_file.md_convert_progress = 100
                    db.commit()
                except Exception as e:
                    logger.error(f"处理 Markdown 文件失败: {str(e)}")
            
            added_files.append({"id": db_file.id, "name": db_file.file_name, "status": "created"})
            
        except Exception as e:
            logger.error(f"复制文件失败: {file_path}, 错误: {str(e)}")
            skipped_files.append({"file": str(file_path), "reason": f"复制失败: {str(e)}"})
    
    return {
        "added_files": added_files,
        "skipped_files": skipped_files,
        "total_added": len(added_files),
        "total_skipped": len(skipped_files)
    }


@router.get("/{workspace_id}/export-csv")
def export_csv_endpoint(workspace_id: int, db: Session = Depends(get_db)):
    return export_workspace_summaries(db, workspace_id)


@router.post("/{workspace_id}/tasks/{task_type}", response_model=CreateWorkspaceTasksResponse)
def create_workspace_tasks(
    workspace_id: int,
    task_type: TaskType,
    request: CreateWorkspaceTasksRequest,
    db: Session = Depends(get_db)
):
    """为工作区所有文件批量创建任务"""
    workspace = get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作区不存在")
    
    if not workspace.files:
        return {"created_count": 0, "skipped_count": 0, "error_count": 0, "message": "工作区没有文件"}
    
    file_ids = [f.id for f in workspace.files]
    return create_tasks_for_files(
        db, file_ids, task_type,
        use_ocr=request.use_ocr,
        duplicate_handling=request.duplicate_handling
    )
