# 文档总结与翻译系统

一个基于FastAPI和Vue3的文档总结与翻译系统，支持PDF、Word和PowerPoint文件的处理。使用AI模型(Ollama)进行智能文档总结和翻译。

## 功能特点

- **文档总结**：自动提取文档的关键内容并生成详细的中文分析报告
- **文档翻译**：将英文文档翻译成流畅、专业的中文，支持断点续传
- **精细化翻译（新）**：多步骤深度翻译流程，包括文章理解、策略制定、翻译执行、质量评审和改进优化
- **多格式支持**：支持 PDF, DOCX, PPT, PPTX 等常见文档格式
- **文件管理**：上传、处理和下载文件
- **任务跟踪**：实时监控任务进度和状态
- **数据持久化**：使用SQLite存储任务信息

## 技术栈

### 后端
- Python 3.8+
- FastAPI - 高性能Web框架
- SQLAlchemy - ORM数据库操作
- Pydantic AI - AI模型集成
- Ollama - 本地AI模型服务

### 前端
- Vue 3 - 渐进式框架
- Element Plus - UI组件库
- Vite - 构建工具
- Axios - HTTP客户端
- **Electron** - 桌面应用框架 (新增)

## 项目结构

```
summ_translate/
├── app/                          # 应用核心代码
│   ├── __init__.py
│   ├── main.py                   # FastAPI主应用入口
│   ├── api/                      # API路由
│   │   ├── routes.py             # 路由定义
│   │   └── dependencies.py       # 依赖注入
│   ├── core/                     # 核心功能
│   │   ├── config.py             # 配置管理
│   │   └── database.py           # 数据库连接
│   ├── models/                   # 数据模型
│   │   └── task.py               # 任务相关模型
│   ├── services/                 # 业务服务
│   │   ├── summarize.py          # 文档总结服务
│   │   ├── translate.py          # 文档翻译服务
│   │   ├── fine_translate.py    # 精翻服务（新）
│   │   └── pdf_converter.py     # PDF转换服务
│   └── utils/                    # 工具函数
│       ├── ai_client.py          # AI客户端
│       ├── prompts.py            # 提示词管理
│       └── logger.py             # 日志工具
├── workspace/                    # 工作空间(所有生成数据统一存放)
│   ├── data/                     # 数据库文件
│   │   └── tasks.db              # SQLite数据库
│   ├── uploads/                  # 上传文件
│   ├── output/                   # 输出文件
│   ├── input/                    # 输入文件
│   ├── temp/                     # 临时文件
│   └── logs/                     # 日志文件
│       └── app.log               # 应用日志
├── ui/                           # Vue3前端项目
│   ├── src/                      # 前端源代码
│   ├── package.json              # 前端依赖
│   └── vite.config.js            # Vite配置
├── .env.example                  # 环境变量配置示例
├── .gitignore                    # Git忽略文件(workspace/已加入)
├── pyproject.toml                # Python项目配置
├── run.py                        # 启动脚本
└── README.md                     # 项目文档
```

## 安装与配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd summ_translate
```

### 2. 环境配置

复制环境变量配置示例文件:

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置AI模型服务:

```bash
# AI模型配置
AI_API_URL=http://your-ollama-server:11434
AI_MODEL_NAME=qwen3:30b-a3b-instruct-2507-fp16

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
```

### 3. 安装后端依赖

**方法一：使用 uv (推荐)**

```bash
# 安装 uv
pip install uv

# 创建虚拟环境
uv venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source .venv/bin/activate

# 安装依赖
uv pip install -e .
```

**方法二：使用 pip**

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source .venv/bin/activate

# 安装依赖
pip install -e .
```

### 4. 安装前端依赖

```bash
cd ui
pnpm install
# 或使用 npm
npm install
```

### 5. 配置 Ollama 服务

