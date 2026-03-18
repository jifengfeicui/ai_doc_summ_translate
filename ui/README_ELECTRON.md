# 文档总结与翻译系统 - Electron 版本

这是基于 Vue 3 + Vite + Electron 的桌面应用程序。

## 项目结构

```
ui/
├── electron/              # Electron 主进程文件
│   ├── main.js           # Electron 主进程入口
│   └── preload.js        # 预加载脚本
├── src/                  # Vue 源代码
├── dist/                 # 构建输出目录
├── release/              # Electron 打包输出目录
├── build/                # 应用图标等资源
├── package.json          # 项目配置
└── vite.config.js        # Vite 配置
```

## 开发环境要求

- Node.js >= 16
- pnpm (推荐) 或 npm

## 安装依赖

```bash
cd ui
pnpm install
```

## 开发模式

### 方式一：使用根目录启动脚本（推荐）

在项目根目录下运行：
```bash
start_electron.bat
```

### 方式二：手动启动

```bash
cd ui

# 同时启动 Vite 开发服务器和 Electron
pnpm start

# 或分别启动
# 终端1: 启动 Vite 开发服务器
pnpm dev

# 终端2: 启动 Electron (等 Vite 启动后)
pnpm dev:electron
```

## 构建打包

### 构建所有平台
```bash
cd ui
pnpm run build:electron
```

### 构建 Windows 版本
```bash
cd ui
pnpm run build:win
```

或在项目根目录使用：
```bash
build_electron.bat
```

### 构建 macOS 版本
```bash
cd ui
pnpm run build:mac
```

### 构建 Linux 版本
```bash
cd ui
pnpm run build:linux
```

构建完成后，安装包将位于 `ui/release/` 目录下。

## Electron API

应用程序通过 `preload.js` 暴露了安全的 API 给渲染进程：

### 对话框 API
```javascript
// 打开文件选择对话框
const result = await window.electronAPI.dialog.openFile({
  filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
})

// 打开文件夹选择对话框
const result = await window.electronAPI.dialog.openDirectory()

// 保存文件对话框
const result = await window.electronAPI.dialog.saveFile({
  defaultPath: 'output.txt',
  filters: [{ name: 'Text Files', extensions: ['txt'] }]
})
```

### 文件系统 API
```javascript
// 读取文件
const result = await window.electronAPI.fs.readFile(filePath, 'utf8')

// 写入文件
const result = await window.electronAPI.fs.writeFile(filePath, data, 'utf8')

// 检查文件是否存在
const result = await window.electronAPI.fs.exists(filePath)
```

### 应用 API
```javascript
// 获取应用路径 (userData, temp, downloads 等)
const path = await window.electronAPI.app.getPath('userData')

// 获取应用版本
const version = await window.electronAPI.app.getVersion()
```

### 窗口控制 API
```javascript
// 最小化窗口
await window.electronAPI.window.minimize()

// 最大化/还原窗口
await window.electronAPI.window.maximize()

// 关闭窗口
await window.electronAPI.window.close()

// 检查是否最大化
const isMaximized = await window.electronAPI.window.isMaximized()
```

### 判断运行环境
```javascript
// 检查是否在 Electron 中运行
if (window.electronAPI?.isElectron) {
  // Electron 环境
} else {
  // 浏览器环境
}

// 获取平台信息
const platform = window.nodeAPI.platform  // 'win32', 'darwin', 'linux'
const versions = window.nodeAPI.versions  // node, chrome, electron 版本
```

## 配置说明

### package.json

- `main`: Electron 主进程入口文件
- `scripts`: 包含开发、构建、打包命令
- `build`: Electron Builder 配置

### vite.config.js

- `base: './'`: 使用相对路径以兼容 Electron
- `server.port`: 固定开发服务器端口为 5173
- `build`: 构建输出配置

## 图标配置

需要在 `build/` 目录下放置应用图标：

- Windows: `icon.ico` (256x256)
- macOS: `icon.icns` (512x512)
- Linux: `icon.png` (512x512)

可以使用在线工具如 [icoconvert.com](https://icoconvert.com/) 生成多平台图标。

## 注意事项

1. **开发模式**: 应用会加载 `http://localhost:5173` 并打开开发者工具
2. **生产模式**: 应用会加载打包后的 `dist/index.html`
3. **后端服务**: 需要确保后端 API 服务 (FastAPI) 在 `http://localhost:8000` 运行
4. **跨域问题**: 通过 Vite 的 proxy 配置解决开发环境的跨域问题
5. **安全性**: 使用 `contextIsolation` 和 `preload.js` 确保渲染进程安全

## 调试

- 开发模式下会自动打开 Chrome DevTools
- 主进程日志会输出到终端
- 渲染进程日志会显示在 DevTools Console 中

## 常见问题

### 1. 端口被占用
如果 5173 端口被占用，修改 `vite.config.js` 中的 `server.port` 和 `electron/main.js` 中的 URL。

### 2. 构建失败
确保已安装所有依赖，并且有足够的磁盘空间。Windows 上可能需要安装 Windows SDK。

### 3. 打包后应用无法启动
检查 `console.log` 输出，确保所有资源文件路径正确。

## 技术栈

- **框架**: Vue 3 + Vite
- **UI 库**: Element Plus
- **桌面框架**: Electron
- **打包工具**: Electron Builder
- **Markdown**: marked.js
- **代码高亮**: highlight.js

## License

MIT

