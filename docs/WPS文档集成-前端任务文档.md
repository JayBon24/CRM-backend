# WPS文档集成功能 - 前端任务文档

## 一、功能概述

在Vue3前端项目中集成WPS Office Web SDK，实现文档在线预览和编辑功能。用户可以在浏览器中直接打开Word文档（.docx），无需下载和安装本地软件，支持在线编辑、保存等功能。

## 二、技术选型

### 2.1 WPS Office Web SDK

**核心方案：WPS Office Web SDK**

**技术特点：**
- 基于Web技术，无需安装插件
- 支持在线查看和编辑Word、Excel、PPT
- 提供丰富的JavaScript API
- 支持自定义UI和功能
- 支持移动端（响应式）

**官方文档：**
- WPS Office Web SDK文档：https://open.wps.cn/docs/office
- API参考：https://open.wps.cn/docs/office/api
- 示例代码：https://open.wps.cn/docs/office/examples

### 2.2 集成方式

**方案一：CDN引入（推荐方式）**
- 优点：快速集成，无需构建配置，官方推荐方式
- 缺点：依赖外部CDN，需要网络连接
- 适用：开发测试、生产环境

**注意：** WPS Office Web SDK目前主要通过CDN方式引入，官方未提供NPM包。如需使用，请参考WPS开放平台官方文档获取最新的CDN地址和集成方式。

## 三、前端核心功能

### 3.1 文档预览组件

**组件名称：** `WPSViewer.vue`

**功能：**
- 文档在线预览（只读模式）
- 支持全屏显示
- 支持缩放控制
- 支持打印功能

**Props：**
```typescript
interface WPSViewerProps {
  documentId: number;      // 文档ID
  mode?: 'view' | 'edit';  // 模式：预览或编辑，默认'view'
  width?: string;          // 容器宽度，默认'100%'
  height?: string;         // 容器高度，默认'600px'
  autoLoad?: boolean;      // 是否自动加载，默认true
}
```

**Events：**
```typescript
interface WPSViewerEvents {
  'load': (config: any) => void;           // 加载完成
  'error': (error: Error) => void;        // 加载错误
  'ready': () => void;                    // WPS就绪
  'close': () => void;                    // 关闭文档
}
```

### 3.2 文档编辑组件

**组件名称：** `WPSEditor.vue`

**功能：**
- 文档在线编辑
- 自动保存功能
- 编辑状态提示
- 工具栏自定义

**Props：**
```typescript
interface WPSEditorProps {
  documentId: number;           // 文档ID
  userId?: number;              // 用户ID
  userName?: string;            // 用户名
  autoSave?: boolean;           // 是否自动保存，默认true
  autoSaveInterval?: number;    // 自动保存间隔（秒），默认300
  showToolbar?: boolean;        // 是否显示工具栏，默认true
  width?: string;               // 容器宽度，默认'100%'
  height?: string;              // 容器高度，默认'100%'
}
```

**Events：**
```typescript
interface WPSEditorEvents {
  'load': (config: any) => void;           // 加载完成
  'ready': () => void;                    // 编辑器就绪
  'save': (result: SaveResult) => void;    // 保存成功
  'save-error': (error: Error) => void;   // 保存失败
  'change': () => void;                   // 内容改变
  'close': () => void;                    // 关闭文档
  'error': (error: Error) => void;        // 错误事件
}
```

### 3.3 WPS服务封装

**模块：** `services/wpsService.ts`

**功能：**
- 获取WPS配置
- 初始化WPS实例
- 处理WPS事件
- 文档保存

**主要方法：**
```typescript
class WPSService {
  /**
   * 获取WPS编辑配置
   */
  async getEditConfig(documentId: number, mode: 'view' | 'edit' = 'edit'): Promise<WPSConfig> {
    // 调用后端API获取配置
  }
  
  /**
   * 初始化WPS实例
   */
  initWPS(config: WPSConfig, container: HTMLElement): Promise<WPSInstance> {
    // 初始化WPS Office Web SDK
  }
  
  /**
   * 保存文档
   */
  async saveDocument(documentId: number, fileUrl: string): Promise<SaveResult> {
    // 调用后端保存接口
  }
  
  /**
   * 销毁WPS实例
   */
  destroyWPS(instance: WPSInstance): void {
    // 清理WPS实例
  }
}
```

