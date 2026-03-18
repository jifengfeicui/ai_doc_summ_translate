"""
文件处理工具函数
"""
import hashlib
from pathlib import Path
from typing import Optional


def calculate_file_md5(file_path: str, chunk_size: int = 8192) -> str:
    """
    计算文件的MD5哈希值
    
    Args:
        file_path: 文件路径
        chunk_size: 读取块大小,默认8KB
        
    Returns:
        32位小写MD5哈希字符串
    """
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            # 分块读取文件以支持大文件
            while chunk := f.read(chunk_size):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
    except Exception as e:
        raise Exception(f"计算文件MD5失败: {str(e)}")


def calculate_file_md5_from_upload(file_content: bytes) -> str:
    """
    计算上传文件内容的MD5哈希值
    
    Args:
        file_content: 文件内容(字节)
        
    Returns:
        32位小写MD5哈希字符串
    """
    return hashlib.md5(file_content).hexdigest()


def get_file_info(file_path: str) -> dict:
    """
    获取文件基本信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含文件名、大小、类型、MD5等信息的字典
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"路径不是文件: {file_path}")
    
    return {
        "file_name": path.name,
        "file_size": path.stat().st_size,
        "file_type": path.suffix.lower(),
        "file_md5": calculate_file_md5(str(path))
    }


