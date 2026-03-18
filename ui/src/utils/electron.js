/**
 * Electron API 工具类
 * 提供统一的接口访问 Electron 功能,并在浏览器环境中提供降级方案
 */

// 检查是否在 Electron 环境中
export const isElectron = () => {
  return !!(window.electronAPI && window.electronAPI.isElectron)
}

// 检查是否在浏览器环境中
export const isBrowser = () => {
  return !isElectron()
}

/**
 * 对话框 API
 */
export const dialog = {
  /**
   * 打开文件选择对话框
   * @param {Object} options - 选项 { filters: [{ name, extensions }] }
   * @returns {Promise<{canceled: boolean, filePath?: string, fileName?: string}>}
   */
  async openFile(options = {}) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { canceled: true }
    }
    return window.electronAPI.dialog.openFile(options)
  },

  /**
   * 打开文件夹选择对话框
   * @returns {Promise<{canceled: boolean, directoryPath?: string}>}
   */
  async openDirectory() {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { canceled: true }
    }
    return window.electronAPI.dialog.openDirectory()
  },

  /**
   * 保存文件对话框
   * @param {Object} options - 选项 { defaultPath, filters }
   * @returns {Promise<{canceled: boolean, filePath?: string}>}
   */
  async saveFile(options = {}) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { canceled: true }
    }
    return window.electronAPI.dialog.saveFile(options)
  }
}

/**
 * 文件系统 API
 */
export const fs = {
  /**
   * 读取文件内容
   * @param {string} filePath - 文件路径
   * @param {string} encoding - 编码,默认 'utf8'
   * @returns {Promise<{success: boolean, data?: string, error?: string}>}
   */
  async readFile(filePath, encoding = 'utf8') {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { success: false, error: 'Not in Electron environment' }
    }
    return window.electronAPI.fs.readFile(filePath, encoding)
  },

  /**
   * 写入文件内容
   * @param {string} filePath - 文件路径
   * @param {string} data - 文件内容
   * @param {string} encoding - 编码,默认 'utf8'
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async writeFile(filePath, data, encoding = 'utf8') {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { success: false, error: 'Not in Electron environment' }
    }
    return window.electronAPI.fs.writeFile(filePath, data, encoding)
  },

  /**
   * 检查文件是否存在
   * @param {string} filePath - 文件路径
   * @returns {Promise<{exists: boolean}>}
   */
  async exists(filePath) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { exists: false }
    }
    return window.electronAPI.fs.exists(filePath)
  },

  /**
   * 获取文件/目录信息
   * @param {string} filePath - 文件路径
   * @returns {Promise<{success: boolean, stats?: object, error?: string}>}
   */
  async stat(filePath) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { success: false, error: 'Not in Electron environment' }
    }
    return window.electronAPI.fs.stat(filePath)
  },

  /**
   * 读取目录内容
   * @param {string} dirPath - 目录路径
   * @returns {Promise<{success: boolean, entries?: array, error?: string}>}
   */
  async readdir(dirPath) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { success: false, error: 'Not in Electron environment' }
    }
    return window.electronAPI.fs.readdir(dirPath)
  },

  /**
   * 递归扫描目录中的文件
   * @param {string} dirPath - 目录路径
   * @param {Array} extensions - 支持的扩展名数组,默认 ['.pdf', '.doc', '.docx', '.ppt', '.pptx']
   * @returns {Promise<{success: boolean, files?: array, error?: string}>}
   */
  async scanDirectory(dirPath, extensions) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return { success: false, error: 'Not in Electron environment' }
    }
    return window.electronAPI.fs.scanDirectory(dirPath, extensions)
  }
}

/**
 * 应用 API
 */
export const app = {
  /**
   * 获取应用路径
   * @param {string} name - 路径名称 (userData, temp, downloads, etc.)
   * @returns {Promise<string>}
   */
  async getPath(name) {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return ''
    }
    return window.electronAPI.app.getPath(name)
  },

  /**
   * 获取应用版本
   * @returns {Promise<string>}
   */
  async getVersion() {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return '0.0.0'
    }
    return window.electronAPI.app.getVersion()
  }
}

/**
 * 窗口控制 API
 */
export const windowControl = {
  /**
   * 最小化窗口
   */
  async minimize() {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return
    }
    return window.electronAPI.window.minimize()
  },

  /**
   * 最大化/还原窗口
   */
  async maximize() {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return
    }
    return window.electronAPI.window.maximize()
  },

  /**
   * 关闭窗口
   */
  async close() {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return
    }
    return window.electronAPI.window.close()
  },

  /**
   * 检查窗口是否最大化
   * @returns {Promise<boolean>}
   */
  async isMaximized() {
    if (!isElectron()) {
      console.warn('Electron API not available in browser mode')
      return false
    }
    return window.electronAPI.window.isMaximized()
  }
}

/**
 * 获取平台信息
 * @returns {string} 'win32', 'darwin', 'linux' 或 'browser'
 */
export const getPlatform = () => {
  if (isElectron()) {
    return window.nodeAPI.platform
  }
  // 在浏览器中尝试检测平台
  const userAgent = navigator.userAgent.toLowerCase()
  if (userAgent.includes('win')) return 'win32'
  if (userAgent.includes('mac')) return 'darwin'
  if (userAgent.includes('linux')) return 'linux'
  return 'browser'
}

/**
 * 获取版本信息
 * @returns {Object} { node, chrome, electron }
 */
export const getVersions = () => {
  if (isElectron()) {
    return window.nodeAPI.versions
  }
  return {
    node: 'N/A',
    chrome: 'N/A',
    electron: 'N/A'
  }
}

export default {
  isElectron,
  isBrowser,
  dialog,
  fs,
  app,
  windowControl,
  getPlatform,
  getVersions
}