## 四、API接口对接

### 4.1 获取WPS配置接口

**接口路径：** `POST /api/case/document/wps/edit-config/`

**请求参数：**
```typescript
interface WPSConfigRequest {
  documentId: number;
  mode: 'view' | 'edit';
  userId?: number;
  userName?: string;
}
```

**响应数据：**
```typescript
interface WPSConfigResponse {
  code: number;
  msg: string;
  data: {
    documentId: number;
    wpsConfig: {
      fileUrl: string;          // 文档URL
      fileId: string;           // 文件ID
      appId: string;           // 应用ID
      token: string;           // 访问令牌
      mode: 'view' | 'edit';   // 模式
      userId: string;          // 用户ID
      userName: string;        // 用户名
      callbackUrl: string;     // 回调地址
      downloadUrl: string;     // 下载地址
      saveUrl: string;         // 保存地址
    };
  };
}
```

**实现示例：**
```typescript
// api/document.ts
export const getWPSConfig = async (
  documentId: number,
  mode: 'view' | 'edit' = 'edit'
): Promise<WPSConfig> => {
  const response = await request.post('/api/case/document/wps/edit-config/', {
    documentId,
    mode,
    userId: getCurrentUserId(),
    userName: getCurrentUserName(),
  });
  return response.data.wpsConfig;
};
```

### 4.2 文档保存接口

**接口路径：** `POST /api/case/document/wps/save/<document_id>/`

**请求参数：**
```typescript
FormData {
  file: File;           // 文档文件
  documentId: number;   // 文档ID
}
```

**响应数据：**
```typescript
interface SaveResponse {
  code: number;
  msg: string;
  data: {
    documentId: number;
    filePath: string;
    fileSize: number;
    updateTime: string;
    version: number;
  };
}
```

**实现示例：**
```typescript
export const saveWPSDocument = async (
  documentId: number,
  file: File
): Promise<SaveResult> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('documentId', documentId.toString());
  
  const response = await request.post(
    `/api/case/document/wps/save/${documentId}/`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};
```

### 4.3 文档下载接口

**接口路径：** `GET /api/case/document/wps/download/<document_id>/`

**实现示例：**
```typescript
export const downloadWPSDocument = async (documentId: number): Promise<void> => {
  const response = await request.get(
    `/api/case/document/wps/download/${documentId}/`,
    {
      responseType: 'blob',
    }
  );
  
  // 创建下载链接
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `document_${documentId}.docx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
```

## 五、WPS Office Web SDK集成

### 5.1 安装和引入

**CDN引入方式（官方推荐）**

WPS Office Web SDK主要通过CDN方式引入。有两种方式：

**方式一：在 `index.html` 中直接引入（推荐用于简单项目）**

```html
<!DOCTYPE html>
<html>
<head>
  <!-- WPS Office Web SDK -->
  <script src="https://wwo.wps.cn/office/v1/index.js"></script>
  <!-- 注意：请访问WPS开放平台获取最新的CDN地址 -->
</head>
<body>
  <div id="app"></div>
</body>
</html>
```

**方式二：动态加载（推荐用于Vue项目）**

在需要使用WPS的组件中动态加载SDK，具体实现见5.2节的WPS初始化部分。

**重要提示：**
- WPS Office Web SDK目前没有官方NPM包
- CDN地址请以WPS开放平台官方文档为准：https://open.wps.cn/docs/office
- 建议使用动态加载方式，避免全局污染和提高加载性能

### 5.2 WPS初始化

**实现示例：**
```typescript
// utils/wps-loader.ts
// 动态加载WPS SDK
export const loadWPSSDK = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    // 检查是否已加载
    if (window.WPS) {
      resolve();
      return;
    }
    
    // 动态创建script标签
    const script = document.createElement('script');
    script.src = 'https://wwo.wps.cn/office/v1/index.js';
    script.async = true;
    script.onload = () => {
      if (window.WPS) {
        resolve();
      } else {
        reject(new Error('WPS SDK加载失败'));
      }
    };
    script.onerror = () => {
      reject(new Error('WPS SDK加载失败：网络错误'));
    };
    document.head.appendChild(script);
  });
};

// utils/wps.ts
import { loadWPSSDK } from './wps-loader';

