<template>
  <div class="container">
    <!-- 本地文件选择(Electron 模式) -->
    <LocalFileSelector 
      v-if="isElectronEnv"
    />

    <!-- 传统文件上传(浏览器模式) -->
    <div v-else>
    <div class="page-header">
      <h2>文档总结与翻译</h2>
    </div>
    <div class="card">
      <h3>上传文件</h3>
      <el-form :model="form" label-width="120px">
        <el-form-item label="选择文件">
          <el-upload
            class="upload-demo"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            :file-list="fileList"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF, Word, PowerPoint 文件
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="loading" :disabled="!form.file">
            上传文件
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <div class="card" v-if="recentFiles.length > 0">
      <h3>最近上传</h3>
      <el-table :data="recentFiles" style="width: 100%">
        <el-table-column prop="file_name" label="文件名" />
        <el-table-column prop="file_type" label="类型" width="100" />
        <el-table-column prop="upload_time" label="上传时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.upload_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="md_converted" label="MD转换" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.md_converted" type="success" size="small">已转换</el-tag>
            <el-tag v-else type="info" size="small">未转换</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="任务数" width="100">
          <template #default="scope">
            {{ scope.row.tasks ? scope.row.tasks.length : 0 }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button 
              size="small" 
              @click="viewFileDetail(scope.row.id)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { fileApi } from '@/api'
import { isElectron } from '@/utils/electron'
import LocalFileSelector from '@/components/LocalFileSelector.vue'

const router = useRouter()
const isElectronEnv = ref(false)
const form = ref({
  file: null
})
const fileList = ref([])
const loading = ref(false)
const recentFiles = ref([])

// 获取最近文件
const fetchRecentFiles = async () => {
  try {
    const response = await fileApi.getFiles()
    recentFiles.value = response.files.slice(0, 5)
  } catch (error) {
    console.error('获取文件列表失败:', error)
    ElMessage.error('获取文件列表失败')
  }
}

// 处理文件变化
const handleFileChange = (file) => {
  form.value.file = file.raw
  fileList.value = [file]
}

// 提交表单
const submitForm = async () => {
  if (!form.value.file) {
    ElMessage.warning('请选择文件')
    return
  }
  
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', form.value.file)
    
    const response = await fileApi.uploadFile(formData)
    ElMessage.success('文件上传成功')
    
    // 重置表单
    form.value.file = null
    fileList.value = []
    
    // 跳转到文件详情页
    router.push(`/files/${response.id}`)
  } catch (error) {
    console.error('上传文件失败:', error)
    ElMessage.error(error.response?.data?.detail || '上传文件失败')
  } finally {
    loading.value = false
  }
}

// 查看文件详情
const viewFileDetail = (fileId) => {
  router.push(`/files/${fileId}`)
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


onMounted(() => {
  isElectronEnv.value = isElectron()
  fetchRecentFiles()
})
</script>

<style scoped>
.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 7px;
}
</style>
