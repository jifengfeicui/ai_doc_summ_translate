<template>
  <div class="container">
    <div class="page-header">
      <h2>任务队列</h2>
      <el-space>
        <el-switch
          v-model="autoRefreshEnabled"
          active-text="自动刷新"
          inactive-text="自动刷新"
          style="--el-switch-on-color: #67c23a; --el-switch-off-color: #dcdfe6;"
        />
        <el-button :icon="Refresh" @click="refreshTasks" :loading="refreshing">
          刷新
        </el-button>
        <el-button 
          v-if="selectedTasks.length > 0" 
          type="danger" 
          :icon="Delete"
          @click="deleteBatchTasks">
          删除选中 ({{ selectedTasks.length }})
        </el-button>
      </el-space>
    </div>

    <!-- 统计信息（可点击筛选） -->
    <el-row :gutter="16" style="margin-bottom: 20px;">
      <el-col :span="4">
        <div 
          class="stat-card"
          :class="{ 'stat-card-active': statusFilter === '' }"
          @click="statusFilter = ''">
          <el-card shadow="hover">
            <el-statistic title="总任务数" :value="tasks.length">
              <template #prefix>
                <el-icon><List /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </div>
      </el-col>
      <el-col :span="4">
        <div 
          class="stat-card"
          :class="{ 'stat-card-active': statusFilter === 'pending' }"
          @click="toggleStatusFilter('pending')">
          <el-card shadow="hover">
            <el-statistic 
              title="等待中" 
              :value="statusCount.pending" 
              value-style="color: #909399;">
              <template #prefix>
                <el-icon><Clock /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </div>
      </el-col>
      <el-col :span="4">
        <div 
          class="stat-card"
          :class="{ 'stat-card-active': statusFilter === 'processing' }"
          @click="toggleStatusFilter('processing')">
          <el-card shadow="hover">
            <el-statistic 
              title="处理中" 
              :value="statusCount.processing" 
              value-style="color: #409eff;">
              <template #prefix>
                <el-icon><Loading /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </div>
      </el-col>
      <el-col :span="4">
        <div 
          class="stat-card"
          :class="{ 'stat-card-active': statusFilter === 'completed' }"
          @click="toggleStatusFilter('completed')">
          <el-card shadow="hover">
            <el-statistic 
              title="已完成" 
              :value="statusCount.completed"
              value-style="color: #67c23a;">
              <template #prefix>
                <el-icon><CircleCheck /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </div>
      </el-col>
      <el-col :span="4">
        <div 
          class="stat-card"
          :class="{ 'stat-card-active': statusFilter === 'failed' }"
          @click="toggleStatusFilter('failed')">
          <el-card shadow="hover">
            <el-statistic 
              title="失败" 
              :value="statusCount.failed"
              value-style="color: #f56c6c;">
              <template #prefix>
                <el-icon><CircleClose /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </div>
      </el-col>
      <el-col :span="4">
        <div 
          class="stat-card"
          :class="{ 'stat-card-active': statusFilter === 'cancelled' }"
          @click="toggleStatusFilter('cancelled')">
          <el-card shadow="hover">
            <el-statistic 
              title="已取消" 
              :value="statusCount.cancelled"
              value-style="color: #e6a23c;">
              <template #prefix>
                <el-icon><WarningFilled /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- 筛选器 -->
    <el-card shadow="never" style="margin-bottom: 20px;">
      <el-space wrap>
        <el-input
          v-model="searchQuery"
          placeholder="搜索文件名"
          :prefix-icon="Search"
          style="width: 200px;"
          clearable
        />
        <el-select 
          v-model="statusFilter" 
          placeholder="任务状态" 
          clearable 
          style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="等待中" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-select 
          v-model="typeFilter" 
          placeholder="任务类型" 
          clearable 
          style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="总结" value="summarize" />
          <el-option label="翻译" value="translate" />
        </el-select>
      </el-space>
    </el-card>

    <!-- 任务列表 -->
    <el-card>
      <el-table 
        :data="filteredTasks" 
        @selection-change="handleSelectionChange"
        v-loading="loading"
        row-key="id"
        style="width: 100%">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="文件名" min-width="200">
          <template #default="scope">
            <div class="file-info">
              <el-icon><Document /></el-icon>
              <span>{{ scope.row.file?.file_name || '未知文件' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" label="任务类型" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.task_type === 'summarize' ? 'success' : 'primary'" size="small">
              {{ scope.row.task_type === 'summarize' ? '总结' : '翻译' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
            <el-tag v-if="scope.row.stop_requested" type="warning" size="small" style="margin-left: 4px;">
              停止中
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200">
          <template #default="scope">
            <div v-if="scope.row.status === 'processing'">
              <el-progress 
                :percentage="scope.row.progress" 
                :status="scope.row.progress === 100 ? 'success' : undefined"
              />
              <el-text size="small" type="info" v-if="scope.row.total_paragraphs > 0">
                {{ scope.row.current_paragraph }} / {{ scope.row.total_paragraphs }}
              </el-text>
            </div>
            <span v-else-if="scope.row.status === 'completed'">
              <el-progress :percentage="100" status="success" />
            </span>
            <span v-else-if="scope.row.status === 'failed'">
              <el-text type="danger" size="small">{{ scope.row.error_message || '失败' }}</el-text>
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="scope">
            <el-space wrap>
              <!-- 停止按钮 - 仅处理中的任务显示 -->
              <el-button 
                v-if="scope.row.status === 'processing' && !scope.row.stop_requested" 
                type="warning" 
                size="small" 
                @click="stopTask(scope.row.id)">
                停止
              </el-button>
              <!-- 强制停止按钮 - 已请求停止但未响应时显示 -->
              <el-button 
                v-if="scope.row.status === 'processing' && scope.row.stop_requested" 
                type="danger" 
                size="small" 
                @click="forceStopTask(scope.row.id)">
                强制停止
              </el-button>
              <!-- 查看按钮 - 已完成的任务 -->
              <el-button 
                v-if="scope.row.status === 'completed'" 
                type="primary" 
                size="small" 
                @click="viewResult(scope.row.id)">
                查看
              </el-button>
              <!-- 下载按钮 - 已完成的任务 -->
              <el-button 
                v-if="scope.row.status === 'completed'" 
                type="success" 
                size="small" 
                @click="downloadResult(scope.row.id)">
                下载
              </el-button>
              <!-- 预览按钮 - 已完成的任务 -->
              <el-button 
                v-if="scope.row.status === 'completed'" 
                type="info" 
                size="small"
                :icon="View"
                @click="quickPreview(scope.row.id)">
                预览
              </el-button>
              <!-- 重试按钮 - 失败、已完成、已取消的任务 -->
              <el-button 
                v-if="['failed', 'completed', 'cancelled'].includes(scope.row.status)" 
                type="warning" 
                size="small" 
                @click="retryTask(scope.row.id)">
                重试
              </el-button>
              <!-- 删除按钮 - 非处理中的任务 -->
              <el-button 
                v-if="scope.row.status !== 'processing'" 
                type="danger" 
                size="small" 
                @click="deleteTask(scope.row.id)">
                删除
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 20px; text-align: right;">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredTasks.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <MarkdownViewer
      v-model="previewDialogVisible"
      :title="previewTitle"
      :content="previewContent"
      :file-name="previewFileName"
      :loading="previewLoading"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, 
  Delete, 
  Search, 
  Document,
  List,
  Loading,
  CircleCheck,
  CircleClose,
  Clock,
  WarningFilled,
  View
} from '@element-plus/icons-vue'
import { taskApi, fileApi } from '@/api'
import MarkdownViewer from '@/components/MarkdownViewer.vue'

const router = useRouter()
const tasks = ref([])
const selectedTasks = ref([])
const loading = ref(false)
const refreshing = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const autoRefreshEnabled = ref(true)
const previewDialogVisible = ref(false)
const previewContent = ref('')
const previewFileName = ref('')
const previewTitle = ref('')
const previewLoading = ref(false)

let autoRefreshTimer = null

// 统计信息
const statusCount = computed(() => {
  return {
    processing: tasks.value.filter(t => t.status === 'processing').length,
    completed: tasks.value.filter(t => t.status === 'completed').length,
    failed: tasks.value.filter(t => t.status === 'failed').length,
    pending: tasks.value.filter(t => t.status === 'pending').length,
    cancelled: tasks.value.filter(t => t.status === 'cancelled').length
  }
})

// 过滤后的任务
const filteredTasks = computed(() => {
  let result = tasks.value

  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t => 
      t.file?.file_name?.toLowerCase().includes(query)
    )
  }

  // 状态过滤
  if (statusFilter.value) {
    result = result.filter(t => t.status === statusFilter.value)
  }

  // 类型过滤
  if (typeFilter.value) {
    result = result.filter(t => t.task_type === typeFilter.value)
  }

  return result
})

// 获取任务列表
const fetchTasks = async () => {
  try {
    loading.value = true
    const response = await taskApi.getTasks()
    tasks.value = response.tasks || []
    
    // 同时获取文件信息
    const filesResponse = await fileApi.getFiles()
    const filesMap = {}
    filesResponse.files.forEach(f => {
      filesMap[f.id] = f
    })
    
    // 关联文件信息
    tasks.value.forEach(t => {
      if (t.file_id && filesMap[t.file_id]) {
        t.file = filesMap[t.file_id]
      }
    })
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// 刷新任务
const refreshTasks = async () => {
  refreshing.value = true
  await fetchTasks()
  refreshing.value = false
  ElMessage.success('已刷新')
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTasks.value = selection
}

// 删除单个任务
const deleteTask = async (taskId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个任务吗? 任务结果文件也会被删除。',
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    await taskApi.deleteTask(taskId)
    ElMessage.success('任务已删除')
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除任务失败')
    }
  }
}

// 批量删除任务
const deleteBatchTasks = async () => {
  try {
    // 检查是否有正在处理的任务
    const processingTasks = selectedTasks.value.filter(t => t.status === 'processing')
    if (processingTasks.length > 0) {
      await ElMessageBox.confirm(
        `选中的任务中有 ${processingTasks.length} 个正在处理中,将被跳过。是否继续删除其他任务?`,
        '提示',
        {
          type: 'warning',
          confirmButtonText: '继续',
          cancelButtonText: '取消'
        }
      )
    }
    
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个任务吗? 任务结果文件也会被删除。`,
      '确认批量删除',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    const taskIds = selectedTasks.value.map(t => t.id)
    const result = await taskApi.deleteTasksBatch(taskIds)
    
    if (result.deleted_count > 0) {
      ElMessage.success(result.message)
    }
    
    if (result.errors && result.errors.length > 0) {
      ElMessage.warning(`部分任务删除失败: ${result.errors.join(', ')}`)
    }
    
    selectedTasks.value = []
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除任务失败:', error)
      ElMessage.error('批量删除任务失败')
    }
  }
}

// 查看结果
const viewResult = (taskId) => {
  router.push(`/tasks/${taskId}`)
}

// 下载结果
const downloadResult = (taskId) => {
  taskApi.downloadTaskResult(taskId)
  ElMessage.success('开始下载')
}

// 重试任务
const retryTask = async (taskId) => {
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
    
    await taskApi.retryTask(taskId)
    ElMessage.success('任务已重新启动')
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重试任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '重试任务失败')
    }
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
    
    // 开始轮询任务状态
    const checkInterval = setInterval(async () => {
      const task = tasks.value.find(t => t.id === taskId)
      if (task && task.status === 'cancelled') {
        ElMessage.success('任务已停止')
        clearInterval(checkInterval)
      }
    }, 2000)
    
    // 30秒后停止轮询
    setTimeout(() => clearInterval(checkInterval), 30000)
    
    await fetchTasks()
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
        cancelButtonText: '取消',
        distinguishCancelAndClose: true
      }
    )
    
    await taskApi.forceStopTask(taskId)
    ElMessage.success('任务已强制停止')
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('强制停止任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '强制停止任务失败')
    }
  }
}

// 获取状态类型
const getStatusType = (status) => {
  const typeMap = {
    pending: 'info',
    processing: '',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return textMap[status] || status
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

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

// 自动刷新(每5秒)
const startAutoRefresh = () => {
  autoRefreshTimer = setInterval(() => {
    if (!autoRefreshEnabled.value) return
    if (statusCount.value.processing > 0 || statusCount.value.pending > 0) {
      fetchTasks()
    }
  }, 5000)
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

const toggleStatusFilter = (status) => {
  if (statusFilter.value === status) {
    statusFilter.value = ''
  } else {
    statusFilter.value = status
  }
}

const quickPreview = async (taskId) => {
  try {
    previewLoading.value = true
    const task = tasks.value.find(t => t.id === taskId)
    const response = await taskApi.getTaskContent(taskId)
    previewContent.value = response.content
    previewFileName.value = response.file_name || task?.file?.file_name || '任务结果'
    previewTitle.value = `任务结果 - ${previewFileName.value}`
    previewDialogVisible.value = true
  } catch (error) {
    console.error('获取任务结果失败:', error)
    ElMessage.error('获取任务结果失败')
  } finally {
    previewLoading.value = false
  }
}

onMounted(() => {
  fetchTasks()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover .el-card {
  border-color: #409eff;
}

.stat-card-active .el-card {
  border-color: #409eff;
  background: linear-gradient(135deg, #ecf5ff 0%, #f0f9ff 100%);
}
</style>