export interface WPSConfig {
  fileUrl: string;
  fileId: string;
  appId: string;
  token: string;
  mode: 'view' | 'edit';
  userId: string;
  userName: string;
  callbackUrl: string;
  saveUrl: string;
  downloadUrl: string;
}

export class WPSManager {
  private instance: any = null;
  
  /**
   * 初始化WPS实例
   */
  async init(config: WPSConfig, container: HTMLElement): Promise<void> {
    // 先加载WPS SDK
    await loadWPSSDK();
    
    // 检查WPS是否可用
    if (!window.WPS) {
      throw new Error('WPS SDK未加载');
    }
    
    return new Promise((resolve, reject) => {
      this.instance = window.WPS.config({
        mount: container,              // 挂载容器
        fileId: config.fileId,          // 文件ID
        appId: config.appId,            // 应用ID
        token: config.token,            // 访问令牌
        mode: config.mode,              // 模式：view/edit
        userId: config.userId,          // 用户ID
        userName: config.userName,      // 用户名
        fileUrl: config.fileUrl,        // 文件URL
        callbackUrl: config.callbackUrl, // 回调地址
        saveUrl: config.saveUrl,        // 保存地址
        downloadUrl: config.downloadUrl, // 下载地址
        onReady: () => {
          console.log('WPS已就绪');
          resolve();
        },
        onError: (error: any) => {
          console.error('WPS初始化错误:', error);
          reject(error);
        },
        onSave: async (fileUrl: string) => {
          // 保存回调
          console.log('文档保存:', fileUrl);
          await this.handleSave(fileUrl);
        },
        onClose: () => {
          console.log('文档已关闭');
          this.destroy();
        },
      });
    });
  }
  
  /**
   * 处理保存
   */
  private async handleSave(fileUrl: string): Promise<void> {
    try {
      // 下载文件
      const response = await fetch(fileUrl);
      const blob = await response.blob();
      const file = new File([blob], 'document.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      
      // 调用后端保存接口
      await saveWPSDocument(this.documentId, file);
      
      // 触发保存成功事件
      this.emit('save', { success: true });
    } catch (error) {
      console.error('保存失败:', error);
      this.emit('save-error', error);
    }
  }
  
  /**
   * 销毁WPS实例
   */
  destroy(): void {
    if (this.instance) {
      this.instance.destroy();
      this.instance = null;
    }
  }
  
  /**
   * 获取WPS实例
   */
  getInstance(): any {
    return this.instance;
  }
}
```

### 5.3 WPS事件处理

**主要事件：**
```typescript
// WPS事件类型
interface WPSEvents {
  onReady: () => void;                    // WPS就绪
  onError: (error: any) => void;          // 错误事件
  onSave: (fileUrl: string) => void;      // 保存事件
  onClose: () => void;                    // 关闭事件
  onChange: () => void;                   // 内容改变
  onPrint: () => void;                    // 打印事件
}
```

## 六、Vue组件实现

### 6.1 WPSViewer组件

**文件：** `components/WPSViewer.vue`

```vue
<template>
  <div class="wps-viewer">
    <div ref="wpsContainer" class="wps-container" :style="containerStyle"></div>
    <div v-if="loading" class="loading-overlay">
      <el-loading text="正在加载文档..." />
    </div>
    <div v-if="error" class="error-message">
      <el-alert :title="error" type="error" show-icon />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { getWPSConfig } from '@/api/document';
import { WPSManager } from '@/utils/wps';
import { ElMessage } from 'element-plus';

interface Props {
  documentId: number;
  mode?: 'view' | 'edit';
  width?: string;
  height?: string;
  autoLoad?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'view',
  width: '100%',
  height: '600px',
  autoLoad: true,
});

const emit = defineEmits<{
  load: [config: any];
  error: [error: Error];
  ready: [];
  close: [];
}>();

const wpsContainer = ref<HTMLElement>();
const loading = ref(false);
const error = ref<string>('');
const wpsManager = ref<WPSManager | null>(null);

const containerStyle = computed(() => ({
  width: props.width,
  height: props.height,
}));

