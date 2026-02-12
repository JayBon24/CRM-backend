# WPS SDK CDN 加载问题排查指南

## 问题描述

**错误信息：** `WPS SDK加载失败：网络错误，请检查CDN地址是否正确`

## 可能原因

### 1. CDN 地址不正确

**当前文档中的 CDN 地址：**
```
https://wwo.wps.cn/office/v1/index.js
```

**⚠️ 注意：** 这个地址可能已经过时或需要更新。请访问 WPS 开放平台获取最新的 CDN 地址：
- WPS 开放平台：https://open.wps.cn/
- 官方文档：https://open.wps.cn/docs/office

### 2. 网络连接问题

- 检查是否能访问 `wwo.wps.cn` 域名
- 检查防火墙是否阻止了 CDN 访问
- 检查代理设置是否正确

### 3. 跨域问题（CORS）

如果使用内网穿透或域名访问，可能存在跨域限制。

### 4. CDN 地址需要配置

建议将 CDN 地址配置为可配置项，而不是硬编码。

## 解决方案

### 方案一：检查并更新 CDN 地址

1. **访问 WPS 开放平台获取最新地址**
   - 访问：https://open.wps.cn/docs/office
   - 查看最新的 CDN 引入方式

2. **测试 CDN 地址是否可访问**
   ```bash
   # 在浏览器中直接访问
   https://wwo.wps.cn/office/v1/index.js
   
   # 或使用 curl 测试
   curl -I https://wwo.wps.cn/office/v1/index.js
   ```

3. **如果 CDN 不可访问，尝试其他 CDN 地址**
   - 查看 WPS 官方文档是否有其他 CDN 地址
   - 或使用私有化部署方案

### 方案二：使用后端配置 CDN 地址

在后端 API 返回的 WPS 配置中包含 CDN 地址，让前端动态加载：

**后端修改（views.py）：**

```python
@action(detail=True, methods=['post'], url_path='wps/edit-config', permission_classes=[])
def wps_edit_config(self, request, pk=None):
    """获取WPS编辑配置"""
    try:
        document = self.get_object()
        mode = request.data.get('mode', 'edit')
        
        # 从环境变量或配置中获取 CDN 地址（支持配置）
        wps_cdn_url = os.getenv('WPS_CDN_URL', 'https://wwo.wps.cn/office/v1/index.js')
        
        # ... 其他配置 ...
        
        wps_config = {
            'fileUrl': file_url,
            'fileId': str(document.id),
            'appId': os.getenv('WPS_APP_ID', 'wps_app_id_placeholder'),
            'token': token,
            'mode': mode,
            'userId': str(user_id) if user_id else '0',
            'userName': user_name or '用户',
            'callbackUrl': callback_url,
            'saveUrl': save_url,
            'downloadUrl': download_url,
            'cdnUrl': wps_cdn_url,  # ✅ 新增：CDN 地址
        }
        
        return DetailResponse(
            data={
                'documentId': document.id,
                'wpsConfig': wps_config
            },
            msg="WPS配置生成成功"
        )
    except Exception as e:
        logger.error(f"生成WPS配置失败: {str(e)}")
        return ErrorResponse(msg=f"生成WPS配置失败: {str(e)}")
```

**前端修改：**

```typescript
// utils/wps-loader.ts
export const loadWPSSDK = (cdnUrl?: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    // 检查是否已加载
    if (window.WPS) {
      resolve();
      return;
    }
    
    // 使用配置的 CDN 地址，如果没有则使用默认值
    const defaultCDN = 'https://wwo.wps.cn/office/v1/index.js';
    const scriptUrl = cdnUrl || defaultCDN;
    
    // 动态创建script标签
    const script = document.createElement('script');
    script.src = scriptUrl;
    script.async = true;
    script.onload = () => {
      if (window.WPS) {
        resolve();
      } else {
        reject(new Error('WPS SDK加载失败：SDK未正确初始化'));
      }
    };
    script.onerror = () => {
      reject(new Error(`WPS SDK加载失败：网络错误，请检查CDN地址是否正确\nCDN地址: ${scriptUrl}`));
    };
    document.head.appendChild(script);
  });
};

// 使用配置中的 CDN 地址
const wpsConfig = await getWPSConfig(documentId, mode);
await loadWPSSDK(wpsConfig.cdnUrl);  // 使用后端返回的 CDN 地址
```

