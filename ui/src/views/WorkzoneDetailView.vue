<template>
  <div class="container">
    <div class="page-header">
      <div>
        <el-button @click="goBack">返回</el-button>
        <h2 style="display: inline; margin-left: 16px;">{{ workspace?.name }}</h2>
      </div>
      <el-space>
        <el-button type="success" @click="createAllTasks('summarize')" :loading="batchLoading" :disabled="!workspace || workspace.file_count === 0">
          全部总结
        </el-button>
        <el-button type="primary" @click="createAllTasks('translate')" :loading="batchLoading" :disabled="!workspace || workspace.file_count === 0">
          全部翻译
        </el-button>
        <el-divider direction="vertical" />
        <el-button type="success" @click="batchCreateTask('summarize')" :disabled="selectedFiles.length === 0" :loading="batchLoading">
          批量总结
        </el-button>
        <el-button type="primary" @click="batchCreateTask('translate')" :disabled="selectedFiles.length === 0" :loading="batchLoading">
          批量翻译
        </el-button>
        <el-divider direction="vertical" />
        <el-switch v-model="useOcr" active-text="OCR" inactive-text="OCR" />
        <el-button type="success" @click="exportCsv" :loading="exporting">导出总结CSV</el-button>
        <el-button type="primary" @click="triggerUpload">上传文件</el-button>
        <el-button @click="showScanFolderDialog = true">扫描文件夹</el-button>
        <el-button :icon="Refresh" @click="fetchWorkspace" :loading="loading">刷新</el-button>
      </el-space>
    </div>

    <el-descriptions :column="2" border v-if="workspace">
      <el-descriptions-item label="名称">{{ workspace.name }}</el-descriptions-item>
      <el-descriptions-item label="文件数">{{ workspace.file_count }}</el-descriptions-item>
      <el-descriptions-item label="描述">{{ workspace.description || '-' }}</el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ formatDateTime(workspace.created_at) }}</el-descriptions-item>
    </el-descriptions>

    <el-divider />

    <h3>文件列表</h3>
    <el-table 
      :data="workspace?.files || []" 
      v-loading="loading" 
      stripe 
      border
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="file_type" label="类型" width="100">
        <template #default="scope">
          <el-tag size="small">{{ scope.row.file_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_size" label="大小" width="120">
        <template #default="scope">
          {{ formatFileSize(scope.row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column label="任务" width="180">
        <template #default="scope">
          <div v-if="scope.row.tasks && scope.row.tasks.length > 0">
            <el-tag v-for="task in scope.row.tasks" :key="task.id" 
              :type="getTaskStatusType(task.status)" 
              size="small" style="margin-right: 4px;">
              {{ task.task_type === 'summarize' ? '总结' : task.task_type }}
            </el-tag>
          </div>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="viewFileDetail(scope.row.id)">查看详情</el-button>
          <el-button size="small" type="danger" @click="removeFile(scope.row.id)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      @current-change="fetchWorkspace"
      @size-change="fetchWorkspace"
      style="margin-top: 16px; justify-content: flex-end;"
    />

    <el-dialog v-model="showScanFolderDialog" title="扫描文件夹" width="500px">
      <el-form label-width="80px">
        <el-form-item label="文件夹路径">
          <el-input v-model="scanFolderPath" placeholder="请输入或选择文件夹路径">
            <template #append>
              <el-button @click="selectFolder" :icon="FolderOpened">选择</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showScanFolderDialog = false">取消</el-button>
        <el-button type="primary" @click="scanFolder" :loading="scanning">扫描</el-button>
      </template>
    </el-dialog>
    <input ref="fileInputRef" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.md" style="display: none;" @change="handleFileChange" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FolderOpened, Refresh } from '@element-plus/icons-vue'
import { workspaceApi, fileApi, taskApi } from '@/api'

const router = useRouter()
const route = useRoute()

const workspace = ref(null)
const loading = ref(false)
const exporting = ref(false)
const batchLoading = ref(false)
const useOcr = ref(false)
const selectedFiles = ref([])
const fileInputRef = ref(null)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const showScanFolderDialog = ref(false)
const scanning = ref(false)
const scanFolderPath = ref('')

const uploadData = computed(() => ({
  workspace_id: route.params.id
}))

const uploadHeaders = computed(() => ({}))

const beforeUpload = (file) => {
  const allowedTypes = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.md']
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedTypes.includes(ext)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  return true
}

const handleUploadSuccess = (response) => {
  ElMessage.success('文件上传成功')
  fetchWorkspace()
}

const handleUploadError = (error) => {
  ElMessage.error('文件上传失败: ' + error)
}

const fetchWorkspace = async () => {
  loading.value = true
  try {
    workspace.value = await workspaceApi.getWorkspaceDetail(route.params.id, pagination.page, pagination.pageSize)
    pagination.total = workspace.value.total
  } catch (e) {
    ElMessage.error('获取工作区详情失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedFiles.value = selection
}

const batchCreateTask = async (taskType) => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  const fileIds = selectedFiles.value.map(f => f.id)
  const taskTypeText = taskType === 'summarize' ? '总结' : '翻译'
  
  try {
    batchLoading.value = true
    await fileApi.createTasksBatch(fileIds, taskType, useOcr.value)
    ElMessage.success(`已为 ${selectedFiles.value.length} 个文件创建${taskTypeText}任务`)
    selectedFiles.value = []
    fetchWorkspace()
  } catch (e) {
    ElMessage.error('创建任务失败')
  } finally {
    batchLoading.value = false
  }
}

const createAllTasks = async (taskType) => {
  if (!workspace.value || workspace.value.file_count === 0) {
    ElMessage.warning('工作区没有文件')
    return
  }
  
  const taskTypeText = taskType === 'summarize' ? '总结' : '翻译'
  
  try {
    await ElMessageBox.confirm(`将为工作区所有 ${workspace.value.file_count} 个文件创建${taskTypeText}任务`, '确认', { type: 'warning' })
    batchLoading.value = true
    const result = await workspaceApi.createWorkspaceTasks(route.params.id, taskType, useOcr.value)
    ElMessage.success(result.message)
    fetchWorkspace()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('创建任务失败')
    }
  } finally {
    batchLoading.value = false
  }
}

const removeFile = async (fileId) => {
  try {
    await ElMessageBox.confirm('确定要从工作区移除该文件吗？', '提示', { type: 'warning' })
    await workspaceApi.removeFilesFromWorkspace(route.params.id, [fileId])
    ElMessage.success('移除成功')
    fetchWorkspace()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
}

const scanFolder = async () => {
  if (!scanFolderPath.value) {
    ElMessage.warning('请输入文件夹路径')
    return
  }
  scanning.value = true
  try {
    const result = await workspaceApi.scanFolder(route.params.id, scanFolderPath.value)
    ElMessage.success(`成功添加 ${result.total_added} 个文件，跳过 ${result.total_skipped} 个`)
    showScanFolderDialog.value = false
    scanFolderPath.value = ''
    fetchWorkspace()
  } catch (e) {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

const selectFolder = async () => {
  if (window.electronAPI?.dialog?.openDirectory) {
    const result = await window.electronAPI.dialog.openDirectory()
    if (!result.canceled && result.directoryPath) {
      scanFolderPath.value = result.directoryPath
    }
  } else {
    ElMessage.warning('请在 Electron 环境中使用此功能')
  }
}

const exportCsv = async () => {
  exporting.value = true
  try {
    workspaceApi.exportCsv(route.params.id)
    ElMessage.success('开始导出总结CSV')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const viewFileDetail = (fileId) => {
  router.push(`/files/${fileId}`)
}

const goBack = () => {
  router.push('/workzones')
}

const formatDateTime = (str) => {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN')
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  return (bytes / 1024).toFixed(1) + ' KB'
}

const getTaskStatusType = (status) => {
  const types = {
    'completed': 'success',
    'processing': 'warning',
    'pending': 'info',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

let fileInput = null

const triggerUpload = () => {
  fileInputRef.value.click()
}

const handleFileChange = async (e) => {
  const files = e.target.files
  if (files.length === 0) return
  
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('workspace_id', route.params.id)
    
    try {
      await fetch('/api/files/upload', {
        method: 'POST',
        body: formData
      })
    } catch (err) {
      console.error('上传失败', err)
    }
  }
  
  ElMessage.success(`已上传 ${files.length} 个文件`)
  fetchWorkspace()
  e.target.value = ''
}

onMounted(() => {
  fetchWorkspace()
})
</script>

<style scoped>
.container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  vertical-align: middle;
}
</style>
