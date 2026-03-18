<template>
  <el-container style="height: 100vh">
    <!-- 左侧导航栏 -->
    <el-aside :width="asideWidth" class="aside-menu">
      <div class="logo-container">
        <h1 v-if="!isCollapsed" class="logo">文档系统</h1>
        <h1 v-else class="logo-mini">文</h1>
      </div>
      
      <el-menu 
        :default-active="activeIndex" 
        :collapse="isCollapsed"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF">
        <el-menu-item index="/">
          <el-icon><Upload /></el-icon>
          <template #title>选择文件</template>
        </el-menu-item>
        <el-menu-item index="/files">
          <el-icon><Folder /></el-icon>
          <template #title>文件列表</template>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>任务队列</template>
        </el-menu-item>
      </el-menu>
      
      <div class="collapse-btn">
        <el-button 
          :icon="isCollapsed ? Expand : Fold" 
          circle 
          size="small"
          @click="toggleCollapse" />
      </div>
    </el-aside>
    
    <!-- 右侧内容区域 -->
    <el-container>
      <el-header height="60px" class="header">
        <div class="header-container">
          <h2 class="page-title">{{ currentPageTitle }}</h2>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
      
      <el-footer height="40px" class="footer">
        <div class="footer-container">
          <p>©2025   AI文档总结与翻译系统</p>
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, List, Folder, Expand, Fold } from '@element-plus/icons-vue'

const route = useRoute()
const isCollapsed = ref(false)

const activeIndex = computed(() => route.path)

const asideWidth = computed(() => isCollapsed.value ? '64px' : '200px')

const currentPageTitle = computed(() => {
  const titles = {
    '/': '选择文件',
    '/tasks': '任务队列',
    '/files': '文件列表'
  }
  // 匹配详情页面
  if (route.path.startsWith('/files/')) return '文件详情'
  if (route.path.startsWith('/tasks/')) return '任务详情'
  return titles[route.path] || '文档总结与翻译系统'
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
/* 左侧导航栏 */
.aside-menu {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #2b3847;
  border-bottom: 1px solid #1f2d3d;
}

.logo {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.logo-mini {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #fff;
}

.el-menu {
  flex: 1;
  border-right: none;
}

.collapse-btn {
  padding: 16px;
  text-align: center;
  border-top: 1px solid #1f2d3d;
}

/* 顶部标题栏 */
.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  padding: 0;
}

.header-container {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
  color: #303133;
}

/* 主内容区域 */
.main-content {
  padding: 20px;
  background-color: #f0f2f5;
  overflow-y: auto;
}

/* 底部 */
.footer {
  background-color: #fff;
  border-top: 1px solid #e6e6e6;
  padding: 0;
}

.footer-container {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.footer-container p {
  margin: 0;
  font-size: 12px;
  color: #909399;
}
</style>
