# WPS init 方式后端接口规范

## 概述

前端已改为使用 `WebOfficeSDK.init()` 方式（官方推荐），后端需要实现WPS官方规范的回调接口。

## 前端调用方式

```javascript
const instance = WebOfficeSDK.init({
  appId: 'your_app_id',        // WPS应用ID
  fileId: '238',                // 文件ID（文档ID）
  officeType: 'w',              // w=Writer(文字), s=Spreadsheet(表格), p=Presentation(演示), pdf=PDF
  token: 'user_token',          // 用户认证token
  mount: containerElement       // 挂载点DOM元素
})

await instance.ready()  // 等待WPS实例就绪
```

## 后端需要实现的接口

### 1. 前端配置接口（新增）

**接口路径：** `POST /api/case/documents/{documentId}/wps/init-config/`

**说明：** 前端调用此接口获取 WPS 初始化所需的配置

**请求参数：**
```json
{
  "mode": "edit",      // "view" 或 "edit"
  "userId": 123,       // 可选
  "userName": "张三"   // 可选
}
```

**响应格式：**
```json
{
  "code": 0,
  "data": {
    "appId": "your_wps_app_id",      // WPS应用ID（从WPS开放平台申请）
    "fileId": "238",                  // 文件ID（通常就是documentId）
    "officeType": "w",                // 文件类型：w/s/p/pdf
    "token": "user_jwt_token",        // 用户认证token（用于回调接口鉴权）
    "endpoint": "http://your-domain.com"  // 可选：回调服务地址
  }
}
```

**officeType 说明：**
- `w`: Word文档（.doc, .docx）
- `s`: Excel表格（.xls, .xlsx）
- `p`: PowerPoint演示（.ppt, .pptx）
- `pdf`: PDF文档（.pdf）

---

### 2. WPS 回调接口（必需）

WPS SDK会自动调用以下回调接口，后端必须按照WPS官方规范实现：

#### 2.1 获取文件下载地址

**接口路径：** `GET /v3/3rd/files/{fileId}/download`

**说明：** 返回文件的下载地址，WPS会从这个地址加载文件内容

**请求头：**
```
Authorization: WPS-2 签名
X-App-Id: your_app_id
X-WebOffice-Token: user_token（前端init时传入的token）
X-Request-Id: 请求ID
```

**响应格式：**
```json
{
  "code": 0,
  "data": {
    "url": "http://your-domain.com/api/case/documents/238/public_download/"
  }
}
```

**重要：**
- `url` 返回的地址必须是**可直接下载文件**的地址
- 该地址返回的文件**必须设置** `Content-Disposition: inline`
- **必须允许iframe加载**（不能设置 `X-Frame-Options: deny`）

---

#### 2.2 文件下载接口（public_download）

**接口路径：** `/api/case/documents/{id}/public_download/`

**说明：** 直接返回文件二进制内容，供WPS在iframe中加载

**响应头设置（关键）：**
```python
# Django 示例
response = FileResponse(file, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# ⚠️ 必须设置以下响应头
response['Content-Disposition'] = f'inline; filename="{document.name}"'  # 必须是 inline
response['X-Frame-Options'] = 'SAMEORIGIN'  # 或不设置，不能是 deny
response['Content-Security-Policy'] = "frame-ancestors 'self'"
```

**关键点：**
1. **Content-Disposition 必须设置为 `inline`**（不能是 `attachment`，不能未设置）
2. **X-Frame-Options 不能设置为 `deny`**（可以是 `SAMEORIGIN` 或不设置）
3. 必须返回文件二进制流，不能返回JSON

---

#### 2.3 获取文件信息

**接口路径：** `GET /v3/3rd/files/{fileId}`

**说明：** 获取文件的元信息

**请求头：** 同2.1

**响应格式：**
```json
{
  "code": 0,
  "data": {
    "id": "238",
    "name": "文档名称.docx",
    "version": 1,
    "size": 1024000,
    "create_time": 1234567890,
    "modify_time": 1234567890,
    "creator": "创建人",
    "modifier": "修改人"
  }
}
```

---

#### 2.4 获取用户权限

**接口路径：** `GET /v3/3rd/files/{fileId}/permission`

**说明：** 获取当前用户对文件的操作权限

**请求头：** 同2.1

