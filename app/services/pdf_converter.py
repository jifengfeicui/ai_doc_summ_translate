"""
PDF文档转换服务
支持 PDF, DOCX, PPT 等格式转换为 Markdown
"""
import shutil
import subprocess
from pathlib import Path

from app.core.config import TEMP_DIR, OUTPUT_DIR
from app.utils.logger import logger


def convert_pdf_to_md(pdf_path: Path, md_path: Path, use_ocr: bool = False) -> bool:
    """
    将PDF文档转换为Markdown格式
    
    Args:
        pdf_path: PDF文件路径
        md_path: 输出Markdown文件路径
        use_ocr: 是否使用OCR模式
        
    Returns:
        转换是否成功
    """
    temp_dir = Path(TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if not pdf_path.is_file():
        logger.error(f"文件不存在: {pdf_path}")
        return False
    
    ext = pdf_path.suffix.lower()
    pdf_output = None
    
    try:
        if ext == ".pdf":
            # 直接复制 PDF
            pdf_output = temp_dir / pdf_path.name
            shutil.copy(pdf_path, pdf_output)
            logger.info(f"复制PDF文件: {pdf_path} → {pdf_output}")
        
        elif ext in [".docx", ".ppt", ".pptx"]:
            # 转换 DOCX/PPT → PDF
            pdf_output = temp_dir / f"{pdf_path.stem}.pdf"
            try:
                libreoffice_convert(pdf_path, temp_dir)
                logger.info(f"转换为PDF: {pdf_path} → {pdf_output}")
            except Exception as e:
                logger.error(f"转换PDF失败: {pdf_path}, 错误: {e}")
                return False
        
        if pdf_output and pdf_output.exists():
            # 使用 mineru 转换 PDF → Markdown
            output_dir = Path(OUTPUT_DIR)
            cmd = ["mineru", "-p", str(pdf_output), "-o", str(output_dir)]
            
            # 如果使用OCR模式，添加-m ocr参数
            if use_ocr:
                cmd.extend(["-m", "ocr"])
                logger.info("使用OCR模式进行PDF转换")
            
            try:
                subprocess.run(cmd, check=True, shell=True)
                
                # 如果使用了OCR模式，输出目录会是 output_dir / pdf_stem / "ocr"
                # 需要将其重命名为 output_dir / pdf_stem / "auto"
                if use_ocr:
                    pdf_stem = pdf_output.stem
                    ocr_dir = output_dir / pdf_stem / "ocr"
                    auto_dir = output_dir / pdf_stem / "auto"
                    
                    if ocr_dir.exists():
                        # 如果auto目录已存在，先删除
                        if auto_dir.exists():
                            shutil.rmtree(auto_dir)
                        # 重命名ocr目录为auto
                        ocr_dir.rename(auto_dir)
                        logger.info(f"OCR输出目录重命名: {ocr_dir} → {auto_dir}")
                    else:
                        logger.warning(f"OCR输出目录不存在: {ocr_dir}")
                
                logger.info(f"PDF转Markdown成功: {pdf_output} → {md_path}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"PDF转Markdown失败: {pdf_output}, 错误: {e}")
                return False
    
    except Exception as e:
        logger.error(f"转换过程异常: {e}")
        return False
    
    return False


def libreoffice_convert(input_path: Path, output_dir: Path):
    """
    使用 LibreOffice 转换文档为 PDF
    
    Args:
        input_path: 输入文件路径
        output_dir: 输出目录
    """
    cmd = [
        "soffice.exe",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(output_dir),
        str(input_path)
    ]
    subprocess.run(cmd, check=True)

