"""
API路由定义
提供文档总结和翻译的API接口
"""
import os
import json
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File as FastAPIFile, Form
from fastapi.responses import FileResponse as FastAPIFileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.task import File, Task, TaskStatus, TaskType, TaskResult
from app.core.database import get_db
from app.core.config import OUTPUT_DIR, UPLOAD_DIR
from app.services.pdf_converter import convert_pdf_to_md
from app.services.summarize import summarize_file
from app.services.translate import translate_file
from app.services.fine_translate import fine_translate_file
from app.services.task_processor import get_task_processor
from app.api.dependencies import get_ai_model
from app.utils.logger import logger
from app.utils.file_utils import calculate_file_md5, calculate_file_md5_from_upload, get_file_info

# 创建路由器
router = APIRouter()

# 请求和响应模型
class TaskResponse(BaseModel):
    id: int
    file_id: int
    task_type: TaskType
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int
    current_paragraph: int
    total_paragraphs: int
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    md_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    upload_time: datetime
    md_converted: bool
    md_convert_progress: int
    tasks: List[TaskResponse] = []
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    files: List[FileResponse]


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]


class CreateTaskRequest(BaseModel):
    task_type: TaskType
    use_ocr: bool = False  # 是否使用OCR模式


class CreateFineTranslateTaskRequest(BaseModel):
    """创建精翻任务的请求"""
    task_type: TaskType  # 必须是 fine_translate
    target_audience: str = "有一定科学素养，对科技感兴趣的读者群体"  # 目标读者群体
    enable_review: bool = False  # 是否启用评审步骤
    enable_refinement: bool = False  # 是否启用改进步骤
    max_iterations: int = 1  # 最大改进迭代次数


