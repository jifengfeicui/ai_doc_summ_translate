# Electron API 使用示例

本文档展示如何在 Vue 组件中使用 Electron API。

## 📦 导入工具类

```javascript
import { 
  isElectron, 
  dialog, 
  fs, 
  app, 
  windowControl,
  getPlatform 
} from '@/utils/electron'
```

## 🎯 使用示例

### 1. 检测运行环境

```vue
<template>
  <div>
    <el-alert 
      v-if="isElectronEnv" 
      type="success" 
      :closable="false">
      正在 Electron 桌面应用中运行
    </el-alert>
    <el-alert 
      v-else 
      type="info" 
      :closable="false">
      正在浏览器中运行
    </el-alert>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { isElectron } from '@/utils/electron'

const isElectronEnv = ref(false)

onMounted(() => {
  isElectronEnv.value = isElectron()
})
</script>
```

### 2. 文件选择对话框

```vue
<template>
  <div>
    <el-button @click="selectPdfFile">选择 PDF 文件</el-button>
    <p v-if="selectedFile">已选择: {{ selectedFile }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dialog } from '@/utils/electron'

const selectedFile = ref('')

const selectPdfFile = async () => {
  try {
    const result = await dialog.openFile({
      filters: [
        { name: 'PDF 文件', extensions: ['pdf'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    })
    
    if (!result.canceled) {
      selectedFile.value = result.fileName
      ElMessage.success(`已选择文件: ${result.fileName}`)
      
      // 可以获取完整路径
      console.log('文件路径:', result.filePath)
      
      // 然后可以读取文件内容或上传到服务器
      await handleFileUpload(result.filePath)
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('选择文件失败')
  }
}

const handleFileUpload = async (filePath) => {
  // 在这里处理文件上传逻辑
  console.log('上传文件:', filePath)
}
</script>
```

### 3. 保存文件对话框

```vue
<template>
  <div>
    <el-button @click="saveResult">保存结果</el-button>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { dialog, fs } from '@/utils/electron'

const resultContent = ref('这是处理结果的内容...')

const saveResult = async () => {
  try {
    // 打开保存对话框
    const result = await dialog.saveFile({
      defaultPath: `result_${Date.now()}.txt`,
      filters: [
        { name: 'Text Files', extensions: ['txt'] },
        { name: 'Markdown Files', extensions: ['md'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    })
    
    if (!result.canceled) {
      // 写入文件
      const writeResult = await fs.writeFile(
        result.filePath, 
        resultContent.value
      )
      
      if (writeResult.success) {
        ElMessage.success('文件保存成功!')
      } else {
        ElMessage.error(`保存失败: ${writeResult.error}`)
      }
    }
  } catch (error) {
    console.error('保存文件失败:', error)
    ElMessage.error('保存文件失败')
  }
}
</script>
```

### 4. 读取文件内容

```vue
<template>
  <div>
    <el-button @click="loadConfig">加载配置</el-button>
    <pre v-if="configContent">{{ configContent }}</pre>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fs, app } from '@/utils/electron'

const configContent = ref('')

const loadConfig = async () => {
  try {
    // 获取应用数据目录
    const userDataPath = await app.getPath('userData')
    const configPath = `${userDataPath}/config.json`
    
    // 检查文件是否存在
    const existsResult = await fs.exists(configPath)
    
    if (existsResult.exists) {
      // 读取文件
      const readResult = await fs.readFile(configPath)
      
      if (readResult.success) {
        configContent.value = readResult.data
        ElMessage.success('配置加载成功')
      } else {
        ElMessage.error(`读取失败: ${readResult.error}`)
      }
    } else {
      ElMessage.warning('配置文件不存在')
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
  }
}
</script>
```

### 5. 窗口控制

```vue
<template>
  <div class="window-controls">
    <el-button 
      :icon="Minus" 
      circle 
      size="small" 
      @click="minimizeWindow">
    </el-button>
    <el-button 
      :icon="isMaximized ? CopyDocument : FullScreen" 
      circle 
      size="small" 
      @click="toggleMaximize">
    </el-button>
    <el-button 
      :icon="Close" 
      circle 
      size="small" 
      type="danger" 
      @click="closeWindow">
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Minus, FullScreen, CopyDocument, Close } from '@element-plus/icons-vue'
import { windowControl } from '@/utils/electron'

const isMaximized = ref(false)

onMounted(async () => {
  isMaximized.value = await windowControl.isMaximized()
})

const minimizeWindow = async () => {
  await windowControl.minimize()
}

const toggleMaximize = async () => {
  await windowControl.maximize()
  isMaximized.value = await windowControl.isMaximized()
}

const closeWindow = async () => {
  await windowControl.close()
}
</script>

<style scoped>
.window-controls {
  display: flex;
  gap: 8px;
  -webkit-app-region: no-drag; /* 允许按钮可点击 */
}
</style>
```

### 6. 平台检测与适配

