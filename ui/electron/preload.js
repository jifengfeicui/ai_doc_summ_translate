const { contextBridge, ipcRenderer } = require('electron')

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 对话框 API
  dialog: {
    openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),
    openDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
    saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options)
  },
  
  // 文件系统 API
  fs: {
    readFile: (filePath, encoding) => ipcRenderer.invoke('fs:readFile', filePath, encoding),
    writeFile: (filePath, data, encoding) => ipcRenderer.invoke('fs:writeFile', filePath, data, encoding),
    exists: (filePath) => ipcRenderer.invoke('fs:exists', filePath),
    stat: (filePath) => ipcRenderer.invoke('fs:stat', filePath),
    readdir: (dirPath) => ipcRenderer.invoke('fs:readdir', dirPath),
    scanDirectory: (dirPath, extensions) => ipcRenderer.invoke('fs:scanDirectory', dirPath, extensions)
  },
  
  // 应用 API
  app: {
    getPath: (name) => ipcRenderer.invoke('app:getPath', name),
    getVersion: () => ipcRenderer.invoke('app:getVersion')
  },
  
  // 窗口控制 API
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized')
  },
  
  // 判断是否在 Electron 环境中运行
  isElectron: true
})

// 暴露 Node.js 环境信息(只读)
contextBridge.exposeInMainWorld('nodeAPI', {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron
  }
})