const loadDocument = async () => {
  if (!wpsContainer.value) {
    return;
  }
  
  loading.value = true;
  error.value = '';
  
  try {
    // 获取WPS配置
    const config = await getWPSConfig(props.documentId, props.mode);
    emit('load', config);
    
    // 初始化WPS
    const manager = new WPSManager();
    await manager.init(config, wpsContainer.value);
    wpsManager.value = manager;
    
    emit('ready');
  } catch (err: any) {
    error.value = err.message || '加载文档失败';
    emit('error', err);
    ElMessage.error(error.value);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (props.autoLoad) {
    loadDocument();
  }
});

onBeforeUnmount(() => {
  if (wpsManager.value) {
    wpsManager.value.destroy();
  }
});

defineExpose({
  loadDocument,
  reload: loadDocument,
});
</script>

<style scoped>
.wps-viewer {
  position: relative;
  width: 100%;
  height: 100%;
}

.wps-container {
  width: 100%;
  height: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-message {
  padding: 20px;
}
</style>
```

### 6.2 WPSEditor组件

**文件：** `components/WPSEditor.vue`

```vue
<template>
  <div class="wps-editor">
    <!-- 工具栏 -->
    <div v-if="showToolbar" class="wps-toolbar">
      <el-button-group>
        <el-button @click="handleSave" :loading="saving">
          <el-icon><Document /></el-icon>
          保存
        </el-button>
        <el-button @click="handleDownload">
          <el-icon><Download /></el-icon>
          下载
        </el-button>
        <el-button @click="handleClose">
          <el-icon><Close /></el-icon>
          关闭
        </el-button>
      </el-button-group>
      <div class="toolbar-right">
        <el-tag v-if="hasChanges" type="warning">未保存</el-tag>
        <el-tag v-if="autoSaving" type="info">保存中...</el-tag>
        <el-tag v-if="lastSaveTime" type="success">
          已保存 {{ formatTime(lastSaveTime) }}
        </el-tag>
      </div>
    </div>
    
    <!-- WPS容器 -->
    <WPSViewer
      ref="wpsViewerRef"
      :document-id="documentId"
      mode="edit"
      :width="width"
      :height="editorHeight"
      @ready="handleReady"
      @error="handleError"
      @close="handleClose"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Document, Download, Close } from '@element-plus/icons-vue';
import WPSViewer from './WPSViewer.vue';
import { downloadWPSDocument } from '@/api/document';

interface Props {
  documentId: number;
  userId?: number;
  userName?: string;
  autoSave?: boolean;
  autoSaveInterval?: number;
  showToolbar?: boolean;
  width?: string;
  height?: string;
}

const props = withDefaults(defineProps<Props>(), {
  autoSave: true,
  autoSaveInterval: 300, // 5分钟
  showToolbar: true,
  width: '100%',
  height: '100%',
});

const emit = defineEmits<{
  save: [result: any];
  'save-error': [error: Error];
  change: [];
  close: [];
  error: [error: Error];
}>();

const wpsViewerRef = ref<InstanceType<typeof WPSViewer>>();
const saving = ref(false);
const autoSaving = ref(false);
const hasChanges = ref(false);
const lastSaveTime = ref<Date | null>(null);
let autoSaveTimer: number | null = null;

const editorHeight = computed(() => {
  if (props.showToolbar) {
    return `calc(${props.height} - 50px)`;
  }
  return props.height;
});

const handleReady = () => {
  console.log('WPS编辑器就绪');
  
  // 启动自动保存
  if (props.autoSave) {
    startAutoSave();
  }
};

const handleError = (error: Error) => {
  emit('error', error);
  ElMessage.error('加载文档失败');
};

const handleSave = async () => {
  if (!wpsViewerRef.value) {
    return;
  }
  
  saving.value = true;
  
  try {
    // 触发WPS保存
    const wpsManager = (wpsViewerRef.value as any).wpsManager;
    if (wpsManager && wpsManager.getInstance()) {
      await wpsManager.getInstance().save();
    }
    
    hasChanges.value = false;
    lastSaveTime.value = new Date();
    
    emit('save', { success: true });
    ElMessage.success('保存成功');
  } catch (error: any) {
    emit('save-error', error);
    ElMessage.error('保存失败: ' + error.message);
  } finally {
    saving.value = false;
  }
};

const handleDownload = async () => {
  try {
    await downloadWPSDocument(props.documentId);
    ElMessage.success('下载成功');
  } catch (error: any) {
    ElMessage.error('下载失败: ' + error.message);
  }
};