### 方案三：添加 CDN 备用地址

如果主 CDN 不可用，可以尝试备用 CDN：

```typescript
const CDN_URLS = [
  'https://wwo.wps.cn/office/v1/index.js',
  'https://wpsapi.wps.cn/office/v1/index.js',  // 备用地址（需要确认）
  // 其他可能的 CDN 地址
];

export const loadWPSSDK = async (): Promise<void> => {
  for (const cdnUrl of CDN_URLS) {
    try {
      await loadFromCDN(cdnUrl);
      return;  // 成功加载
    } catch (error) {
      console.warn(`CDN ${cdnUrl} 加载失败，尝试下一个`, error);
      continue;
    }
  }
  throw new Error('所有 CDN 地址都加载失败');
};

const loadFromCDN = (url: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    if (window.WPS) {
      resolve();
      return;
    }
    
    const script = document.createElement('script');
    script.src = url;
    script.async = true;
    script.onload = () => {
      if (window.WPS) {
        resolve();
      } else {
        reject(new Error('SDK未正确初始化'));
      }
    };
    script.onerror = () => reject(new Error(`CDN加载失败: ${url}`));
    document.head.appendChild(script);
  });
};
```

### 方案四：私有化部署（企业版）

如果 CDN 不可用，可以考虑私有化部署 WPS Office 服务器：

1. 联系 WPS 官方获取私有化部署方案
2. 配置自己的 WPS 服务器地址
3. 在环境变量中配置 `WPS_SERVER_URL`

## 环境变量配置

在 `conf/env.py` 中添加：

```python
# WPS CDN 配置
WPS_CDN_URL = os.getenv('WPS_CDN_URL', 'https://wwo.wps.cn/office/v1/index.js')
WPS_SERVER_URL = os.getenv('WPS_SERVER_URL', 'https://wwo.wps.cn')
```

## 调试步骤

1. **检查 CDN 地址是否可访问**
   ```bash
   # 在浏览器控制台执行
   fetch('https://wwo.wps.cn/office/v1/index.js')
     .then(res => console.log('CDN 可访问:', res.status))
     .catch(err => console.error('CDN 不可访问:', err));
   ```

2. **检查网络请求**
   - 打开浏览器开发者工具（F12）
   - 查看 Network 标签
   - 查找 `index.js` 的请求
   - 查看请求状态和错误信息

3. **检查控制台错误**
   - 查看浏览器控制台的错误信息
   - 查看是否有 CORS 错误
   - 查看是否有网络错误

4. **测试 CDN 地址**
   - 在浏览器中直接访问 CDN 地址
   - 确认返回的是 JavaScript 代码

## 最新 CDN 地址获取

请访问以下地址获取最新的 CDN 地址和集成方式：

- **WPS 开放平台：** https://open.wps.cn/
- **官方文档：** https://open.wps.cn/docs/office
- **API 参考：** https://open.wps.cn/docs/office/api

## 联系支持

如果以上方案都无法解决问题，建议：

1. 联系 WPS 官方技术支持
2. 提供详细的错误信息和环境配置
3. 提供网络请求的详细信息（Network 标签截图）

## 注意事项

1. **CDN 地址可能会变更**：建议定期检查 WPS 官方文档，确保使用最新的 CDN 地址
2. **网络环境**：确保服务器能够访问外网 CDN
3. **HTTPS**：确保使用 HTTPS 协议访问 CDN（某些浏览器可能阻止 HTTP）
4. **版本兼容性**：确保 WPS SDK 版本与后端 API 兼容