# 后台任务处理函数
def process_summarize_task(task_id: int, db: Session):
    """处理总结任务"""
    # 获取任务信息
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        logger.error(f"任务不存在: {task_id}")
        return
    
    # 获取关联文件
    db_file = db_task.file
    if not db_file:
        logger.error(f"文件不存在: task_id={task_id}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = "关联文件不存在"
        db.commit()
        return
    
    try:
        # 更新任务状态为处理中
        db_task.status = TaskStatus.PROCESSING
        db_task.progress = 0
        db.commit()
        
        file_path = Path(db_file.file_path)
        base_name = file_path.stem
        
        # 创建输出目录
        local_md_dir = Path(OUTPUT_DIR) / base_name
        local_md_dir.mkdir(parents=True, exist_ok=True)
        (local_md_dir / "auto").mkdir(exist_ok=True)
        
        # 生成MD路径
        md_path = local_md_dir / "auto" / f"{base_name}.md"
        
        # 第一步：检查是否需要转换MD
        if not db_file.md_converted or not md_path.exists():
            logger.info(f"转换PDF到Markdown: {file_path}, use_ocr={db_task.use_ocr}")
            db_task.progress = 10
            db.commit()
            
            res = convert_pdf_to_md(file_path, md_path, use_ocr=db_task.use_ocr)
            if not res:
                raise Exception("PDF转Markdown失败")
            
            # 更新文件MD转换状态
            db_file.md_converted = True
            db_file.md_path = str(md_path)
            db_file.md_convert_progress = 100
            db.commit()
        else:
            md_path = Path(db_file.md_path)
        
        # 第二步：总结
        db_task.progress = 40
        db.commit()
        
        md_summ_path = local_md_dir / "auto" / f"{base_name}_summarize.md"
        model = get_ai_model()
        success = summarize_file(md_path, md_summ_path, model=model)
        
        if not success:
            raise Exception("文档总结失败")
        
        # 更新任务状态为已完成
        db_task.status = TaskStatus.COMPLETED
        db_task.progress = 100
        db_task.output_path = str(md_summ_path)
        
        # 创建任务结果记录
        task_result = TaskResult(
            task_id=task_id,
            output_file=str(md_summ_path)
        )
        db.add(task_result)
        db.commit()
        
        logger.info(f"总结任务完成: {task_id}, 输出文件: {md_summ_path}")
        
    except Exception as e:
        logger.error(f"总结任务异常: {task_id}, 错误: {str(e)}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = str(e)
        db.commit()


def process_translate_task(task_id: int, db: Session):
    """处理翻译任务"""
    # 获取任务信息
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        logger.error(f"任务不存在: {task_id}")
        return
    
    # 获取关联文件
    db_file = db_task.file
    if not db_file:
        logger.error(f"文件不存在: task_id={task_id}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = "关联文件不存在"
        db.commit()
        return
    
    try:
        # 更新任务状态为处理中
        db_task.status = TaskStatus.PROCESSING
        db_task.progress = 0
        db.commit()
        
        file_path = Path(db_file.file_path)
        base_name = file_path.stem
        
        # 创建输出目录
        local_md_dir = Path(OUTPUT_DIR) / base_name
        local_md_dir.mkdir(parents=True, exist_ok=True)
        (local_md_dir / "auto").mkdir(exist_ok=True)
        
        # 生成MD路径
        md_path = local_md_dir / "auto" / f"{base_name}.md"
        
        # 第一步：检查是否需要转换MD
        if not db_file.md_converted or not md_path.exists():
            logger.info(f"转换PDF到Markdown: {file_path}, use_ocr={db_task.use_ocr}")
            db_task.progress = 10
            db.commit()
            
            res = convert_pdf_to_md(file_path, md_path, use_ocr=db_task.use_ocr)
            if not res:
                raise Exception("PDF转Markdown失败")
            
            # 更新文件MD转换状态
            db_file.md_converted = True
            db_file.md_path = str(md_path)
            db_file.md_convert_progress = 100
            db.commit()
        else:
            md_path = Path(db_file.md_path)
        
        # 第二步：翻译
        db_task.progress = 30
        db.commit()
        
        md_zh_path = local_md_dir / "auto" / f"{base_name}_zh.md"
        model = get_ai_model()
        
        # 定义进度回调函数
        def progress_callback(current, total, percentage):
            db_task.current_paragraph = current
            db_task.total_paragraphs = total
            # 翻译占70%进度 (30-100)
            db_task.progress = 30 + int(percentage * 0.7)
            db.commit()
        
        success = translate_file(md_path, md_zh_path, model=model, progress_callback=progress_callback)
        
        if not success:
            raise Exception("文档翻译失败")
        
        # 更新任务状态为已完成
        db_task.status = TaskStatus.COMPLETED
        db_task.progress = 100
        db_task.output_path = str(md_zh_path)
        
        # 创建任务结果记录
        task_result = TaskResult(
            task_id=task_id,
            output_file=str(md_zh_path)
        )
        db.add(task_result)
        db.commit()
        
        logger.info(f"翻译任务完成: {task_id}, 输出文件: {md_zh_path}")
        
    except Exception as e:
        logger.error(f"翻译任务异常: {task_id}, 错误: {str(e)}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = str(e)
        db.commit()


def process_fine_translate_task(task_id: int, db: Session):
    """处理精翻任务"""
    # 获取任务信息
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        logger.error(f"任务不存在: {task_id}")
        return
    
    # 获取关联文件
    db_file = db_task.file
    if not db_file:
        logger.error(f"文件不存在: task_id={task_id}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = "关联文件不存在"
        db.commit()
        return
    
    try:
        # 更新任务状态为处理中
        db_task.status = TaskStatus.PROCESSING
        db_task.progress = 0
        db.commit()
        
        file_path = Path(db_file.file_path)
        base_name = file_path.stem
        
        # 创建输出目录
        local_md_dir = Path(OUTPUT_DIR) / base_name
        local_md_dir.mkdir(parents=True, exist_ok=True)
        (local_md_dir / "auto").mkdir(exist_ok=True)
        
        # 生成MD路径
        md_path = local_md_dir / "auto" / f"{base_name}.md"
        
        # 第一步：检查是否需要转换MD
        if not db_file.md_converted or not md_path.exists():
            logger.info(f"转换PDF到Markdown: {file_path}, use_ocr={db_task.use_ocr}")
            db_task.progress = 10
            db.commit()
            
            res = convert_pdf_to_md(file_path, md_path, use_ocr=db_task.use_ocr)
            if not res:
                raise Exception("PDF转Markdown失败")
            
            # 更新文件MD转换状态
            db_file.md_converted = True
            db_file.md_path = str(md_path)
            db_file.md_convert_progress = 100
            db.commit()
        else:
            md_path = Path(db_file.md_path)
        
        # 第二步：精翻
        db_task.progress = 30
        db.commit()
        
        # 解析精翻配置
        fine_config = {}
        if db_task.fine_translate_config:
            try:
                fine_config = json.loads(db_task.fine_translate_config)
            except:
                fine_config = {}
        
        target_audience = fine_config.get("target_audience", "有一定科学素养，对科技感兴趣的读者群体")
        enable_review = fine_config.get("enable_review", False)
        enable_refinement = fine_config.get("enable_refinement", False)
        max_iterations = fine_config.get("max_iterations", 1)
        
        md_zh_path = local_md_dir / "auto" / f"{base_name}_fine_zh.md"
        model = get_ai_model()
        
        # 定义进度回调函数
        def progress_callback(current, total, percentage):
            db_task.current_paragraph = current
            db_task.total_paragraphs = total
            # 精翻占70%进度 (30-100)
            db_task.progress = 30 + int(percentage * 0.7)
            db.commit()
        
        success = fine_translate_file(
            md_path, 
            md_zh_path, 
            model=model,
            target_audience=target_audience,
            enable_review=enable_review,
            enable_refinement=enable_refinement,
            max_iterations=max_iterations,
            progress_callback=progress_callback
        )
        
        if not success:
            raise Exception("文档精翻失败")
        
        # 更新任务状态为已完成
        db_task.status = TaskStatus.COMPLETED
        db_task.progress = 100
        db_task.output_path = str(md_zh_path)
        
        # 创建任务结果记录
        task_result = TaskResult(
            task_id=task_id,
            output_file=str(md_zh_path)
        )
        db.add(task_result)
        db.commit()
        
        logger.info(f"精翻任务完成: {task_id}, 输出文件: {md_zh_path}")
        
    except Exception as e:
        logger.error(f"精翻任务异常: {task_id}, 错误: {str(e)}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = str(e)
        db.commit()


# API路由
@router.get("/")
def read_root():
    """API根路径"""
    return {"message": "文档总结与翻译API服务"}


# ==================== 文件相关端点 ====================

class LocalFileRequest(BaseModel):
    file_path: str


@router.post("/files/", response_model=FileResponse)
def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db)
):
    """上传文件（仅上传，不执行任务）- 支持MD5去重"""
    # 检查文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.pdf', '.doc', '.docx', '.ppt', '.pptx']:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    # 读取文件内容
    file_content = file.file.read()
    file.file.seek(0)  # 重置文件指针
    
    # 计算MD5
    file_md5 = calculate_file_md5_from_upload(file_content)
    
    # 检查是否已存在相同MD5的文件
    existing_file = db.query(File).filter(File.file_md5 == file_md5).first()
    if existing_file:
        logger.info(f"文件已存在(MD5去重): {file.filename}, 现有文件ID: {existing_file.id}")
        return existing_file
    
    # 保存上传的文件
    upload_dir = Path(UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    
    # 如果文件名已存在,添加时间戳
    if file_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = upload_dir / f"{file_path.stem}_{timestamp}{file_ext}"
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    file_size = len(file_content)
    
    # 创建文件记录
    db_file = File(
        file_name=file.filename,
        file_path=str(file_path),
        file_md5=file_md5,
        file_size=file_size,
        file_type=file_ext,
        md_converted=False,
        md_convert_progress=0
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    logger.info(f"文件上传成功: {file.filename}, ID: {db_file.id}, MD5: {file_md5}")
    return db_file


@router.post("/files/local", response_model=FileResponse)
def register_local_file(
    request: LocalFileRequest,
    db: Session = Depends(get_db)
):
    """注册本地文件（Electron 应用使用，会复制文件到项目目录）- 支持MD5去重"""
    file_path = Path(request.file_path)
    
    # 检查文件是否存在
    if not file_path.exists():
        raise HTTPException(status_code=400, detail="文件不存在")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    # 检查文件类型
    file_ext = file_path.suffix.lower()
    if file_ext not in ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.md']:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    # 计算文件MD5
    try:
        file_md5 = calculate_file_md5(str(file_path))
    except Exception as e:
        logger.error(f"计算文件MD5失败: {file_path}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"计算文件MD5失败: {str(e)}")
    
    # 检查是否已存在相同MD5的文件
    existing_file = db.query(File).filter(File.file_md5 == file_md5).first()
    if existing_file:
        logger.info(f"文件已存在(MD5去重): {file_path}, 现有文件ID: {existing_file.id}, MD5: {file_md5}")
        return existing_file
    
    # 复制文件到上传目录
    try:
        # 确保上传目录存在（转换为 Path 对象）
        upload_dir = Path(UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成目标文件名（使用原始文件名，如果重复则添加序号）
        target_filename = file_path.name
        target_path = upload_dir / target_filename
        counter = 1
        while target_path.exists():
            name_without_ext = file_path.stem
            target_filename = f"{name_without_ext}_{counter}{file_ext}"
            target_path = upload_dir / target_filename
            counter += 1
        
        # 复制文件
        shutil.copy2(str(file_path), str(target_path))
        logger.info(f"文件已复制: {file_path} -> {target_path}")
        
    except Exception as e:
        logger.error(f"复制文件失败: {file_path}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"复制文件失败: {str(e)}")
    
    # 获取文件大小
    file_size = target_path.stat().st_size
    
    # 处理 Markdown 文件
    md_converted = False
    md_convert_progress = 0
    md_path = None
    
    if file_ext == '.md':
        # Markdown 文件直接复制到 output 目录作为已转换文件
        try:
            # 创建文件专属目录（去除扩展名）
            dir_name = Path(target_filename).stem
            output_dir = Path(OUTPUT_DIR) / dir_name / "auto"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            md_target_path = output_dir / target_filename
            shutil.copy2(str(target_path), str(md_target_path))
            
            md_path = str(md_target_path)
            md_converted = True
            md_convert_progress = 100
            
            logger.info(f"Markdown 文件已复制到输出目录: {md_target_path}")
        except Exception as e:
            logger.error(f"复制 Markdown 文件到输出目录失败: {str(e)}", exc_info=True)
            # 不抛出异常，继续创建文件记录
    
    # 创建文件记录（使用复制后的路径）
    db_file = File(
        file_name=target_filename,
        file_path=str(target_path),
        md_path=md_path,
        file_md5=file_md5,
        file_size=file_size,
        file_type=file_ext,
        md_converted=md_converted,
        md_convert_progress=md_convert_progress
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    logger.info(f"本地文件注册成功: {file_path}, ID: {db_file.id}, MD5: {file_md5}, 复制到: {target_path}")
    return db_file


@router.post("/files/local/batch", response_model=FileListResponse)
def register_local_files_batch(
    file_paths: List[str],
    db: Session = Depends(get_db)
):
    """批量注册本地文件（会复制文件到项目目录）"""
    logger.info(f"开始批量注册文件: {file_paths}")
    registered_files = []
    errors = []
    
    for file_path_str in file_paths:
        try:
            logger.info(f"处理文件: {file_path_str}")
            file_path = Path(file_path_str)
            
            # 检查文件
            if not file_path.exists() or not file_path.is_file():
                error_msg = f"{file_path.name}: 文件不存在或不是文件"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
            
            file_ext = file_path.suffix.lower()
            if file_ext not in ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.md']:
                errors.append(f"{file_path.name}: 不支持的文件类型")
                continue
            
            # 计算MD5
            try:
                file_md5 = calculate_file_md5(str(file_path))
            except Exception as e:
                errors.append(f"{file_path.name}: 计算MD5失败 - {str(e)}")
                continue
            
            # 检查是否已存在相同MD5的文件
            existing_file = db.query(File).filter(File.file_md5 == file_md5).first()
            if existing_file:
                registered_files.append(existing_file)
                logger.info(f"文件已存在(MD5去重): {file_path.name}, 使用现有文件ID: {existing_file.id}")
                continue
            
            # 复制文件到上传目录
            try:
                # 确保上传目录存在（转换为 Path 对象）
                upload_dir = Path(UPLOAD_DIR)
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成目标文件名（使用原始文件名，如果重复则添加序号）
                target_filename = file_path.name
                target_path = upload_dir / target_filename
                counter = 1
                while target_path.exists():
                    name_without_ext = file_path.stem
                    target_filename = f"{name_without_ext}_{counter}{file_ext}"
                    target_path = upload_dir / target_filename
                    counter += 1
                
                # 复制文件
                shutil.copy2(str(file_path), str(target_path))
                logger.info(f"文件已复制: {file_path} -> {target_path}")
                
            except Exception as e:
                errors.append(f"{file_path.name}: 复制文件失败 - {str(e)}")
                logger.error(f"复制文件异常: {str(e)}", exc_info=True)
                continue
            
            # 获取文件大小
            file_size = target_path.stat().st_size
            
            # 处理 Markdown 文件
            md_converted = False
            md_convert_progress = 0
            md_path = None
            
            if file_ext == '.md':
                # Markdown 文件直接复制到 output 目录作为已转换文件
                logger.info(f"检测到 Markdown 文件，开始处理: {target_filename}")
                try:
                    # 创建文件专属目录（去除扩展名）
                    dir_name = Path(target_filename).stem  # 使用 stem 获取无扩展名的文件名
                    output_dir = Path(OUTPUT_DIR) / dir_name / "auto"
                    logger.info(f"创建输出目录: {output_dir}")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    md_target_path = output_dir / target_filename
                    shutil.copy2(str(target_path), str(md_target_path))
                    
                    md_path = str(md_target_path)
                    md_converted = True
                    md_convert_progress = 100
                    
                    logger.info(f"Markdown 文件已复制到输出目录: {md_target_path}, md_converted={md_converted}")
                except Exception as e:
                    logger.error(f"复制 Markdown 文件到输出目录失败: {str(e)}", exc_info=True)
                    # 不抛出异常，继续创建文件记录
            
            # 创建文件记录（使用复制后的路径）
            logger.info(f"创建数据库记录: {target_filename}, md_converted={md_converted}, md_path={md_path}")
            db_file = File(
                file_name=target_filename,
                file_path=str(target_path),
                md_path=md_path,
                file_md5=file_md5,
                file_size=file_size,
                file_type=file_ext,
                md_converted=md_converted,
                md_convert_progress=md_convert_progress
            )
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            registered_files.append(db_file)
            logger.info(f"文件注册成功: {target_filename}, ID: {db_file.id}, 数据库中 md_converted={db_file.md_converted}, md_path={db_file.md_path}")
            
        except Exception as e:
            error_msg = f"{Path(file_path_str).name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"注册文件失败: {file_path_str}, 错误: {str(e)}", exc_info=True)
    
    if errors:
        logger.warning(f"批量注册完成,部分失败: {errors}")
    
    logger.info(f"批量注册本地文件: 成功 {len(registered_files)}, 失败 {len(errors)}")
    return {"files": registered_files}


@router.get("/files/", response_model=FileListResponse)
def list_files(db: Session = Depends(get_db)):
    """获取文件列表"""
    files = db.query(File).order_by(File.upload_time.desc()).all()
    return {"files": files}


@router.get("/files/{file_id}", response_model=FileResponse)
def get_file(file_id: int, db: Session = Depends(get_db)):
    """获取文件详情及其关联任务"""
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return file


@router.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """删除文件及其所有任务"""
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 删除物理文件
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    if file.md_path and os.path.exists(file.md_path):
        os.remove(file.md_path)
    
    # 删除数据库记录（级联删除关联任务）
    db.delete(file)
    db.commit()
    
    logger.info(f"文件已删除: {file_id}")
    return {"message": "文件删除成功"}


class CreateTasksBatchRequest(BaseModel):
    file_ids: List[int]
    task_type: TaskType
    use_ocr: bool = False  # 是否使用OCR模式


class SkippedFileInfo(BaseModel):
    file_id: int
    file_name: str
    reason: str


class CreateTasksBatchResponse(BaseModel):
    created_tasks: List[TaskResponse]
    skipped_files: List[SkippedFileInfo]
    errors: List[str]


@router.post("/files/batch/tasks", response_model=CreateTasksBatchResponse)
def create_tasks_batch(
    request: CreateTasksBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量为多个文件创建任务（总结或翻译）"""
    logger.info(f"批量创建任务请求: file_ids={request.file_ids}, task_type={request.task_type}")
    created_tasks = []
    skipped_files = []
    errors = []
    
    for file_id in request.file_ids:
        try:
            # 检查文件是否存在
            file = db.query(File).filter(File.id == file_id).first()
            if not file:
                errors.append(f"文件ID {file_id}: 文件不存在")
                continue
            
            # 检查是否已有相同类型的任务（包括已完成的任务）
            existing_task = db.query(Task).filter(
                Task.file_id == file_id,
                Task.task_type == request.task_type,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED])
            ).first()
            
            if existing_task:
                if existing_task.status == TaskStatus.COMPLETED:
                    reason = f"已有已完成的{request.task_type.value}任务，如需重新执行请在任务队列中点击重试"
                else:
                    reason = f"已有{request.task_type.value}任务正在进行中或等待中"
                
                skipped_files.append(SkippedFileInfo(
                    file_id=file_id,
                    file_name=file.file_name,
                    reason=reason
                ))
                continue
            
            # 创建任务记录
            db_task = Task(
                file_id=file_id,
                task_type=request.task_type,
                status=TaskStatus.PENDING,
                progress=0,
                current_paragraph=0,
                total_paragraphs=0,
                use_ocr=request.use_ocr
            )
            db.add(db_task)
            db.commit()
            db.refresh(db_task)
            
            # 使用任务队列处理
            import threading
            task_processor = get_task_processor()
            threading.Thread(
                target=task_processor.process_task,
                args=(db_task.id, request.task_type),
                daemon=True
            ).start()
            
            created_tasks.append(db_task)
            logger.info(f"批量任务已加入队列: file_id={file_id}, task_id={db_task.id}, type={request.task_type}, use_ocr={request.use_ocr}")
            
        except Exception as e:
            errors.append(f"文件ID {file_id}: {str(e)}")
            logger.error(f"批量创建任务失败: file_id={file_id}, 错误: {str(e)}")
    
    logger.info(f"批量创建任务完成: 成功 {len(created_tasks)}, 跳过 {len(skipped_files)}, 失败 {len(errors)}")
    
    return {
        "created_tasks": created_tasks,
        "skipped_files": skipped_files,
        "errors": errors
    }


@router.post("/files/{file_id}/tasks", response_model=TaskResponse)
def create_task(
    file_id: int,
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """为文件创建任务（总结或翻译）- 使用任务队列"""
    # 检查文件是否存在
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查是否已有相同类型的任务（包括已完成的任务）
    existing_task = db.query(Task).filter(
        Task.file_id == file_id,
        Task.task_type == request.task_type,
        Task.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED])
    ).first()
    
    if existing_task:
        if existing_task.status == TaskStatus.COMPLETED:
            raise HTTPException(status_code=400, detail=f"该文件已有已完成的{request.task_type.value}任务，如需重新执行请在任务队列中点击重试")
        else:
            raise HTTPException(status_code=400, detail=f"该文件已有{request.task_type.value}任务正在进行中或等待中")
    
    # 创建任务记录
    db_task = Task(
        file_id=file_id,
        task_type=request.task_type,
        status=TaskStatus.PENDING,
        progress=0,
        current_paragraph=0,
        total_paragraphs=0,
        use_ocr=request.use_ocr
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # 使用任务队列处理
    import threading
    task_processor = get_task_processor()
    threading.Thread(
        target=task_processor.process_task,
        args=(db_task.id, request.task_type),
        daemon=True
    ).start()
    
    logger.info(f"任务已加入队列: file_id={file_id}, task_id={db_task.id}, type={request.task_type}, use_ocr={request.use_ocr}")
    return db_task


@router.post("/files/{file_id}/fine-translate", response_model=TaskResponse)
def create_fine_translate_task(
    file_id: int,
    request: CreateFineTranslateTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """为文件创建精翻任务 - 使用任务队列"""
    # 检查文件是否存在
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 验证任务类型
    if request.task_type != TaskType.FINE_TRANSLATE:
        raise HTTPException(status_code=400, detail="任务类型必须是 fine_translate")
    
    # 检查是否已有相同类型的任务（包括已完成的任务）
    existing_task = db.query(Task).filter(
        Task.file_id == file_id,
        Task.task_type == TaskType.FINE_TRANSLATE,
        Task.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED])
    ).first()
    
    if existing_task:
        if existing_task.status == TaskStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="该文件已有已完成的精翻任务，如需重新执行请在任务队列中点击重试")
        else:
            raise HTTPException(status_code=400, detail="该文件已有精翻任务正在进行中或等待中")
    
    # 准备精翻配置
    fine_config = {
        "target_audience": request.target_audience,
        "enable_review": request.enable_review,
        "enable_refinement": request.enable_refinement,
        "max_iterations": request.max_iterations
    }
    
    # 创建任务记录
    db_task = Task(
        file_id=file_id,
        task_type=TaskType.FINE_TRANSLATE,
        status=TaskStatus.PENDING,
        progress=0,
        current_paragraph=0,
        total_paragraphs=0,
        fine_translate_config=json.dumps(fine_config, ensure_ascii=False)
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # 使用任务队列处理
    import threading
    task_processor = get_task_processor()
    threading.Thread(
        target=task_processor.process_task,
        args=(db_task.id, TaskType.FINE_TRANSLATE),
        daemon=True
    ).start()
    
    logger.info(f"精翻任务已加入队列: file_id={file_id}, task_id={db_task.id}, config={fine_config}")
    return db_task


# ==================== 任务相关端点 ====================

@router.get("/tasks/queue/status")
def get_queue_status(db: Session = Depends(get_db)):
    """获取任务队列状态"""
    task_processor = get_task_processor()
    
    pending_count = db.query(Task).filter(Task.status == TaskStatus.PENDING).count()
    processing_count = db.query(Task).filter(Task.status == TaskStatus.PROCESSING).count()
    
    current_task_id = task_processor.current_task_id
    current_task = None
    if current_task_id:
        current_task = db.query(Task).filter(Task.id == current_task_id).first()
    
    # 获取等待队列中的任务
    pending_tasks = db.query(Task).filter(
        Task.status == TaskStatus.PENDING
    ).order_by(Task.created_at.asc()).limit(5).all()
    
    return {
        "is_processing": task_processor.is_processing,
        "current_task_id": current_task_id,
        "current_task": current_task if current_task else None,
        "pending_count": pending_count,
        "processing_count": processing_count,
        "queue_length": pending_count,
        "next_tasks": [{"id": t.id, "file_id": t.file_id, "task_type": t.task_type} for t in pending_tasks]
    }


@router.get("/tasks/", response_model=TaskListResponse)
def list_tasks(db: Session = Depends(get_db)):
    """获取所有任务"""
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return {"tasks": tasks}


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/tasks/{task_id}/download")
def download_task_result(task_id: int, db: Session = Depends(get_db)):
    """下载任务结果"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    if not task.output_path or not os.path.exists(task.output_path):
        raise HTTPException(status_code=404, detail="输出文件不存在")
    
    return FastAPIFileResponse(
        path=task.output_path,
        filename=Path(task.output_path).name,
        media_type="text/markdown"
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskResponse)
def retry_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """重试失败、已完成或已取消的任务 - 使用任务队列"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status not in [TaskStatus.FAILED, TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="只能重试失败、已完成或已取消的任务")
    
    # 重置任务状态
    task.status = TaskStatus.PENDING
    task.progress = 0
    task.current_paragraph = 0
    task.total_paragraphs = 0
    task.error_message = None
    task.stop_requested = False  # 重置停止标志
    
    # 保留原输出路径,以便覆盖
    # task.output_path = None
    
    db.commit()
    db.refresh(task)
    
    # 使用任务队列处理
    import threading
    task_processor = get_task_processor()
    threading.Thread(
        target=task_processor.process_task,
        args=(task.id, task.task_type),
        daemon=True
    ).start()
    
    logger.info(f"重试任务已加入队列: {task_id}")
    return task


@router.post("/tasks/{task_id}/stop", response_model=TaskResponse)
def stop_task(task_id: int, db: Session = Depends(get_db)):
    """停止正在运行的任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 只能停止正在处理中的任务
    if task.status != TaskStatus.PROCESSING:
        raise HTTPException(status_code=400, detail=f"任务状态为 {task.status.value}，无法停止")
    
    # 检查是否是当前正在处理的任务
    task_processor = get_task_processor()
    current_task_id = task_processor.current_task_id
    if current_task_id != task_id:
        raise HTTPException(status_code=400, detail="该任务不是当前正在处理的任务")
    
    # 设置停止标志
    task.stop_requested = True
    db.commit()
    db.refresh(task)
    
    logger.info(f"任务停止请求已发送: {task_id}")
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务及其输出文件、翻译进度"""
    from app.models.task import TranslateProgress
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 不允许删除正在处理的任务，需要先停止
    if task.status == TaskStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="无法删除正在处理的任务，请先停止任务")
    
    # 删除输出文件
    if task.output_path and os.path.exists(task.output_path):
        try:
            os.remove(task.output_path)
            logger.info(f"删除任务输出文件: {task.output_path}")
        except Exception as e:
            logger.warning(f"删除输出文件失败: {task.output_path}, 错误: {str(e)}")
    
    # 删除翻译进度记录
    progress_count = db.query(TranslateProgress).filter(
        TranslateProgress.task_id == task_id
    ).delete()
    if progress_count > 0:
        logger.info(f"删除翻译进度记录: {progress_count} 条")
    
    # 删除任务结果记录
    db.query(TaskResult).filter(TaskResult.task_id == task_id).delete()
    
    # 删除任务记录
    db.delete(task)
    db.commit()
    
    logger.info(f"任务已删除: {task_id}")
    return {"message": "任务删除成功", "task_id": task_id}


@router.post("/tasks/{task_id}/force-stop")
def force_stop_task(task_id: int, db: Session = Depends(get_db)):
    """强制停止并取消任务（用于处理卡住的任务）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status not in [TaskStatus.PROCESSING, TaskStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"任务状态为 {task.status.value}，无需停止")
    
    # 直接设置为已取消
    task.status = TaskStatus.CANCELLED
    task.stop_requested = True
    task.error_message = "任务被强制停止"
    db.commit()
    
    logger.warning(f"任务被强制停止: {task_id}")
    return {"message": "任务已强制停止", "task_id": task_id}


@router.post("/tasks/batch/delete")
def delete_tasks_batch(task_ids: List[int], db: Session = Depends(get_db)):
    """批量删除任务"""
    from app.models.task import TranslateProgress
    
    deleted_count = 0
    errors = []
    
    for task_id in task_ids:
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                errors.append(f"任务 {task_id}: 不存在")
                continue
            
            if task.status == TaskStatus.PROCESSING:
                errors.append(f"任务 {task_id}: 正在处理中,无法删除,请先停止任务")
                continue
            
            # 删除输出文件
            if task.output_path and os.path.exists(task.output_path):
                try:
                    os.remove(task.output_path)
                except Exception as e:
                    logger.warning(f"删除输出文件失败: {task.output_path}, 错误: {str(e)}")
            
            # 删除翻译进度记录
            db.query(TranslateProgress).filter(
                TranslateProgress.task_id == task_id
            ).delete()
            
            # 删除任务结果记录
            db.query(TaskResult).filter(TaskResult.task_id == task_id).delete()
            
            # 删除任务记录
            db.delete(task)
            deleted_count += 1
            
        except Exception as e:
            errors.append(f"任务 {task_id}: {str(e)}")
            logger.error(f"删除任务失败: {task_id}, 错误: {str(e)}")
    
    db.commit()
    
    logger.info(f"批量删除任务: 成功 {deleted_count}, 失败 {len(errors)}")
    return {
        "message": f"成功删除 {deleted_count} 个任务",
        "deleted_count": deleted_count,
        "errors": errors if errors else None
    }


@router.get("/tasks/{task_id}/content")
def get_task_content(task_id: int, db: Session = Depends(get_db)):
    """获取任务输出文件的内容（用于预览）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    if not task.output_path or not os.path.exists(task.output_path):
        raise HTTPException(status_code=404, detail="输出文件不存在")
    
    try:
        with open(task.output_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "content": content,
            "file_name": Path(task.output_path).name,
            "file_path": task.output_path
        }
    except Exception as e:
        logger.error(f"读取文件内容失败: {task.output_path}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail="读取文件内容失败")


@router.get("/files/{file_id}/md-content")
def get_file_md_content(file_id: int, db: Session = Depends(get_db)):
    """获取文件转换后的 Markdown 内容（用于预览原始 MD）"""
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not file.md_converted or not file.md_path:
        raise HTTPException(status_code=400, detail="文件尚未转换为 Markdown")
    
    if not os.path.exists(file.md_path):
        raise HTTPException(status_code=404, detail="Markdown 文件不存在")
    
    try:
        with open(file.md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "content": content,
            "file_name": Path(file.md_path).name,
            "file_path": file.md_path
        }
    except Exception as e:
        logger.error(f"读取 Markdown 文件内容失败: {file.md_path}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail="读取 Markdown 文件内容失败")