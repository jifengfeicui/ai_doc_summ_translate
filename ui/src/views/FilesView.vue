<template>
  <div class="files-view">
    <div class="view-header">
      <div class="header-actions">
        <el-button 
          type="success" 
          @click="batchCreateTask('summarize')"
          :disabled="selectedFiles.length === 0"
          :loading="batchLoading">
          批量总结
        </el-button>
        <el-button 
          type="primary" 
          @click="batchCreateTask('translate')"
          :disabled="selectedFiles.length === 0"
          :loading="batchLoading">
          批量翻译
        </el-button>
        <el-divider direction="vertical" />
        <el-switch
          v-model="useOcr"
          active-text="启用OCR"
          inactive-text="关闭OCR"
        />
        <el-tooltip 
          content="启用OCR模式处理扫描版PDF或图片型PDF，处理时间会较长"
          placement="bottom"
        >
          <el-icon style="cursor: help; color: #909399;">
            <QuestionFilled />
          </el-icon>
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          @change="handleAutoRefreshChange"
        />
        <el-button 
          type="primary" 
          :icon="Refresh" 
          @click="fetchFiles"
          :loading="loading">
          刷新
        </el-button>
      </div>
    </div>
    
    <el-table 
      :data="files" 
      style="width: 100%" 
      v-loading="loading"
      element-loading-text="加载中..."
      stripe
      border
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="file_type" label="类型" width="100">
        <template #default="scope">
          <el-tag :type="getFileTypeTag(scope.row.file_type)" size="small">
            {{ scope.row.file_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_size" label="大小" width="120">
        <template #default="scope">
          {{ formatFileSize(scope.row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column prop="md_converted" label="MD转换" width="120">
        <template #default="scope">
          <el-tag v-if="scope.row.md_converted" type="success">已转换</el-tag>
          <el-tag v-else type="info">未转换</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="upload_time" label="上传时间" width="180">
        <template #default="scope">
          {{ formatDateTime(scope.row.upload_time) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button 
            size="small" 
            @click="viewFileDetail(scope.row.id)"
          >
            查看详情
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="deleteFile(scope.row.id, scope.row.file_name)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, QuestionFilled } from '@element-plus/icons-vue'
import { fileApi } from '@/api'

const router = useRouter()
const files = ref([])
const loading = ref(false)
const selectedFiles = ref([])
const batchLoading = ref(false)
const autoRefresh = ref(true)
const useOcr = ref(false)
const tableRef = ref(null)

// 处理表格多选变化
const handleSelectionChange = (selection) => {
  selectedFiles.value = selection
}

// 处理自动刷新开关变化
const handleAutoRefreshChange = (value) => {
  if (value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

// 批量创建任务
const batchCreateTask = async (taskType) => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要处理的文件')
    return
  }
  
  const fileIds = selectedFiles.value.map(file => file.id)
  const taskTypeText = taskType === 'summarize' ? '总结' : '翻译'
  const ocrText = useOcr.value ? ' (启用OCR)' : ''
  
  console.log('批量创建任务请求:', { fileIds, taskType, useOcr: useOcr.value })
  
  try {
    batchLoading.value = true
    
    const response = await fileApi.createTasksBatch(fileIds, taskType, useOcr.value)
    console.log('批量创建任务响应:', response)
    
    const createdCount = response.created_tasks?.length || 0
    const skippedCount = response.skipped_files?.length || 0
    const errorCount = response.errors?.length || 0
    
    // 构建提示消息
    let message = `批量${taskTypeText}任务创建完成${ocrText}：`
    if (createdCount > 0) {
      message += `成功创建 ${createdCount} 个任务`
    }
    if (skippedCount > 0) {
      message += `，跳过 ${skippedCount} 个文件（已有任务）`
    }
    if (errorCount > 0) {
      message += `，失败 ${errorCount} 个`
    }
    
    if (createdCount > 0) {
      ElMessage.success(message)
    } else if (skippedCount > 0 && errorCount === 0) {
      ElMessage.warning(message)
    } else {
      ElMessage.error(message)
    }
    
    // 显示跳过和错误的详细信息
    if (skippedCount > 0) {
      const skippedInfo = response.skipped_files
        .map(f => `${f.file_name}: ${f.reason}`)
        .join('\n')
      console.log('跳过的文件:\n' + skippedInfo)
    }
    if (errorCount > 0) {
      const errorInfo = response.errors.join('\n')
      console.error('失败的文件:\n' + errorInfo)
    }
    
    // 刷新文件列表并清空选中状态
    await fetchFiles()
    selectedFiles.value = []
    
  } catch (error) {
    console.error(`批量创建${taskTypeText}任务失败:`, error)
    ElMessage.error(`批量创建${taskTypeText}任务失败`)
  } finally {
    batchLoading.value = false
  }
}

// 获取文件列表
const fetchFiles = async () => {
  loading.value = true
  try {
    const response = await fileApi.getFiles()
    console.log('获取文件列表响应:', response)
    console.log('文件数量:', response.files?.length || 0)
    files.value = response.files
  } catch (error) {
    console.error('获取文件列表失败:', error)
    ElMessage.error('获取文件列表失败')
  } finally {
    loading.value = false
  }
}

// 查看文件详情
const viewFileDetail = (fileId) => {
  router.push(`/files/${fileId}`)
}

// 删除文件
const deleteFile = async (fileId, fileName) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件 "${fileName}" 吗？这将同时删除该文件的所有任务。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await fileApi.deleteFile(fileId)
    ElMessage.success('文件删除成功')
    // 刷新文件列表
    await fetchFiles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文件失败:', error)
      ElMessage.error('删除文件失败')
    }
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 格式化日期时间
const formatDateTime = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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

// 定时刷新文件列表
let refreshInterval = null
const startAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  refreshInterval = setInterval(() => {
    fetchFiles()
  }, 10000) // 每10秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

onMounted(() => {
  fetchFiles()
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

// 组件卸载时清除定时器
onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.files-view {
  width: 100%;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.view-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 16px 20px;
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.el-divider--vertical {
  height: 1.5em;
  margin: 0 8px;
}
</style>
