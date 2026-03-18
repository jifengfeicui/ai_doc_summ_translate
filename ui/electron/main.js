const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const fs = require('fs')

// 开发模式判断
const isDev = process.env.NODE_ENV !== 'production'

let mainWindow = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    frame: true,
    backgroundColor: '#ffffff',
    show: false,
    title: '文档总结与翻译系统'
  })

  // 窗口准备好后再显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  // 加载应用
  if (isDev) {
    // 开发模式下加载 Vite 开发服务器
    mainWindow.loadURL('http://localhost:5173')
    // 开发模式下自动打开开发者工具
    mainWindow.webContents.openDevTools()
  } else {
    // 生产模式下加载打包后的文件（不打开开发者工具）
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// 当 Electron 完成初始化时创建窗口
app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    // 在 macOS 上,点击 dock 图标时如果没有其他窗口打开,则重新创建一个窗口
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 当所有窗口关闭时退出应用(macOS 除外)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC 处理程序

// 选择文件
ipcMain.handle('dialog:openFile', async (event, options) => {
  const properties = options?.properties || ['openFile']
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: properties,
    filters: options?.filters || [
      { name: 'All Files', extensions: ['*'] }
    ]
  })
  
  if (!result.canceled && result.filePaths.length > 0) {
    // 支持多选
    if (properties.includes('multiSelections')) {
      return {
        canceled: false,
        filePaths: result.filePaths
      }
    } else {
      return {
        canceled: false,
        filePath: result.filePaths[0],
        fileName: path.basename(result.filePaths[0])
      }
    }
  }
  
  return { canceled: true }
})

// 选择文件夹
ipcMain.handle('dialog:openDirectory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  })
  
  if (!result.canceled && result.filePaths.length > 0) {
    return {
      canceled: false,
      directoryPath: result.filePaths[0]
    }
  }
  
  return { canceled: true }
})

// 保存文件
ipcMain.handle('dialog:saveFile', async (event, options) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: options?.defaultPath || 'untitled',
    filters: options?.filters || [
      { name: 'All Files', extensions: ['*'] }
    ]
  })
  
  if (!result.canceled) {
    return {
      canceled: false,
      filePath: result.filePath
    }
  }
  
  return { canceled: true }
})

// 读取文件
ipcMain.handle('fs:readFile', async (event, filePath, encoding = 'utf8') => {
  try {
    const data = await fs.promises.readFile(filePath, encoding)
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// 写入文件
ipcMain.handle('fs:writeFile', async (event, filePath, data, encoding = 'utf8') => {
  try {
    await fs.promises.writeFile(filePath, data, encoding)
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// 检查文件是否存在
ipcMain.handle('fs:exists', async (event, filePath) => {
  try {
    await fs.promises.access(filePath)
    return { exists: true }
  } catch {
    return { exists: false }
  }
})

// 获取文件/目录信息
ipcMain.handle('fs:stat', async (event, filePath) => {
  try {
    const stats = await fs.promises.stat(filePath)
    return {
      success: true,
      stats: {
        size: stats.size,
        isFile: stats.isFile(),
        isDirectory: stats.isDirectory(),
        createdTime: stats.birthtime,
        modifiedTime: stats.mtime
      }
    }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// 读取目录内容
ipcMain.handle('fs:readdir', async (event, dirPath) => {
  try {
    const entries = await fs.promises.readdir(dirPath, { withFileTypes: true })
    const result = entries.map(entry => ({
      name: entry.name,
      path: path.join(dirPath, entry.name),
      isFile: entry.isFile(),
      isDirectory: entry.isDirectory()
    }))
    return { success: true, entries: result }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// 递归扫描目录中的文件
ipcMain.handle('fs:scanDirectory', async (event, dirPath, extensions) => {
  const supportedExtensions = extensions || ['.pdf', '.doc', '.docx', '.ppt', '.pptx']
  const files = []
  
  async function scanRecursive(currentPath) {
    try {
      const entries = await fs.promises.readdir(currentPath, { withFileTypes: true })
      
      for (const entry of entries) {
        const fullPath = path.join(currentPath, entry.name)
        
        try {
          if (entry.isDirectory()) {
            // 递归扫描子目录
            await scanRecursive(fullPath)
          } else if (entry.isFile()) {
            const ext = path.extname(entry.name).toLowerCase()
            if (supportedExtensions.includes(ext)) {
              const stats = await fs.promises.stat(fullPath)
              files.push({
                path: fullPath,
                name: entry.name,
                type: ext,
                size: stats.size
              })
            }
          }
        } catch (error) {
          // 跳过无法访问的文件/目录
          console.error(`跳过文件: ${fullPath}, 错误: ${error.message}`)
        }
      }
    } catch (error) {
      console.error(`扫描目录失败: ${currentPath}, 错误: ${error.message}`)
    }
  }
  
  try {
    await scanRecursive(dirPath)
    return { success: true, files: files }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// 获取应用路径
ipcMain.handle('app:getPath', async (event, name) => {
  return app.getPath(name)
})

// 获取应用版本
ipcMain.handle('app:getVersion', async () => {
  return app.getVersion()
})

// 最小化窗口
ipcMain.handle('window:minimize', () => {
  if (mainWindow) {
    mainWindow.minimize()
  }
})

// 最大化/还原窗口
ipcMain.handle('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow.maximize()
    }
  }
})

// 关闭窗口
ipcMain.handle('window:close', () => {
  if (mainWindow) {
    mainWindow.close()
  }
})

// 检查窗口是否最大化
ipcMain.handle('window:isMaximized', () => {
  return mainWindow ? mainWindow.isMaximized() : false
})

