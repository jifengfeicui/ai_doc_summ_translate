"""
FastAPI主应用
文档总结与翻译系统的API服务入口
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.database import create_tables
from app.core.config import OUTPUT_DIR, UPLOAD_DIR, INPUT_DIR, TEMP_DIR
from app.utils.logger import logger

# 创建FastAPI应用
app = FastAPI(
    title="文档总结与翻译API",
    description="提供文档总结和翻译功能的API接口",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保必要的目录存在
for directory in [INPUT_DIR, OUTPUT_DIR, UPLOAD_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"确保目录存在: {directory}")

# 创建数据库表
create_tables()
logger.info("数据库表初始化完成")

# 挂载静态文件目录
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# 注册路由
app.include_router(router, prefix="/api")

# 启动时的日志
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("="*50)
    logger.info("文档总结与翻译API服务启动")
    logger.info(f"输入目录: {INPUT_DIR}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info(f"上传目录: {UPLOAD_DIR}")
    logger.info(f"临时目录: {TEMP_DIR}")
    logger.info("="*50)
    
    # 恢复等待中的任务
    logger.info("\n检查并恢复等待中的任务...")
    from app.services.task_processor import get_task_processor
    task_processor = get_task_processor()
    task_processor.resume_pending_tasks()
    logger.info("任务恢复检查完成\n")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("文档总结与翻译API服务关闭")


# 用于直接运行的入口
if __name__ == "__main__":
    import uvicorn
    from app.core.config import APP_HOST, APP_PORT, DEBUG
    
    logger.info("="*50)
    logger.info("文档总结与翻译API服务")
    logger.info("="*50)
    logger.info(f"监听地址: {APP_HOST}:{APP_PORT}")
    logger.info(f"调试模式: {DEBUG}")
    logger.info("\nAPI文档将在以下地址可用:")
    logger.info(f"  http://localhost:{APP_PORT}/docs")
    logger.info("="*50)
    
    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=DEBUG
    )

