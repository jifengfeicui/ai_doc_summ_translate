<template>
  <div class="container">
    <div class="page-header">
      <h2>文件详情</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>
    
    <template v-else-if="file">
      <!-- 文件基本信息 -->
      <div class="card">
        <h3>文件信息</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件ID">{{ file.id }}</el-descriptions-item>
          <el-descriptions-item label="文件名">{{ file.file_name }}</el-descriptions-item>
          <el-descriptions-item label="文件类型">{{ file.file_type }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(file.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ formatDateTime(file.upload_time) }}</el-descriptions-item>
          <el-descriptions-item label="Markdown转换状态">
            <el-tag v-if="file.md_converted" type="success">已转换</el-tag>
            <el-tag v-else type="info">未转换</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="操作" v-if="file.md_converted">
            <el-button size="small" type="primary" @click="previewMarkdown">
              预览 Markdown
            </el-button>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <!-- 创建任务 -->
      <div class="card">
        <h3>创建任务</h3>
        <div class="task-creation">
          <div class="ocr-option">
            <el-switch
              v-model="useOcr"
              active-text="启用OCR"
              inactive-text="关闭OCR"
            />
            <el-tooltip 
              content="启用OCR模式处理扫描版PDF或图片型PDF，处理时间会较长"
              placement="right"
            >
              <el-icon style="cursor: help; color: #909399; margin-left: 8px;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </div>
          <div class="task-actions">
            <el-button 
              type="success" 
              @click="createTask('summarize')"
              :loading="creatingTask === 'summarize'"
              :disabled="hasActiveTask('summarize')"
            >
              {{ hasActiveTask('summarize') ? '总结任务进行中' : '创建总结任务' }}
            </el-button>
            <el-button 
              type="primary" 
              @click="createTask('translate')"
              :loading="creatingTask === 'translate'"
              :disabled="hasActiveTask('translate')"
            >
              {{ hasActiveTask('translate') ? '翻译任务进行中' : '创建翻译任务' }}
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 任务列表 -->
      <div class="card">
        <h3>任务列表</h3>
        <el-table 
          :data="file.tasks" 
          style="width: 100%"
          v-if="file.tasks && file.tasks.length > 0"
        >
          <el-table-column prop="id" label="任务ID" width="100" />
          <el-table-column prop="task_type" label="任务类型" width="120">
            <template #default="scope">
              <el-tag v-if="scope.row.task_type === 'summarize'" type="success">总结</el-tag>
              <el-tag v-else-if="scope.row.task_type === 'translate'" type="primary">翻译</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="140">
            <template #default="scope">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <el-tag v-if="scope.row.status === 'completed'" type="success">已完成</el-tag>
                <el-tag v-else-if="scope.row.status === 'processing'" type="warning">处理中</el-tag>
                <el-tag v-else-if="scope.row.status === 'pending'" type="info">等待中</el-tag>
                <el-tag v-else-if="scope.row.status === 'cancelled'" type="warning">已取消</el-tag>
                <el-tag v-else-if="scope.row.status === 'failed'" type="danger">失败</el-tag>
                <el-tag v-if="scope.row.stop_requested" type="warning" size="small">停止中</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="progress" label="进度" width="200">
            <template #default="scope">
              <el-progress 
                :percentage="scope.row.progress" 
                :status="getProgressStatus(scope.row.status)"
              />
              <div v-if="scope.row.task_type === 'translate' && scope.row.total_paragraphs > 0" class="paragraph-info">
                第 {{ scope.row.current_paragraph }}/{{ scope.row.total_paragraphs }} 段
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="420">
            <template #default="scope">
              <el-space wrap size="small">
                <!-- 停止按钮 -->
                <el-button 
                  v-if="scope.row.status === 'processing' && !scope.row.stop_requested"
                  size="small" 
                  type="warning" 
                  @click="stopTask(scope.row.id)"
                >
                  停止
                </el-button>
                <!-- 强制停止按钮 -->
                <el-button 
                  v-if="scope.row.status === 'processing' && scope.row.stop_requested"
                  size="small" 
                  type="danger" 
                  @click="forceStopTask(scope.row.id)"
                >
                  强制停止
                </el-button>
                <!-- 查看按钮 -->
                <el-button 
                  size="small" 
                  @click="viewTaskDetail(scope.row.id)"
                >
                  查看
                </el-button>
                <!-- 预览按钮 -->
                <el-button 
                  size="small" 
                  type="success" 
                  @click="previewTaskResult(scope.row.id)"
                  :disabled="scope.row.status !== 'completed'"
                >
                  预览
                </el-button>
                <!-- 下载按钮 -->
                <el-button 
                  size="small" 
                  type="primary" 
                  @click="downloadResult(scope.row.id)"
                  :disabled="scope.row.status !== 'completed'"
                >
                  下载
                </el-button>
                <!-- 重试按钮 -->
                <el-button 
                  v-if="['failed', 'cancelled'].includes(scope.row.status)"
                  size="small" 
                  type="warning" 
                  @click="retryTask(scope.row.id)"
                >
                  重试
                </el-button>
                <!-- 删除按钮 -->
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="deleteTask(scope.row.id, scope.row.task_type)"
                  :disabled="scope.row.status === 'processing' && !scope.row.stop_requested"
                >
                  删除
                </el-button>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无任务" />
      </div>
    </template>
    
    <div v-else class="error-container">
      <el-empty description="未找到文件信息" />
    </div>

    <!-- Markdown 预览器 -->
    <MarkdownViewer
      v-model="showMarkdownViewer"
      :title="markdownTitle"
      :content="markdownContent"
      :file-name="markdownFileName"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { fileApi, taskApi, contentApi } from '@/api'
