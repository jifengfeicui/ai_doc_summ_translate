import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('响应错误:', error)
    return Promise.reject(error)
  }
)

// 文件相关API
export const fileApi = {
  // 上传文件
  uploadFile(formData) {
    return api.post('/files/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 注册本地文件 (Electron 使用)
  registerLocalFile(filePath) {
    return api.post('/files/local', {
      file_path: filePath
    })
  },
  
  // 批量注册本地文件 (Electron 使用)
  registerLocalFilesBatch(filePaths) {
    return api.post('/files/local/batch', filePaths)
  },
  
  // 获取文件列表
  getFiles() {
    return api.get('/files/')
  },
  
  // 获取文件详情
  getFileDetail(fileId) {
    return api.get(`/files/${fileId}`)
  },
  
  // 删除文件
  deleteFile(fileId) {
    return api.delete(`/files/${fileId}`)
  },
  
  // 为文件创建任务
  createTask(fileId, taskType, useOcr = false) {
    return api.post(`/files/${fileId}/tasks`, {
      task_type: taskType,
      use_ocr: useOcr
    })
  },
  
  // 批量为文件创建任务
  createTasksBatch(fileIds, taskType, useOcr = false) {
    return api.post('/files/batch/tasks', {
      file_ids: fileIds,
      task_type: taskType,
      use_ocr: useOcr
    })
  }
}

// 任务相关API
export const taskApi = {
  // 获取任务列表（分页）
  getTasks(page = 1, pageSize = 20, status = '') {
    return api.get(`/tasks/?page=${page}&page_size=${pageSize}&status=${status}`)
  },
  
  // 获取任务详情
  getTaskDetail(taskId) {
    return api.get(`/tasks/${taskId}`)
  },
  
  // 重试任务
  retryTask(taskId) {
    return api.post(`/tasks/${taskId}/retry`)
  },
  
  // 停止任务
  stopTask(taskId) {
    return api.post(`/tasks/${taskId}/stop`)
  },
  
  // 强制停止任务
  forceStopTask(taskId) {
    return api.post(`/tasks/${taskId}/force-stop`)
  },
  
  // 删除任务
  deleteTask(taskId) {
    return api.delete(`/tasks/${taskId}`)
  },
  
  // 批量删除任务
  deleteTasksBatch(taskIds) {
    return api.post('/tasks/batch/delete', taskIds)
  },
  
  // 下载任务结果
  downloadTaskResult(taskId) {
    window.location.href = `/api/tasks/${taskId}/download`
  },
  
  // 获取任务输出内容（用于预览）
  getTaskContent(taskId) {
    return api.get(`/tasks/${taskId}/content`)
  }
}

// 文件内容相关API
export const contentApi = {
  // 获取文件的原始 Markdown 内容
  getFileMdContent(fileId) {
    return api.get(`/files/${fileId}/md-content`)
  }
}

// 工作区相关API
export const workspaceApi = {
  createWorkspace(name, description) {
    return api.post('/workspaces/', { name, description })
  },
  getWorkspaces() {
    return api.get('/workspaces/')
  },
  getWorkspaceDetail(workspaceId, page = 1, pageSize = 20) {
    return api.get(`/workspaces/${workspaceId}?page=${page}&page_size=${pageSize}`)
  },
  updateWorkspace(workspaceId, name, description) {
    return api.put(`/workspaces/${workspaceId}`, { name, description })
  },
  deleteWorkspace(workspaceId) {
    return api.delete(`/workspaces/${workspaceId}`)
  },
  addFilesToWorkspace(workspaceId, fileIds) {
    return api.post(`/workspaces/${workspaceId}/files`, { file_ids: fileIds })
  },
  removeFilesFromWorkspace(workspaceId, fileIds) {
    return api.delete(`/workspaces/${workspaceId}/files`, { data: { file_ids: fileIds } })
  },
  scanFolder(workspaceId, folderPath) {
    return api.post(`/workspaces/${workspaceId}/scan-folder`, { folder_path: folderPath })
  },
  createWorkspaceTasks(workspaceId, taskType, useOcr = false, duplicateHandling = 'skip') {
    return api.post(`/workspaces/${workspaceId}/tasks/${taskType}`, {
      task_type: taskType,
      use_ocr: useOcr,
      duplicate_handling: duplicateHandling
    })
  },
  exportCsv(workspaceId) {
    window.location.href = `/api/workspaces/${workspaceId}/export-csv`
  }
}

export default api
