# WPS 回调服务实现规范

根据 [WPS 官方文档](https://solution.wps.cn/docs/callback/preview.html) 的要求，后端需要实现以下回调接口。

## 一、文档预览接口

### 1.1 获取文件下载地址

**接口路径：** `GET /v3/3rd/files/:file_id/download`

**说明：** 该接口返回文件下载地址，WPS SDK 会使用这个地址在 iframe 中加载文档。

**返回值：**
```json
{
  "code": 0,
  "data": {
    "url": "http://127.0.0.1:8000/api/case/documents/238/public_download/"
  }
}
```

**重要提示：**
- `url` 字段返回的地址就是 `public_download` 接口
- 该地址需要确保**外网可访问**（WPS服务器需要能访问）
- 该地址需要排除访问时防火墙的限制

### 1.2 文件下载接口（public_download）

**接口路径：** `/api/case/documents/{id}/public_download/`

**说明：** 这是 WPS SDK 在 iframe 中实际加载的接口，需要**直接返回文件内容**，而不是 JSON。

**关键要求：**

1. **返回文件内容（必需）**
   - 必须直接返回文件二进制流
   - 不能返回 JSON 格式
   - 设置正确的 `Content-Type`：
     - Word: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
     - Excel: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
     - PPT: `application/vnd.openxmlformats-officedocument.presentationml.presentation`

2. **响应头设置（必需）**
   - **不能设置** `X-Frame-Options: deny`
   - 可以设置为 `X-Frame-Options: SAMEORIGIN`（允许同源iframe）
   - 或者完全不设置该响应头
   - 确保 `Content-Security-Policy` 的 `frame-ancestors` 允许 iframe 加载

3. **Referer 防盗链（可选）**
   - 如果设置了 Referer 防盗链，需要在 `/v3/3rd/files/:file_id/download` 的返回值中返回自定义 Referer 请求头

**Django 实现示例：**

```python
from django.http import HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods
import os

@require_http_methods(["GET"])
def public_download(request, document_id):
    """
    WPS 文件下载接口
    直接返回文件内容，用于 iframe 加载
    """
    try:
        # 获取文档对象
        document = CaseDocument.objects.get(id=document_id)
        
        # 获取文件路径
        file_path = document.file_path
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return HttpResponse(
                json.dumps({"code": 40004, "message": "file not exists"}),
                content_type="application/json",
                status=404
            )
        
        # 打开文件
        file = open(file_path, 'rb')
        
        # 创建响应
        response = FileResponse(
            file,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        # 设置响应头
        response['Content-Disposition'] = f'inline; filename="{document.name}"'
        
        # 重要：不设置 X-Frame-Options: deny
        # 或者设置为 SAMEORIGIN
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # 或者完全不设置该响应头
        # del response['X-Frame-Options']
        
        # 确保 Content-Security-Policy 允许 iframe
        response['Content-Security-Policy'] = "frame-ancestors 'self'"
        
        return response
        
    except CaseDocument.DoesNotExist:
        return HttpResponse(
            json.dumps({"code": 40004, "message": "file not exists"}),
            content_type="application/json",
            status=404
        )
    except Exception as e:
        # 错误处理：确保错误页面也不设置 X-Frame-Options: deny
        error_response = HttpResponse(
            json.dumps({"code": 50000, "message": str(e)}),
            content_type="application/json",
            status=500
        )
        # 重要：错误页面也不能设置 X-Frame-Options: deny
        error_response['X-Frame-Options'] = 'SAMEORIGIN'
        return error_response
```

## 二、其他必需的回调接口

根据官方文档，还需要实现以下接口：

### 2.1 获取文件信息

**接口路径：** `GET /v3/3rd/files/:file_id`

**返回值：**
```json
{
  "code": 0,
  "data": {
    "id": "238",
    "name": "文档名称.docx",
    "version": 1,
    "size": 1024,
    "create_time": 1234567890,
    "modify_time": 1234567890
  }
}
```

### 2.2 文档用户权限

**接口路径：** `GET /v3/3rd/files/:file_id/permission`

**返回值：**
```json
{
  "code": 0,
  "data": {
    "user_id": "404",
    "read": 1,
    "update": 1,
    "download": 1,
    "rename": 1,
    "history": 1,
    "copy": 1,
    "print": 1,
    "saveas": 1,
    "comment": 1
  }
}
```

### 2.3 文档保存接口

**接口路径：** `POST /v3/3rd/files/:file_id/save`

**说明：** 用于保存文档编辑后的内容

### 2.4 用户信息接口

**接口路径：** `GET /v3/3rd/users`

**说明：** 获取用户信息

## 三、回调配置

### 3.1 回调网关配置

根据 [回调网关文档](https://solution.wps.cn/docs/callback/gateway.html)，需要在 WPS 控制台配置：

1. **回调网关地址**：部署在公网的回调服务地址
2. **回调接口路径**：如上所述的各个接口路径
3. **回调请求签名**：使用 WPS-2 签名算法

### 3.2 回调请求签名

WPS 服务器的回调请求会携带以下请求头：

| 请求头 | 说明 |
|--------|------|
| `Authorization` | WPS-2 签名 |
| `X-App-Id` | 应用ID |
| `X-WebOffice-Token` | 用户凭证（前端初始化时传入的token） |
| `X-Request-Id` | 请求ID |
| `X-User-Query` | URL查询参数 |

后端需要：
1. 验证签名（使用 AppId 和 AppSecret）
2. 从 `X-WebOffice-Token` 获取用户凭证进行鉴权

## 四、常见问题

### 4.1 X-Frame-Options 阻止 iframe 加载

**问题：** 浏览器报错 `NS_ERROR_XFO_VIOLATION` 或 `Refused to display...in a frame because it set X-Frame-Options to deny`

**解决方案：**
1. 确保 `public_download` 接口不设置 `X-Frame-Options: deny`
2. 可以设置为 `X-Frame-Options: SAMEORIGIN`
3. 或者完全不设置该响应头
4. 检查 `Content-Security-Policy` 的 `frame-ancestors` 设置

### 4.2 500 内部服务器错误

**问题：** `public_download` 接口返回 500 错误

**可能原因：**
1. 文件不存在
2. 数据库字段缺失（如 `wps_file_id`）
3. 权限验证失败
4. 文件读取失败

**解决方案：**
1. 检查后端日志，查看具体错误信息
2. 确保数据库表结构完整
3. 确保文件路径正确
4. 确保用户有访问权限

### 4.3 回调服务部署要求

**重要要求：**
1. 回调服务必须部署在**公网**（WPS服务器需要能访问）
2. 本地开发环境（127.0.0.1）无法被 WPS 服务器访问
3. 需要使用内网穿透工具（如 ngrok）或部署到公网服务器

## 五、官方文档链接

- [回调服务概述](https://solution.wps.cn/docs/callback/summary.html)
- [文档预览接口](https://solution.wps.cn/docs/callback/preview.html)
- [文档保存接口](https://solution.wps.cn/docs/callback/save.html)
- [用户信息接口](https://solution.wps.cn/docs/callback/user.html)
- [回调网关](https://solution.wps.cn/docs/callback/gateway.html)

## 六、前端与后端的配合

### 6.1 前端配置

前端通过 `getWPSConfig` 接口获取配置，后端返回的 `fileUrl` 应该是：

```
http://127.0.0.1:8000/api/case/documents/238/public_download/
```

这个 URL 会被 WPS SDK 设置为 iframe 的 `src`，浏览器会自动加载。

### 6.2 后端实现要点

1. **`public_download` 接口必须返回文件内容**（不是JSON）
2. **响应头不能设置 `X-Frame-Options: deny`**
3. **确保接口返回 200 状态码**（不是 500）
4. **设置正确的 Content-Type**

## 七、测试建议

1. **直接访问测试：** 在浏览器中直接访问 `public_download` 接口，确认：
   - 能正常下载文件
   - 响应头中没有 `X-Frame-Options: deny`
   - 返回 200 状态码

2. **Network 面板检查：** 在浏览器开发者工具的 Network 面板中：
   - 查看 `public_download` 请求的响应头
   - 确认 `X-Frame-Options` 设置
   - 确认状态码和响应内容

3. **iframe 测试：** 在 HTML 中创建一个 iframe 测试：
   ```html
   <iframe src="http://127.0.0.1:8000/api/case/documents/238/public_download/"></iframe>
   ```
   确认 iframe 能正常加载，浏览器控制台没有 X-Frame-Options 错误