import MarkdownViewer from '@/components/MarkdownViewer.vue'

const route = useRoute()
const router = useRouter()
const fileId = computed(() => route.params.id)
const file = ref(null)
const loading = ref(false)
const creatingTask = ref(null)
const useOcr = ref(false)

// Markdown 预览相关
const showMarkdownViewer = ref(false)
const markdownContent = ref('')
const markdownFileName = ref('')
const markdownTitle = ref('')

// 获取文件详情
const fetchFileDetail = async () => {
  loading.value = true
  try {
    const response = await fileApi.getFileDetail(fileId.value)
    file.value = response
  } catch (error) {
    console.error('获取文件详情失败:', error)
    ElMessage.error('获取文件详情失败')
  } finally {
    loading.value = false
  }
}

// 检查是否有活跃的任务
const hasActiveTask = (taskType) => {
  if (!file.value || !file.value.tasks) return false
  return file.value.tasks.some(task => 
    task.task_type === taskType && 
    (task.status === 'pending' || task.status === 'processing')
  )
}

// 创建任务
const createTask = async (taskType) => {
  creatingTask.value = taskType
  const taskTypeText = taskType === 'summarize' ? '总结' : '翻译'
  const ocrText = useOcr.value ? ' (启用OCR)' : ''
  
  try {
    await fileApi.createTask(fileId.value, taskType, useOcr.value)
    ElMessage.success(`${taskTypeText}任务创建成功${ocrText}`)
    // 刷新文件详情
    await fetchFileDetail()
  } catch (error) {
    console.error('创建任务失败:', error)
    ElMessage.error(error.response?.data?.detail || '创建任务失败')
  } finally {
    creatingTask.value = null
  }
}

// 查看任务详情
const viewTaskDetail = (taskId) => {
  router.push(`/tasks/${taskId}`)
}

// 下载任务结果
const downloadResult = (taskId) => {
  taskApi.downloadTaskResult(taskId)
}

// 预览原始 Markdown
const previewMarkdown = async () => {
  try {
    const response = await contentApi.getFileMdContent(fileId.value)
    markdownContent.value = response.content
    markdownFileName.value = response.file_name
    markdownTitle.value = `原始 Markdown - ${file.value.file_name}`
    showMarkdownViewer.value = true
  } catch (error) {
    console.error('获取 Markdown 内容失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取 Markdown 内容失败')
  }
}

// 预览任务结果
const previewTaskResult = async (taskId) => {
  try {
    const response = await taskApi.getTaskContent(taskId)
    markdownContent.value = response.content
    markdownFileName.value = response.file_name
    markdownTitle.value = `任务结果 - ${response.file_name}`
    showMarkdownViewer.value = true
  } catch (error) {
    console.error('获取任务结果内容失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取任务结果内容失败')
  }
}

// 停止任务
const stopTask = async (taskId) => {
  try {
    await ElMessageBox.confirm(
      '确定要停止这个任务吗? 已完成的部分会被保存，可以稍后重试继续。',
      '确认停止',
      {
        type: 'warning',
        confirmButtonText: '停止',
        cancelButtonText: '取消'
      }
    )
    
    await taskApi.stopTask(taskId)
    ElMessage.success('停止请求已发送，任务将在当前段落完成后停止')
    await fetchFileDetail()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '停止任务失败')
    }
  }
}

// 强制停止任务
const forceStopTask = async (taskId) => {
  try {
    await ElMessageBox.confirm(
      '强制停止会立即终止任务，可能导致部分数据丢失。确定要强制停止吗?',
      '确认强制停止',
      {
        type: 'error',
        confirmButtonText: '强制停止',
        cancelButtonText: '取消'
      }
    )
    
    await taskApi.forceStopTask(taskId)
    ElMessage.success('任务已强制停止')
    await fetchFileDetail()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('强制停止任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '强制停止任务失败')
    }
  }
}

// 重试任务
const retryTask = async (taskId) => {
  try {
    await taskApi.retryTask(taskId)
    ElMessage.success('任务已重新提交')
    // 刷新文件详情
    await fetchFileDetail()
  } catch (error) {
    console.error('重试任务失败:', error)
    ElMessage.error('重试任务失败')
  }
}

// 删除任务
const deleteTask = async (taskId, taskType) => {
  const taskTypeText = taskType === 'summarize' ? '总结' : 
                       taskType === 'translate' ? '翻译' : 
                       taskType === 'fine_translate' ? '精翻' : '该'
  
  try {
    await ElMessageBox.confirm(
      `确定要删除这个${taskTypeText}任务吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
    
    await taskApi.deleteTask(taskId)
    ElMessage.success(`${taskTypeText}任务已删除`)
    // 刷新文件详情
    await fetchFileDetail()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除任务失败')
    }
  }
}

// 获取进度条状态
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return ''
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
    minute: '2-digit',
    second: '2-digit'
  })
}

// 定时刷新文件详情
let refreshInterval = null
const startAutoRefresh = () => {
  refreshInterval = setInterval(() => {
    // 只有当有任务在处理中时才刷新
    if (file.value && file.value.tasks && file.value.tasks.some(t => t.status === 'processing' || t.status === 'pending')) {
      fetchFileDetail()
    }
  }, 5000) // 每5秒刷新一次
}

onMounted(() => {
  fetchFileDetail()
  startAutoRefresh()
})

// 组件卸载时清除定时器
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading-container {
  padding: 20px;
}

.error-container {
  padding: 40px 0;
  text-align: center;
}

.task-creation {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ocr-option {
  display: flex;
  align-items: center;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.task-actions {
  display: flex;
  gap: 10px;
}

.paragraph-info {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>