确保 Ollama 服务已启动并可访问。参考 [Ollama 官方文档](https://ollama.ai/) 进行安装和配置。

## 运行项目

### 🖥️ Electron 桌面应用 (推荐)

项目现已支持 Electron 桌面应用! 

**启动开发环境:**

```bash
# Windows
start_electron.bat

# 或手动启动
cd ui
pnpm start
```

**打包桌面应用:**

```bash
# Windows
build_electron.bat

# 或手动打包
cd ui
pnpm run build:win    # Windows 版本
pnpm run build:mac    # macOS 版本
pnpm run build:linux  # Linux 版本
```

详细说明请参考 [ELECTRON_SETUP.md](ELECTRON_SETUP.md)

---

### 🌐 Web 版本

#### 启动后端服务

**方法一：使用启动脚本 (推荐)**

```bash
python run.py
```

**方法二：使用批处理文件 (Windows)**

```bash
start_server.bat
```

**方法三：直接运行**

```bash
python -m app.main
```

后端服务将在 `http://localhost:8000` 启动。

API文档访问: `http://localhost:8000/docs`

#### 启动前端服务

**方法一：使用批处理文件 (Windows)**

```bash
start_frontend.bat
```

**方法二：手动启动**

```bash
cd ui
pnpm dev
# 或
npm run dev
```

前端服务将在 `http://localhost:5173` 启动。

## 使用方法

1. 访问前端界面 `http://localhost:5173`
2. 选择任务类型 (总结或翻译)
3. 上传文档文件 (PDF, DOCX, PPT, PPTX)
4. 等待处理完成 (可查看实时进度)
5. 下载处理结果

## API接口

### 创建任务

```http
POST /tasks/
Content-Type: multipart/form-data

file: <文件>
task_type: summarize | translate
```

### 获取任务列表

```http
GET /tasks/
```

### 获取任务详情

```http
GET /tasks/{task_id}
```

### 下载任务结果

```http
GET /tasks/{task_id}/download
```

### 精翻任务（新）

创建精翻任务：
```http
POST /files/{file_id}/fine-translate
Content-Type: application/json

{
  "task_type": "fine_translate",
  "target_audience": "有一定科学素养，对科技感兴趣的读者群体",
  "enable_review": true,
  "enable_refinement": true,
  "max_iterations": 2
}
```

**参数说明：**
- `target_audience`: 目标读者群体描述
- `enable_review`: 是否启用评审步骤（默认 false）
- `enable_refinement`: 是否启用改进步骤（默认 false）
- `max_iterations`: 最大改进迭代次数（默认 1）

详细使用说明请参考 [FINE_TRANSLATE_GUIDE.md](FINE_TRANSLATE_GUIDE.md)

## 开发指南

### 目录说明

- `app/` - 应用核心代码,包含API、服务、模型等
- `workspace/` - 工作空间,统一存放所有生成数据(自动创建,已加入.gitignore)
  - `data/` - 数据库文件
  - `uploads/` - 用户上传文件
  - `output/` - 处理结果文件
  - `input/` - 批处理输入文件
  - `temp/` - 临时文件
  - `logs/` - 日志文件
- `ui/` - Vue3前端项目

### 配置管理

所有配置统一在 `app/core/config.py` 中管理，支持:
- 环境变量
- .env 文件
- 默认值

### 日志系统

日志文件保存在 `logs/app.log`，同时输出到控制台。

### 添加新功能

1. 在 `app/services/` 中添加业务逻辑
2. 在 `app/api/routes.py` 中添加API路由
3. 更新前端界面 (如需要)

## 常见问题

### 1. 端口被占用

修改 `.env` 文件中的 `APP_PORT` 配置。

### 2. AI模型连接失败

检查 `.env` 文件中的 `AI_API_URL` 是否正确，确保 Ollama 服务正在运行。

### 3. 文件转换失败

确保已安装 LibreOffice 和 mineru 工具:

```bash
# 安装 mineru
pip install mineru
```

### 4. 数据库错误

删除 `workspace/data/tasks.db` 文件，重新启动服务将自动创建新数据库。

### 5. 清理工作空间

如需重置所有数据:
```bash
# Windows
Remove-Item -Recurse -Force workspace
# Linux/Mac  
rm -rf workspace
# 重启服务会自动重新创建目录
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.1.0 (2025-10-23)

- ✨ **新增 Electron 桌面应用支持**
- ✅ 创建 Electron 主进程和预加载脚本
- ✅ 添加文件对话框、文件系统等原生 API
- ✅ 配置 Vite 支持 Electron 构建
- ✅ 添加打包配置和启动脚本
- ✅ 提供 Electron API 工具类
- 📝 完善 Electron 开发文档

### v1.0.0 (2025-10-22)

- ✅ 重构项目结构，采用模块化设计
- ✅ 统一配置管理，支持环境变量
- ✅ 优化AI客户端，支持多种模型
- ✅ 改进日志系统
- ✅ 完善API文档
- ✅ 修复硬编码路径问题
