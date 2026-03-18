<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="90%"
    :fullscreen="isFullscreen"
    @close="handleClose"
  >
    <template #header>
      <div class="dialog-header">
        <span class="dialog-title">{{ title }}</span>
        <div class="header-actions">
          <el-button
            :icon="isFullscreen ? 'FullScreen' : 'FullScreen'"
            circle
            size="small"
            @click="toggleFullscreen"
          >
          </el-button>
        </div>
      </div>
    </template>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="error" class="error-container">
      <el-empty :description="error" />
    </div>

    <div v-else class="markdown-viewer">
      <div class="markdown-content" v-html="renderedContent"></div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button type="primary" @click="copyContent">复制内容</el-button>
        <el-button type="success" @click="downloadContent">下载文件</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Markdown 预览'
  },
  content: {
    type: String,
    default: ''
  },
  fileName: {
    type: String,
    default: 'document.md'
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const error = ref(null)
const isFullscreen = ref(false)

// 配置 marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.error('代码高亮失败:', err)
      }
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true
})

// 渲染 Markdown
const renderedContent = computed(() => {
  if (!props.content) return ''
  try {
    return marked(props.content)
  } catch (err) {
    console.error('Markdown 渲染失败:', err)
    return '<p>Markdown 渲染失败</p>'
  }
})

// 切换全屏
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

// 关闭对话框
const handleClose = () => {
  visible.value = false
  emit('close')
}

// 复制内容
const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    ElMessage.success('内容已复制到剪贴板')
  } catch (err) {
    console.error('复制失败:', err)
    ElMessage.error('复制失败，请手动复制')
  }
}

// 下载文件
const downloadContent = () => {
  try {
    const blob = new Blob([props.content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = props.fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    ElMessage.success('文件下载成功')
  } catch (err) {
    console.error('下载失败:', err)
    ElMessage.error('下载失败')
  }
}
</script>

<style scoped>
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.loading-container {
  padding: 20px;
}

.error-container {
  padding: 40px;
  text-align: center;
}

.markdown-viewer {
  max-height: 70vh;
  overflow-y: auto;
  padding: 20px;
  background-color: #fff;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

<style>
/* Markdown 内容样式 */
.markdown-content {
  line-height: 1.8;
  color: #333;
  font-size: 15px;
}

.markdown-content h1 {
  font-size: 2em;
  margin-top: 0;
  margin-bottom: 16px;
  font-weight: 600;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.markdown-content h2 {
  font-size: 1.5em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.markdown-content h3 {
  font-size: 1.25em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
}

.markdown-content h4 {
  font-size: 1em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
}

.markdown-content p {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-content ul,
.markdown-content ol {
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 2em;
}

.markdown-content li {
  margin-bottom: 0.25em;
}

.markdown-content pre {
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 16px;
  overflow: auto;
  margin-bottom: 16px;
}

.markdown-content code {
  background-color: rgba(175, 184, 193, 0.2);
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.markdown-content pre code {
  background-color: transparent;
  padding: 0;
  font-size: 100%;
}

.markdown-content blockquote {
  margin: 0 0 16px;
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
}

.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 16px;
}

.markdown-content table th,
.markdown-content table td {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
}

.markdown-content table tr {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-content table tr:nth-child(2n) {
  background-color: #f6f8fa;
}

.markdown-content img {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #fff;
}

.markdown-content a {
  color: #0366d6;
  text-decoration: none;
}

.markdown-content a:hover {
  text-decoration: underline;
}

.markdown-content hr {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #e1e4e8;
  border: 0;
}
</style>

