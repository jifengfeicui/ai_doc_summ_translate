<template>
  <div class="container">
    <div class="page-header">
      <h2>任务详情</h2>
      <div class="header-actions">
        <el-button 
          v-if="task && (task.status === 'failed' || task.status === 'completed')"
          type="warning" 
          @click="retryTask" 
          :loading="retrying">
          重试任务
        </el-button>
        <el-button 
          v-if="task && task.status !== 'processing'"
          type="danger" 
          @click="deleteTask">
          删除任务
        </el-button>
        <el-button @click="backToFile" v-if="task && task.file_id">返回文件</el-button>
        <el-button @click="$router.back()">返回</el-button>
      </div>
    </div>
    
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>
    
    <template v-else-if="task">
      <div class="card">
        <h3>基本信息</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="文件ID">{{ task.file_id }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">
            <el-tag v-if="task.task_type === 'summarize'" type="success">总结</el-tag>
            <el-tag v-else-if="task.task_type === 'translate'" type="primary">翻译</el-tag>
            <el-tag v-else type="info">其他</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="task.status === 'completed'" type="success">已完成</el-tag>
            <el-tag v-else-if="task.status === 'processing'" type="warning">处理中</el-tag>
            <el-tag v-else-if="task.status === 'pending'" type="info">等待中</el-tag>
            <el-tag v-else-if="task.status === 'failed'" type="danger">失败</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(task.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(task.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      
      <div class="card">
        <h3>处理进度</h3>
        <el-progress 
          :percentage="task.progress" 
          :status="getProgressStatus(task.status)"
          :format="progressFormat"
          :stroke-width="20"
        />
        
        <!-- 翻译任务的段落进度 -->
        <div v-if="task.task_type === 'translate' && task.total_paragraphs > 0" class="paragraph-progress">
          <p class="paragraph-info">
            正在翻译：第 <strong>{{ task.current_paragraph }}</strong> / {{ task.total_paragraphs }} 段
          </p>
          <el-progress 
            :percentage="getParagraphPercentage(task.current_paragraph, task.total_paragraphs)" 
            :show-text="false"
            :stroke-width="10"
          />
        </div>
        
        <div v-if="task.status === 'processing'" class="processing-info">
          <p>正在处理中，请耐心等待...</p>
          <p>处理大型文档可能需要几分钟时间</p>
        </div>
        
        <div v-if="task.status === 'failed'" class="error-info">
          <h4>错误信息</h4>
          <el-alert
            title="处理失败"
            type="error"
            :description="task.error_message || '未知错误'"
            show-icon
          />
        </div>
      </div>
      
      <div v-if="task.status === 'completed'" class="card">
        <h3>处理结果</h3>
        <div class="result-actions">
          <el-button type="success" @click="previewResult">预览结果</el-button>
          <el-button type="primary" @click="downloadResult">下载结果文件</el-button>
        </div>
      </div>
    </template>
    
    <div v-else class="error-container">
      <el-empty description="未找到任务信息" />
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
import { taskApi } from '@/api'
import MarkdownViewer from '@/components/MarkdownViewer.vue'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => route.params.id)
const task = ref(null)
const loading = ref(false)
const retrying = ref(false)

// Markdown 预览相关
const showMarkdownViewer = ref(false)
const markdownContent = ref('')
const markdownFileName = ref('')
const markdownTitle = ref('')

// 获取任务详情
const fetchTaskDetail = async () => {
  loading.value = true
  try {
    const response = await taskApi.getTaskDetail(taskId.value)
    task.value = response
  } catch (error) {
    console.error('获取任务详情失败:', error)
    ElMessage.error('获取任务详情失败')
  } finally {
    loading.value = false
  }
}

// 下载任务结果
const downloadResult = () => {
  taskApi.downloadTaskResult(taskId.value)
}

// 预览任务结果
const previewResult = async () => {
  try {
    const response = await taskApi.getTaskContent(taskId.value)
    markdownContent.value = response.content
    markdownFileName.value = response.file_name
    markdownTitle.value = `任务结果 - ${response.file_name}`
    showMarkdownViewer.value = true
  } catch (error) {
    console.error('获取任务结果内容失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取任务结果内容失败')
  }
}

// 重试任务
const retryTask = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重新执行这个任务吗?',
      '确认重试',
      {
        type: 'info',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    retrying.value = true
    await taskApi.retryTask(taskId.value)
    ElMessage.success('任务已重新提交')
    // 刷新任务详情
    await fetchTaskDetail()
    // 重新启动自动刷新
    startAutoRefresh()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重试任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '重试任务失败')
    }
  } finally {
    retrying.value = false
  }
}

// 删除任务
const deleteTask = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个任务吗? 任务结果文件也会被删除。删除后将返回上一页。',
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    await taskApi.deleteTask(taskId.value)
    ElMessage.success('任务已删除')
    // 返回上一页
    router.back()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除任务失败')
    }
  }
}

// 返回文件详情
const backToFile = () => {
  if (task.value && task.value.file_id) {
    router.push(`/files/${task.value.file_id}`)
  }
}

// 计算段落进度百分比
const getParagraphPercentage = (current, total) => {
  if (!total) return 0
  return Math.floor((current / total) * 100)
}

// 获取进度条状态
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return ''
}

// 进度条格式化
const progressFormat = (percentage) => {
  if (task.value.status === 'completed') return '完成'
  if (task.value.status === 'failed') return '失败'
  return `${percentage}%`
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

// 定时刷新任务详情
let refreshInterval = null
const startAutoRefresh = () => {
  refreshInterval = setInterval(() => {
    if (task.value && (task.value.status === 'processing' || task.value.status === 'pending')) {
      fetchTaskDetail()
    } else {
      // 如果任务已完成或失败，停止刷新
      clearInterval(refreshInterval)
    }
  }, 5000) // 每5秒刷新一次
}

onMounted(() => {
  fetchTaskDetail()
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

.header-actions {
  display: flex;
  gap: 10px;
}

.loading-container {
  padding: 20px;
}

.error-container {
  padding: 40px 0;
  text-align: center;
}

.processing-info {
  margin-top: 20px;
  color: #909399;
  text-align: center;
}

.error-info {
  margin-top: 20px;
}

.retry-action {
  margin-top: 15px;
}

.paragraph-progress {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.paragraph-info {
  margin-bottom: 10px;
  color: #606266;
  font-size: 14px;
}

.result-actions {
  display: flex;
  gap: 10px;
}
</style>