**响应格式：**
```json
{
  "code": 0,
  "data": {
    "user_id": "123",
    "read": 1,        // 1=允许，0=禁止
    "update": 1,      // 允许编辑
    "download": 1,    // 允许下载
    "rename": 0,      // 禁止重命名
    "history": 1,     // 允许查看历史
    "copy": 1,        // 允许复制
    "print": 1,       // 允许打印
    "saveas": 1,      // 允许另存为
    "comment": 1      // 允许评论
  }
}
```

---

#### 2.5 保存文件

**接口路径：** `POST /v3/3rd/files/{fileId}/save`

**说明：** 保存用户编辑后的文件

**请求头：** 同2.1

**请求体：** 文件二进制流（multipart/form-data）

**响应格式：**
```json
{
  "code": 0,
  "data": {
    "version": 2,
    "modify_time": 1234567890
  }
}
```

---

#### 2.6 获取用户信息

**接口路径：** `GET /v3/3rd/users`

**说明：** 获取当前用户信息（用于显示编辑者头像等）

**请求头：** 同2.1

**响应格式：**
```json
{
  "code": 0,
  "data": {
    "id": "123",
    "name": "张三",
    "avatar_url": "http://example.com/avatar.jpg"
  }
}
```

---

## 回调接口鉴权

### WPS-2 签名算法

WPS的回调请求会携带签名，后端需要验证签名：

```python
import hashlib
import hmac

def verify_wps_signature(request, app_secret):
    """
    验证WPS回调请求的签名
    """
    # 从请求头获取签名信息
    authorization = request.headers.get('Authorization')  # 格式：WPS-2 <signature>
    app_id = request.headers.get('X-App-Id')
    request_id = request.headers.get('X-Request-Id')
    
    # 解析签名
    if not authorization or not authorization.startswith('WPS-2 '):
        return False
    
    signature = authorization[6:]  # 去掉 "WPS-2 " 前缀
    
    # 构建签名字符串
    # 格式：HTTP方法 + 路径 + 查询参数 + 请求体（如果有）
    method = request.method
    path = request.path
    query_string = request.query_string.decode('utf-8')
    body = request.body.decode('utf-8') if request.body else ''
    
    sign_string = f"{method}{path}{query_string}{body}"
    
    # 计算HMAC-SHA256签名
    expected_signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature == expected_signature
```

### Token 验证

```python
def verify_wps_token(request):
    """
    验证WPS回调请求的用户token
    """
    token = request.headers.get('X-WebOffice-Token')
    
    if not token:
        return None
    
    # 解析JWT token，获取用户信息
    try:
        user_info = decode_jwt(token)
        return user_info
    except Exception as e:
        return None
```

---

## Django 完整实现示例

### 配置

```python
# settings.py
WPS_APP_ID = 'your_wps_app_id'
WPS_APP_SECRET = 'your_wps_app_secret'
```

### 前端配置接口

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import jwt
import os