const handleClose = async () => {
  if (hasChanges.value) {
    try {
      await ElMessageBox.confirm(
        '文档有未保存的更改，是否保存？',
        '提示',
        {
          confirmButtonText: '保存',
          cancelButtonText: '不保存',
          type: 'warning',
        }
      );
      await handleSave();
    } catch {
      // 用户取消
    }
  }
  
  emit('close');
};

const startAutoSave = () => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer);
  }
  
  autoSaveTimer = window.setInterval(async () => {
    if (hasChanges.value) {
      autoSaving.value = true;
      try {
        await handleSave();
      } catch (error) {
        console.error('自动保存失败:', error);
      } finally {
        autoSaving.value = false;
      }
    }
  }, props.autoSaveInterval * 1000);
};

const formatTime = (date: Date): string => {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  
  if (minutes < 1) {
    return '刚刚';
  } else if (minutes < 60) {
    return `${minutes}分钟前`;
  } else {
    const hours = Math.floor(minutes / 60);
    return `${hours}小时前`;
  }
};

onMounted(() => {
  // 监听内容改变
  document.addEventListener('keydown', () => {
    hasChanges.value = true;
    emit('change');
  });
});

onBeforeUnmount(() => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer);
  }
});

defineExpose({
  save: handleSave,
  download: handleDownload,
  close: handleClose,
});
</script>

<style scoped>
.wps-editor {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.wps-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
}

.toolbar-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
```

## 七、路由配置

### 7.1 文档预览页面

**文件：** `views/document/Preview.vue`

```vue
<template>
  <div class="document-preview">
    <el-page-header @back="handleBack">
      <template #content>
        <span>{{ documentName }}</span>
      </template>
    </el-page-header>
    
    <WPSViewer
      :document-id="documentId"
      mode="view"
      height="calc(100vh - 80px)"
      @ready="handleReady"
      @error="handleError"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import WPSViewer from '@/components/WPSViewer.vue';
import { getDocumentDetail } from '@/api/document';

const route = useRoute();
const router = useRouter();

const documentId = ref(Number(route.params.id));
const documentName = ref('');

const handleBack = () => {
  router.back();
};

const handleReady = () => {
  console.log('文档加载完成');
};

const handleError = (error: Error) => {
  ElMessage.error('加载文档失败');
  console.error(error);
};

onMounted(async () => {
  try {
    const doc = await getDocumentDetail(documentId.value);
    documentName.value = doc.documentName;
  } catch (error) {
    console.error('获取文档信息失败:', error);
  }
});
</script>
```

### 7.2 文档编辑页面

**文件：** `views/document/Edit.vue`

```vue
<template>
  <div class="document-edit">
    <el-page-header @back="handleBack">
      <template #content>
        <span>{{ documentName }}</span>
      </template>
    </el-page-header>
    
    <WPSEditor
      :document-id="documentId"
      :user-id="currentUserId"
      :user-name="currentUserName"
      :auto-save="true"
      :auto-save-interval="300"
      height="calc(100vh - 80px)"
      @save="handleSave"
      @save-error="handleSaveError"
      @close="handleClose"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import WPSEditor from '@/components/WPSEditor.vue';
import { getDocumentDetail } from '@/api/document';
import { useUserStore } from '@/stores/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const documentId = ref(Number(route.params.id));
const documentName = ref('');
const currentUserId = ref(userStore.userId);
const currentUserName = ref(userStore.userName);

const handleBack = () => {
  router.back();
};

const handleSave = (result: any) => {
  console.log('保存成功:', result);
};

const handleSaveError = (error: Error) => {
  console.error('保存失败:', error);
};

const handleClose = () => {
  router.back();
};

