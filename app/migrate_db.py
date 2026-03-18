"""
数据库迁移脚本
从旧的FileTask模型迁移到新的File+Task模型
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine, Base
from app.models.task import File, Task, TaskResult
from app.utils.logger import logger


def migrate_database():
    """执行数据库迁移"""
    logger.info("开始数据库迁移...")
    
    # 删除旧表并创建新表
    logger.info("删除旧表...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("创建新表...")
    Base.metadata.create_all(bind=engine)
    
    logger.info("数据库迁移完成!")
    logger.info("新表结构:")
    logger.info("  - files: 文件表")
    logger.info("  - tasks: 任务表")
    logger.info("  - task_results: 任务结果表")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--force', action='store_true', help='强制执行迁移（删除所有旧数据）')
    args = parser.parse_args()
    
    if not args.force:
        print("警告: 此操作将删除所有现有数据!")
        print("如果确定要继续，请使用 --force 参数")
        print("\n命令: python -m app.migrate_db --force")
        sys.exit(1)
    
    migrate_database()