@require_http_methods(["POST"])
def get_wps_init_config(request, document_id):
    """
    返回WPS初始化配置
    """
    try:
        # 获取文档
        document = CaseDocument.objects.get(id=document_id)
        
        # 获取当前用户
        user = request.user
        
        # 生成token（JWT）
        token = jwt.encode({
            'user_id': user.id,
            'username': user.username,
            'document_id': document_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, settings.WPS_APP_SECRET, algorithm='HS256')
        
        # 判断文件类型
        file_ext = os.path.splitext(document.name)[1].lower()
        office_type_map = {
            '.doc': 'w', '.docx': 'w',
            '.xls': 's', '.xlsx': 's',
            '.ppt': 'p', '.pptx': 'p',
            '.pdf': 'pdf'
        }
        office_type = office_type_map.get(file_ext, 'w')
        
        return JsonResponse({
            'code': 0,
            'data': {
                'appId': settings.WPS_APP_ID,
                'fileId': str(document_id),
                'officeType': office_type,
                'token': token,
                'endpoint': request.build_absolute_uri('/')[:-1]  # 去掉末尾的 /
            }
        })
    except CaseDocument.DoesNotExist:
        return JsonResponse({
            'code': 40004,
            'message': 'file not exists'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'code': 50000,
            'message': str(e)
        }, status=500)
```

### 文件下载地址接口

```python
@require_http_methods(["GET"])
def wps_file_download_url(request, file_id):
    """
    返回文件下载地址
    WPS回调接口：GET /v3/3rd/files/{file_id}/download
    """
    # 验证签名和token
    if not verify_wps_signature(request, settings.WPS_APP_SECRET):
        return JsonResponse({'code': 40101, 'message': 'invalid signature'}, status=401)
    
    user_info = verify_wps_token(request)
    if not user_info:
        return JsonResponse({'code': 40102, 'message': 'invalid token'}, status=401)
    
    try:
        # 构建文件下载URL
        download_url = request.build_absolute_uri(
            f'/api/case/documents/{file_id}/public_download/'
        )
        
        return JsonResponse({
            'code': 0,
            'data': {
                'url': download_url
            }
        })
    except Exception as e:
        return JsonResponse({
            'code': 50000,
            'message': str(e)
        }, status=500)
```

### 文件下载接口

```python
@require_http_methods(["GET"])
def public_download(request, document_id):
    """
    直接返回文件内容
    """
    try:
        document = CaseDocument.objects.get(id=document_id)
        file_path = document.file_path
        
        if not os.path.exists(file_path):
            return HttpResponse(
                json.dumps({"code": 40004, "message": "file not exists"}),
                content_type="application/json",
                status=404
            )
        
        file = open(file_path, 'rb')
        response = FileResponse(
            file,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        # ⚠️ 关键：必须设置这些响应头
        response['Content-Disposition'] = f'inline; filename="{document.name}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Security-Policy'] = "frame-ancestors 'self'"
        
        return response
    except Exception as e:
        return HttpResponse(status=500)
```

### 文件信息接口

```python
@require_http_methods(["GET"])
def wps_file_info(request, file_id):
    """
    获取文件信息
    WPS回调接口：GET /v3/3rd/files/{file_id}
    """
    if not verify_wps_signature(request, settings.WPS_APP_SECRET):
        return JsonResponse({'code': 40101, 'message': 'invalid signature'}, status=401)
    
    try:
        document = CaseDocument.objects.get(id=file_id)
        
        return JsonResponse({
            'code': 0,
            'data': {
                'id': str(document.id),
                'name': document.name,
                'version': document.version or 1,
                'size': document.size or 0,
                'create_time': int(document.created_at.timestamp()),
                'modify_time': int(document.updated_at.timestamp()),
                'creator': document.creator.username if document.creator else '',
                'modifier': document.modifier.username if document.modifier else ''
            }
        })
    except Exception as e:
        return JsonResponse({'code': 50000, 'message': str(e)}, status=500)
```

### 用户权限接口

```python
@require_http_methods(["GET"])
def wps_file_permission(request, file_id):
    """
    获取用户权限
    WPS回调接口：GET /v3/3rd/files/{file_id}/permission
    """
    if not verify_wps_signature(request, settings.WPS_APP_SECRET):
        return JsonResponse({'code': 40101, 'message': 'invalid signature'}, status=401)
    
    user_info = verify_wps_token(request)
    if not user_info:
        return JsonResponse({'code': 40102, 'message': 'invalid token'}, status=401)
    
    try:
        # 根据用户和文件判断权限
        # 这里简化处理，给予所有权限
        return JsonResponse({
            'code': 0,
            'data': {
                'user_id': str(user_info['user_id']),
                'read': 1,
                'update': 1,
                'download': 1,
                'rename': 1,
                'history': 1,
                'copy': 1,
                'print': 1,
                'saveas': 1,
                'comment': 1
            }
        })
    except Exception as e:
        return JsonResponse({'code': 50000, 'message': str(e)}, status=500)
```

### 保存文件接口

```python
@require_http_methods(["POST"])
def wps_file_save(request, file_id):
    """
    保存文件
    WPS回调接口：POST /v3/3rd/files/{file_id}/save
    """
    if not verify_wps_signature(request, settings.WPS_APP_SECRET):
        return JsonResponse({'code': 40101, 'message': 'invalid signature'}, status=401)
    
    user_info = verify_wps_token(request)
    if not user_info:
        return JsonResponse({'code': 40102, 'message': 'invalid token'}, status=401)
    
    try:
        document = CaseDocument.objects.get(id=file_id)
        
        # 保存上传的文件
        file_content = request.body
        with open(document.file_path, 'wb') as f:
            f.write(file_content)
        
        # 更新版本号
        document.version = (document.version or 1) + 1
        document.updated_at = datetime.now()
        document.save()
        
        return JsonResponse({
            'code': 0,
            'data': {
                'version': document.version,
                'modify_time': int(document.updated_at.timestamp())
            }
        })
    except Exception as e:
        return JsonResponse({'code': 50000, 'message': str(e)}, status=500)
```

### URL 路由配置

```python
# urls.py
urlpatterns = [
    # 前端配置接口
    path('api/case/documents/<int:document_id>/wps/init-config/', get_wps_init_config),
    
    # WPS回调接口
    path('v3/3rd/files/<str:file_id>/download', wps_file_download_url),
    path('v3/3rd/files/<str:file_id>', wps_file_info),
    path('v3/3rd/files/<str:file_id>/permission', wps_file_permission),
    path('v3/3rd/files/<str:file_id>/save', wps_file_save),
    path('v3/3rd/users', wps_user_info),
    
    # 文件下载接口
    path('api/case/documents/<int:document_id>/public_download/', public_download),
]
```

---

## 测试步骤

### 1. 测试前端配置接口

```bash
curl -X POST http://localhost:8000/api/case/documents/238/wps/init-config/ \
  -H "Content-Type: application/json" \
  -d '{"mode": "edit"}'
```

预期响应：
```json
{
  "code": 0,
  "data": {
    "appId": "your_app_id",
    "fileId": "238",
    "officeType": "w",
    "token": "eyJ..."
  }
}
```

### 2. 测试文件下载地址接口

```bash
curl http://localhost:8000/v3/3rd/files/238/download \
  -H "X-WebOffice-Token: <token>"
```

预期响应：
```json
{
  "code": 0,
  "data": {
    "url": "http://localhost:8000/api/case/documents/238/public_download/"
  }
}
```

### 3. 测试文件下载接口

在浏览器中访问：
```
http://localhost:8000/api/case/documents/238/public_download/
```

打开开发者工具的 Network 面板，检查响应头：
- `Content-Disposition: inline; filename="xxx.docx"`（必须是 inline）
- `X-Frame-Options: SAMEORIGIN`（或不设置）

### 4. 测试完整流程

1. 前端页面打开文档预览
2. 打开浏览器开发者工具的 Network 面板
3. 观察以下请求是否成功（状态码200）：
   - `POST /api/case/documents/238/wps/init-config/`
   - `GET /v3/3rd/files/238/download`
   - `GET /v3/3rd/files/238`
   - `GET /v3/3rd/files/238/permission`
   - `GET /api/case/documents/238/public_download/`

---

## 常见问题

### 1. init 超时

**现象：** 前端提示 "WPS初始化超时（30秒）"

**原因：**
- 后端回调接口未实现
- 回调接口返回格式错误
- 签名验证失败

**解决：**
1. 检查 Network 面板，查看回调请求是否返回200
2. 检查回调接口的响应格式是否符合规范
3. 检查签名验证逻辑

### 2. 文件被下载而不是预览

**原因：** `Content-Disposition` 未设置或设置为 `attachment`

**解决：** 确保 `public_download` 接口设置：
```python
response['Content-Disposition'] = 'inline; filename="xxx.docx"'
```

### 3. iframe 加载被阻止

**原因：** 设置了 `X-Frame-Options: deny`

**解决：** 设置为 `SAMEORIGIN` 或不设置：
```python
response['X-Frame-Options'] = 'SAMEORIGIN'
```

### 4. 签名验证失败

**原因：** 签名算法不正确

**解决：** 参考WPS官方文档的签名算法实现

---

## 参考文档

- [WPS官方文档 - 回调服务](https://solution.wps.cn/docs/callback/summary.html)
- [WPS官方文档 - 文档预览](https://solution.wps.cn/docs/callback/preview.html)
- [WPS官方文档 - 回调网关](https://solution.wps.cn/docs/callback/gateway.html)

---

## 总结

init 方式相比 config 方式的优势：

1. **更标准**：符合WPS官方推荐的集成方式
2. **更安全**：通过签名和token进行鉴权
3. **更灵活**：支持协同编辑、权限控制等高级功能
4. **更易维护**：WPS SDK自动管理文件加载和iframe

后端需要实现：
1. 前端配置接口（1个）
2. WPS回调接口（5个）
3. 文件下载接口（1个）
4. 签名验证逻辑
5. Token验证逻辑

**关键点：**
- `public_download` 接口必须设置 `Content-Disposition: inline`
- 不能设置 `X-Frame-Options: deny`
- 回调接口必须验证签名和token
- 响应格式必须符合WPS官方规范