onMounted(async () => {
  try {
    const doc = await getDocumentDetail(documentId.value);
    documentName.value = doc.documentName;
  } catch (error) {
    console.error('获取文档信息失败:', error);
  }
});
</script>
```

### 7.3 路由配置

**文件：** `router/index.ts`

```typescript
import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/document/preview/:id',
    name: 'DocumentPreview',
    component: () => import('@/views/document/Preview.vue'),
    meta: {
      title: '文档预览',
      requiresAuth: true,
    },
  },
  {
    path: '/document/edit/:id',
    name: 'DocumentEdit',
    component: () => import('@/views/document/Edit.vue'),
    meta: {
      title: '文档编辑',
      requiresAuth: true,
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
```

## 八、API服务封装

### 8.1 文档API服务

**文件：** `api/document.ts`

```typescript
import request from '@/utils/request';

// WPS配置类型
export interface WPSConfig {
  fileUrl: string;
  fileId: string;
  appId: string;
  token: string;
  mode: 'view' | 'edit';
  userId: string;
  userName: string;
  callbackUrl: string;
  saveUrl: string;
  downloadUrl: string;
}

// 获取WPS配置
export const getWPSConfig = async (
  documentId: number,
  mode: 'view' | 'edit' = 'edit'
): Promise<WPSConfig> => {
  const response = await request.post('/api/case/document/wps/edit-config/', {
    documentId,
    mode,
  });
  return response.data.wpsConfig;
};

// 保存WPS文档
export const saveWPSDocument = async (
  documentId: number,
  file: File
): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('documentId', documentId.toString());
  
  const response = await request.post(
    `/api/case/document/wps/save/${documentId}/`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

// 下载WPS文档
export const downloadWPSDocument = async (documentId: number): Promise<void> => {
  const response = await request.get(
    `/api/case/document/wps/download/${documentId}/`,
    {
      responseType: 'blob',
    }
  );
  
  // 创建下载链接
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `document_${documentId}.docx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// 获取文档详情
export const getDocumentDetail = async (documentId: number): Promise<any> => {
  const response = await request.get(`/api/case/documents/${documentId}/`);
  return response.data;
};
```

## 九、使用示例

### 9.1 在页面中使用预览组件

```vue
<template>
  <div>
    <WPSViewer
      :document-id="123"
      mode="view"
      height="600px"
      @ready="handleReady"
      @error="handleError"
    />
  </div>
</template>

<script setup lang="ts">
import WPSViewer from '@/components/WPSViewer.vue';

const handleReady = () => {
  console.log('文档已加载');
};

const handleError = (error: Error) => {
  console.error('加载失败:', error);
};
</script>
```

### 9.2 在页面中使用编辑组件

```vue
<template>
  <div>
    <WPSEditor
      :document-id="123"
      :user-id="456"
      user-name="张三"
      :auto-save="true"
      :auto-save-interval="300"
      height="600px"
      @save="handleSave"
      @save-error="handleSaveError"
    />
  </div>
</template>

<script setup lang="ts">
import WPSEditor from '@/components/WPSEditor.vue';
import { ElMessage } from 'element-plus';

const handleSave = (result: any) => {
  ElMessage.success('保存成功');
};

const handleSaveError = (error: Error) => {
  ElMessage.error('保存失败');
};
</script>
```

## 十、错误处理

### 10.1 错误类型

**常见错误：**
- 网络错误：无法连接到服务器
- 配置错误：WPS配置获取失败
- 权限错误：用户无权限访问文档
- 加载错误：文档加载失败
- 保存错误：文档保存失败

### 10.2 错误处理示例

```typescript
// 统一错误处理
const handleWPSError = (error: any) => {
  let message = '操作失败';
  
  if (error.response) {
    // 服务器返回错误
    switch (error.response.status) {
      case 401:
        message = '未授权，请重新登录';
        break;
      case 403:
        message = '无权限访问此文档';
        break;
      case 404:
        message = '文档不存在';
        break;
      case 500:
        message = '服务器错误';
        break;
      default:
        message = error.response.data?.msg || '操作失败';
    }
  } else if (error.request) {
    // 请求已发出但没有收到响应
    message = '网络错误，请检查网络连接';
  } else {
    // 其他错误
    message = error.message || '操作失败';
  }
  
  ElMessage.error(message);
  console.error('WPS错误:', error);
};
```

## 十一、性能优化

### 11.1 懒加载

**按需加载WPS SDK（已在5.1节中实现）：**
- 使用动态加载方式，只在需要时加载WPS SDK
- 避免在页面初始化时就加载，提高首屏加载速度
- 可以在路由级别或组件级别按需加载

### 11.2 缓存配置

**缓存WPS配置：**
```typescript
// 使用缓存避免重复请求
const configCache = new Map<number, WPSConfig>();

export const getWPSConfigWithCache = async (
  documentId: number,
  mode: 'view' | 'edit' = 'edit'
): Promise<WPSConfig> => {
  const cacheKey = `${documentId}_${mode}`;
  
  if (configCache.has(cacheKey)) {
    return configCache.get(cacheKey)!;
  }
  
  const config = await getWPSConfig(documentId, mode);
  configCache.set(cacheKey, config);
  
  // 5分钟后清除缓存
  setTimeout(() => {
    configCache.delete(cacheKey);
  }, 5 * 60 * 1000);
  
  return config;
};
```

## 十二、依赖安装

### 12.1 无需NPM包安装

**WPS Office Web SDK通过CDN方式引入，无需安装NPM包。**

### 12.2 类型定义（TypeScript项目）

如果使用TypeScript，需要创建类型定义文件：

**文件：** `types/wps.d.ts`

```typescript
// WPS Office Web SDK 类型定义
declare global {
  interface Window {
    WPS: {
      config: (options: WPSConfigOptions) => any;
      [key: string]: any;
    };
  }
}

interface WPSConfigOptions {
  mount: HTMLElement;
  fileId: string;
  appId: string;
  token: string;
  mode: 'view' | 'edit';
  userId: string;
  userName: string;
  fileUrl: string;
  callbackUrl?: string;
  saveUrl?: string;
  downloadUrl?: string;
  onReady?: () => void;
  onError?: (error: any) => void;
  onSave?: (fileUrl: string) => void;
  onClose?: () => void;
  onChange?: () => void;
  [key: string]: any;
}

export {};
```

**在 `tsconfig.json` 中配置：**
```json
{
  "compilerOptions": {
    "types": ["./types/wps.d.ts"]
  }
}
```

## 十三、开发步骤建议

### Phase 1：环境准备（0.5天）
1. 配置WPS SDK CDN地址（或使用动态加载方式）
2. 配置API请求基础URL
3. 创建基础组件结构和类型定义

### Phase 2：核心组件开发（2-3天）
1. 实现WPSManager工具类
2. 实现WPSViewer组件
3. 实现WPSEditor组件
4. 单元测试

### Phase 3：API对接（1-2天）
1. 封装API服务
2. 实现配置获取接口
3. 实现保存接口
4. 实现下载接口
5. 接口测试

### Phase 4：页面集成（1-2天）
1. 创建文档预览页面
2. 创建文档编辑页面
3. 配置路由
4. 页面测试

### Phase 5：功能完善（1-2天）
1. 错误处理
2. 加载状态提示
3. 自动保存功能
4. 工具栏功能
5. 性能优化

### Phase 6：测试和优化（1-2天）
1. 功能测试
2. 兼容性测试
3. 性能测试
4. 用户体验优化
5. 文档编写

## 十四、测试用例

### 14.1 功能测试

**文档预览：**
- [ ] 正常加载文档
- [ ] 大文档加载（50MB+）
- [ ] 网络错误处理
- [ ] 权限错误处理
- [ ] 文档不存在处理

**文档编辑：**
- [ ] 正常编辑文档
- [ ] 保存功能
- [ ] 自动保存功能
- [ ] 下载功能
- [ ] 关闭提示未保存更改

### 14.2 兼容性测试

- [ ] Chrome浏览器
- [ ] Firefox浏览器
- [ ] Safari浏览器
- [ ] Edge浏览器
- [ ] 移动端浏览器

### 14.3 性能测试

- [ ] 大文档加载性能
- [ ] 编辑响应性能
- [ ] 内存占用
- [ ] 网络请求优化

## 十五、注意事项

### 15.1 浏览器兼容性

- WPS Office Web SDK需要现代浏览器支持
- 建议使用Chrome、Firefox、Safari、Edge等主流浏览器
- IE浏览器不支持

### 15.2 网络要求

- 需要稳定的网络连接
- 建议使用HTTPS协议
- 注意跨域问题

### 15.3 安全性

- 所有API请求需要携带认证Token
- 文档URL需要签名验证
- 注意XSS攻击防护

## 十六、技术文档参考

- WPS Office Web SDK文档：https://open.wps.cn/docs/office
- WPS开放平台：https://open.wps.cn/
- Vue3文档：https://cn.vuejs.org/
- Element Plus文档：https://element-plus.org/zh-CN/

## 十七、后续扩展

- 支持Excel和PPT文档
- 多人协同编辑
- 文档评论和批注
- 文档历史版本查看
- 移动端适配优化
- 离线编辑支持

