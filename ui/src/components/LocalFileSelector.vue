<template>
  <div class="local-file-selector">
      <!-- Electron 环境 - 本地文件选择 -->
      <div v-if="isElectronEnv" class="electron-mode">
        <el-space direction="vertical" :size="16" style="width: 100%">
          <!-- 页面标题 -->
          <div class="page-title">
            <h2>文件选择与任务创建</h2>
            <el-tag type="success" size="large">
              <el-icon style="margin-right: 4px;"><FolderOpened /></el-icon>
              桌面模式
            </el-tag>
          </div>
          
          <!-- 选择操作按钮 -->
          <el-space wrap>
            <el-button 
              type="primary" 
              :icon="FolderOpened" 
              @click="selectFolder"
              :loading="registering">
              选择文件夹
            </el-button>
            <el-button 
              type="success" 
              :icon="Document" 
              @click="selectFiles"
              :loading="registering">
              选择文件
            </el-button>
          </el-space>

          <!-- 注册成功提示 -->
          <el-alert 
            v-if="recentlyRegistered.length > 0"
            title="文件已成功添加到系统" 
            type="success" 
            :closable="false"
            show-icon>
            <template #default>
              <p>刚刚添加了 {{ recentlyRegistered.length }} 个文件：</p>
              <ul style="margin: 8px 0 0 20px; padding: 0;">
                <li v-for="file in recentlyRegistered.slice(0, 5)" :key="file.id">
                  {{ file.file_name }}
                  <el-tag :type="getFileTypeTag(file.file_type)" size="small" style="margin-left: 8px;">
                    {{ file.file_type }}
                  </el-tag>
                </li>
                <li v-if="recentlyRegistered.length > 5">
                  ... 还有 {{ recentlyRegistered.length - 5 }} 个文件
                </li>
              </ul>
              <div style="margin-top: 12px;">
                <el-button type="primary" size="small" @click="goToFileList">
                  前往文件列表创建任务
                </el-button>
                <el-button size="small" @click="clearRecentList">
                  清除列表
                </el-button>
              </div>
            </template>
          </el-alert>

          <!-- 提示信息 -->
          <el-alert 
            v-if="recentlyRegistered.length === 0"
            title="使用说明" 
            type="info" 
            :closable="false">
            <template #default>
              <p><strong>工作流程：</strong></p>
              <ol style="margin: 8px 0 0 20px; padding: 0;">
                <li>点击"选择文件夹"或"选择文件"按钮添加文件</li>
                <li>文件会被复制到项目目录，避免原文件被移动或删除</li>
                <li>在列表中勾选需要处理的文件</li>
                <li>选择任务类型（总结或翻译）并创建任务</li>
                <li>任务完成后，可以在"文件列表"页面查看所有文件</li>
              </ol>
              <p style="margin-top: 12px;"><strong>支持的文件格式：</strong></p>
              <ul style="margin: 4px 0 0 20px; padding: 0;">
                <li>PDF 文件 (.pdf)</li>
                <li>Word 文档 (.doc, .docx)</li>
                <li>PowerPoint 演示文稿 (.ppt, .pptx)</li>
                <li>Markdown 文档 (.md) - 无需转换，直接可用</li>
              </ul>
              <p style="margin-top: 12px;"><strong>智能去重：</strong></p>
              <ul style="margin: 4px 0 0 20px; padding: 0;">
                <li>系统会自动识别相同文件（通过MD5），避免重复添加</li>
              </ul>
            </template>
          </el-alert>
        </el-space>
      </div>

      <!-- 浏览器环境 - 传统上传 -->
      <div v-else class="browser-mode">
        <el-alert 
          title="浏览器模式限制" 
          type="warning" 
          :closable="false"
          show-icon>
          <template #default>
            本地文件选择功能仅在 Electron 桌面应用中可用。
            <br>
            请下载并使用桌面版本,或使用传统的文件上传方式。
          </template>
        </el-alert>
      </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  FolderOpened, 
  Document
} from '@element-plus/icons-vue'
import { isElectron, dialog, fs } from '@/utils/electron'
import { fileApi } from '@/api'

