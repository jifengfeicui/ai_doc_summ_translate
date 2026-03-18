"""
启动脚本 - 运行FastAPI后端服务
"""
import sys
import uvicorn


def main():
    """主函数"""
    print("="*50)
    print("文档总结与翻译系统")
    print("="*50)
    
    # 检查依赖
    try:
        import fastapi
        import sqlalchemy
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请先安装依赖: uv pip install -e .")
        return
    
    # 启动服务
    try:
        from app.core.config import APP_HOST, APP_PORT
        
        print(f"\n✅ 工作空间: workspace/ (自动创建)")
        print(f"✅ 启动地址: {APP_HOST}:{APP_PORT}")
        print("\nAPI文档: http://localhost:8000/docs")
        print("="*50)
        
        uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=False)
        
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n可能的原因:")
        print("  1. 端口被占用 - 修改 .env 中的 APP_PORT")
        print("  2. 配置错误 - 检查 .env 文件")
        print("  3. 模块缺失 - 确保在项目根目录运行")


if __name__ == "__main__":
    main()

