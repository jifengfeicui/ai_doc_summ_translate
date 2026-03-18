"""
数据库迁移脚本：为tasks表添加use_ocr字段
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine
from app.utils.logger import logger


def migrate_add_use_ocr():
    """为tasks表添加use_ocr字段"""
    logger.info("开始迁移：为tasks表添加use_ocr字段...")
    
    try:
        with engine.connect() as conn:
            # 检查列是否已存在
            result = conn.execute(text("PRAGMA table_info(tasks)"))
            columns = [row[1] for row in result]
            
            if 'use_ocr' in columns:
                logger.info("use_ocr字段已存在，无需迁移")
                return
            
            # 添加use_ocr列，默认值为False
            conn.execute(text("ALTER TABLE tasks ADD COLUMN use_ocr BOOLEAN DEFAULT 0"))
            conn.commit()
            
            logger.info("成功添加use_ocr字段到tasks表")
            logger.info("所有现有任务的use_ocr默认设置为False")
    
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        raise


if __name__ == "__main__":
    migrate_add_use_ocr()
    print("\n迁移完成！")
    print("新字段: tasks.use_ocr (BOOLEAN, 默认值: False)")
    print("\n现在可以在创建任务时指定use_ocr=True来启用OCR模式")