```vue
<template>
  <div>
    <el-descriptions title="系统信息" :column="1" border>
      <el-descriptions-item label="平台">
        {{ platformName }}
      </el-descriptions-item>
      <el-descriptions-item label="Node.js">
        {{ versions.node }}
      </el-descriptions-item>
      <el-descriptions-item label="Chrome">
        {{ versions.chrome }}
      </el-descriptions-item>
      <el-descriptions-item label="Electron">
        {{ versions.electron }}
      </el-descriptions-item>
      <el-descriptions-item label="应用版本">
        {{ appVersion }}
      </el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPlatform, getVersions, app } from '@/utils/electron'

const platform = ref('')
const versions = ref({})
const appVersion = ref('')

const platformName = computed(() => {
  const names = {
    'win32': 'Windows',
    'darwin': 'macOS',
    'linux': 'Linux',
    'browser': '浏览器'
  }
  return names[platform.value] || '未知'
})

onMounted(async () => {
  platform.value = getPlatform()
  versions.value = getVersions()
  appVersion.value = await app.getVersion()
})
</script>
```

### 7. 完整的文件上传组件示例

```vue
<template>
  <div class="file-upload">
    <el-card>
      <template #header>
        <span>文件上传</span>
      </template>
      
      <!-- Electron 环境 -->
      <div v-if="isElectronEnv">
        <el-button 
          type="primary" 
          @click="selectFile"
          :loading="uploading">
          选择文件
        </el-button>
        
        <div v-if="selectedFile" class="file-info">
          <el-tag>{{ selectedFile.name }}</el-tag>
          <el-button 
            type="success" 
            size="small" 
            @click="uploadFile"
            :loading="uploading">
            上传
          </el-button>
        </div>
      </div>
      
      <!-- 浏览器环境 -->
      <div v-else>
        <el-upload
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1">
          <el-button type="primary">选择文件</el-button>
        </el-upload>
      </div>
      
      <!-- 上传进度 -->
      <el-progress 
        v-if="uploadProgress > 0" 
        :percentage="uploadProgress" 
        :status="uploadStatus" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { isElectron, dialog, fs } from '@/utils/electron'
import axios from 'axios'

const isElectronEnv = ref(false)
const selectedFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')

onMounted(() => {
  isElectronEnv.value = isElectron()
})

// Electron 环境: 选择文件
const selectFile = async () => {
  try {
    const result = await dialog.openFile({
      filters: [
        { name: 'PDF 文件', extensions: ['pdf'] },
        { name: 'Word 文档', extensions: ['doc', 'docx'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    })
    
    if (!result.canceled) {
      selectedFile.value = {
        name: result.fileName,
        path: result.filePath
      }
      ElMessage.success('文件已选择')
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('选择文件失败')
  }
}

// Electron 环境: 上传文件
const uploadFile = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  try {
    uploading.value = true
    uploadProgress.value = 0
    uploadStatus.value = ''
    
    // 读取文件内容
    const readResult = await fs.readFile(selectedFile.value.path, 'binary')
    
    if (!readResult.success) {
      throw new Error(readResult.error)
    }
    
    // 创建 FormData
    const formData = new FormData()
    const blob = new Blob([readResult.data])
    formData.append('file', blob, selectedFile.value.name)
    
    // 上传到服务器
    const response = await axios.post('/api/upload', formData, {
      onUploadProgress: (progressEvent) => {
        uploadProgress.value = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
      }
    })
    
    uploadStatus.value = 'success'
    ElMessage.success('上传成功!')
    
    // 清空选择
    selectedFile.value = null
    
  } catch (error) {
    console.error('上传失败:', error)
    uploadStatus.value = 'exception'
    ElMessage.error('上传失败: ' + error.message)
  } finally {
    uploading.value = false
  }
}

// 浏览器环境: 处理文件变化
const handleFileChange = (file) => {
  console.log('Selected file:', file)
  // 使用传统的文件上传方式
}
</script>

<style scoped>
.file-upload {
  padding: 20px;
}

.file-info {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
```

## 🎨 最佳实践

### 1. 始终检查环境

```javascript
if (isElectron()) {
  // 使用 Electron API
} else {
  // 使用浏览器 API
}
```

### 2. 错误处理

```javascript
try {
  const result = await dialog.openFile()
  if (!result.canceled) {
    // 处理文件
  }
} catch (error) {
  console.error('操作失败:', error)
  ElMessage.error('操作失败')
}
```

### 3. 加载状态

```javascript
const loading = ref(false)

const handleAction = async () => {
  loading.value = true
  try {
    // 执行操作
  } finally {
    loading.value = false
  }
}
```

### 4. 用户反馈

```javascript
import { ElMessage, ElMessageBox } from 'element-plus'

// 成功提示
ElMessage.success('操作成功')

// 错误提示
ElMessage.error('操作失败')

// 确认对话框
ElMessageBox.confirm('确定要执行此操作吗?', '提示', {
  type: 'warning'
}).then(() => {
  // 确认后的操作
})
```

## 📚 更多资源

- [Electron 官方文档](https://www.electronjs.org/docs)
- [Element Plus 文档](https://element-plus.org/)
- [Vue 3 组合式 API](https://vuejs.org/guide/introduction.html)

## 💡 提示

1. 所有 Electron API 调用都是异步的,需要使用 `async/await`
2. 在浏览器环境中,Electron API 会返回降级值或打印警告
3. 文件路径在 Windows 中使用反斜杠 `\`,需要注意路径处理
4. 始终进行错误处理,避免应用崩溃