const router = useRouter()

const isElectronEnv = ref(false)
const registering = ref(false)
const recentlyRegistered = ref([])

// 支持的文件扩展名
const SUPPORTED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.md']

onMounted(() => {
  isElectronEnv.value = isElectron()
})

// 选择文件夹
const selectFolder = async () => {
  try {
    const result = await dialog.openDirectory()
    if (!result.canceled) {
      await scanDirectoryAndRegister(result.directoryPath)
    }
  } catch (error) {
    console.error('选择文件夹失败:', error)
    ElMessage.error('选择文件夹失败')
  }
}

// 选择文件
const selectFiles = async () => {
  try {
    const result = await dialog.openFile({
      filters: [
        { name: 'PDF 文件', extensions: ['pdf'] },
        { name: 'Word 文档', extensions: ['doc', 'docx'] },
        { name: 'PowerPoint', extensions: ['ppt', 'pptx'] },
        { name: 'Markdown 文档', extensions: ['md'] },
        { name: '所有支持的文件', extensions: ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'md'] }
      ],
      properties: ['openFile', 'multiSelections']
    })
    
    if (!result.canceled && result.filePaths) {
      await registerFilesToSystem(result.filePaths)
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('选择文件失败')
  }
}

// 扫描目录并注册文件
const scanDirectoryAndRegister = async (dirPath) => {
  try {
    registering.value = true
    ElMessage.info('正在扫描文件夹...')
    
    const result = await fs.scanDirectory(dirPath, SUPPORTED_EXTENSIONS)
    
    if (!result.success) {
      throw new Error(result.error)
    }
    
    const files = result.files || []
    
    if (files.length === 0) {
      ElMessage.warning('未找到支持的文档文件')
      return
    }
    
    // 注册文件到系统
    const filePaths = files.map(f => f.path)
    await registerFilesToSystem(filePaths)
    
  } catch (error) {
    console.error('扫描文件夹失败:', error)
    ElMessage.error(`扫描文件夹失败: ${error.message}`)
  } finally {
    registering.value = false
  }
}

// 注册文件到系统（复制文件并创建记录）
const registerFilesToSystem = async (filePaths) => {
  try {
    registering.value = true
    ElMessage.info(`正在注册 ${filePaths.length} 个文件到系统...`)
    
    // 调用批量注册 API
    const result = await fileApi.registerLocalFilesBatch(filePaths)
    
    console.log('批量注册返回结果:', result)
    
    if (!result.files || result.files.length === 0) {
      ElMessage.warning('没有文件被成功注册')
      console.warn('注册结果为空:', result)
      return
    }
    
    // 保存最近注册的文件列表
    recentlyRegistered.value = result.files
    
    console.log('已注册文件:', result.files)
    ElMessage.success(`成功添加 ${result.files.length} 个文件到系统，文件ID: ${result.files.map(f => f.id).join(', ')}`)
    
  } catch (error) {
    console.error('注册文件失败:', error)
    ElMessage.error(`注册文件失败: ${error.message || '未知错误'}`)
  } finally {
    registering.value = false
  }
}

// 前往文件列表
const goToFileList = () => {
  router.push('/files')
}

// 清除最近注册列表
const clearRecentList = () => {
  recentlyRegistered.value = []
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 获取文件类型标签颜色
const getFileTypeTag = (type) => {
  const tagMap = {
    '.pdf': 'danger',
    '.doc': 'primary',
    '.docx': 'primary',
    '.ppt': 'success',
    '.pptx': 'success',
    '.md': 'warning'
  }
  return tagMap[type] || 'info'
}

</script>

<style scoped>
.local-file-selector {
  width: 100%;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.electron-mode {
  width: 100%;
}

.page-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid #e6e6e6;
}

.page-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
  color: #303133;
}

.file-list-container {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
  background: #fff;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
  font-weight: 600;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.browser-mode {
  padding: 20px 0;
}
</style>

