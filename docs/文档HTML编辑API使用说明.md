# 文档HTML编辑功能 - API使用说明

## 一、功能概述

实现了DOCX与HTML格式互转功能，支持前端富文本编辑器的使用。

## 二、API接口

### 2.1 DOCX转HTML接口

**接口路径：** `POST /api/case/document/convert/docx-to-html/`

**功能：** 将DOCX文档转换为HTML格式，供前端富文本编辑器使用

**请求参数：**
```json
{
  "documentId": 123  // 文档ID（必需）
}
```

**响应数据：**
```json
{
  "code": 2000,
  "msg": "转换成功",
  "data": {
    "documentId": 123,
    "html": "<html>...</html>",
    "title": "文档标题",
    "images": [
      {
        "id": "rId1",
        "url": "/media/images/documents/2025/11/xxx.jpg",
        "path": "images/documents/2025/11/xxx.jpg",
        "size": 12345,
        "content_type": "image/jpeg"
      }
    ]
  }
}
```

### 2.2 HTML转DOCX接口

**接口路径：** `POST /api/case/document/convert/html-to-docx/`

**功能：** 将前端编辑器生成的HTML内容转换为DOCX文档并保存

**请求参数：**
```json
{
  "documentId": 123,  // 文档ID（必需）
  "html": "<html>...</html>",  // HTML内容（必需）
  "title": "文档标题",  // 可选
  "savePath": "custom_filename.docx"  // 可选
}
```

**响应数据：**
```json
{
  "code": 2000,
  "msg": "转换并保存成功",
  "data": {
    "documentId": 123,
    "documentPath": "documents/original/2025/11/123_20251102103000.docx",
    "fileSize": 12345,
    "updateTime": "2025-11-02T10:30:00"
  }
}
```

### 2.3 图片上传接口

**接口路径：** `POST /api/case/document/upload-image/`

**功能：** 处理编辑器中上传的图片，保存到服务器并返回访问URL

**请求参数：**
```
Content-Type: multipart/form-data

file: [图片文件]  // 必需
documentId: 123   // 可选，用于关联
```

**响应数据：**
```json
{
  "code": 2000,
  "msg": "图片上传成功",
  "data": {
    "url": "/media/images/documents/2025/11/xxx.jpg",
    "alt": "xxx.jpg",
    "href": "/media/images/documents/2025/11/xxx.jpg"
  }
}
```

## 三、使用示例

### 3.1 Python requests 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 登录获取token
login_response = requests.post(
    f"{BASE_URL}/api/login/",
    json={"username": "your_username", "password": "your_password"}
)
token = login_response.json()['data']['token']

headers = {"Authorization": f"Bearer {token}"}

# 2. DOCX转HTML
response = requests.post(
    f"{BASE_URL}/api/case/document/convert/docx-to-html/",
    headers=headers,
    json={"documentId": 123}
)
html_data = response.json()['data']
print(f"HTML内容: {html_data['html']}")

# 3. HTML转DOCX
response = requests.post(
    f"{BASE_URL}/api/case/document/convert/html-to-docx/",
    headers=headers,
    json={
        "documentId": 123,
        "html": "<h1>标题</h1><p>这是内容</p>"
    }
)
print(response.json())

# 4. 上传图片
files = {'file': open('image.jpg', 'rb')}
data = {'documentId': 123}
response = requests.post(
    f"{BASE_URL}/api/case/document/upload-image/",
    headers=headers,
    files=files,
    data=data
)
image_url = response.json()['data']['url']
print(f"图片URL: {image_url}")
```

### 3.2 JavaScript/Fetch 示例

```javascript
const BASE_URL = 'http://localhost:8000';
const token = 'your_token';

// DOCX转HTML
async function convertDocxToHtml(documentId) {
  const response = await fetch(`${BASE_URL}/api/case/document/convert/docx-to-html/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ documentId })
  });
  const data = await response.json();
  return data.data;
}

// HTML转DOCX
async function convertHtmlToDocx(documentId, html) {
  const response = await fetch(`${BASE_URL}/api/case/document/convert/html-to-docx/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ documentId, html })
  });
  return await response.json();
}

// 上传图片
async function uploadImage(file, documentId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('documentId', documentId);
  
  const response = await fetch(`${BASE_URL}/api/case/document/upload-image/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  return await response.json();
}
```

## 四、格式支持

### 4.1 DOCX → HTML 支持的格式

- ✅ 文本格式：加粗、斜体、下划线、删除线、颜色、字体大小
- ✅ 段落格式：对齐方式、行距、段落间距
- ✅ 列表：有序列表、无序列表、多级列表
- ✅ 表格：表格结构、单元格合并、边框样式
- ✅ 图片：图片内容、图片大小
- ✅ 标题：H1-H6

### 4.2 HTML → DOCX 支持的格式

- ✅ HTML标签：`<p>`, `<h1>-<h6>`, `<b>`, `<strong>`, `<i>`, `<em>`, `<u>`, `<ul>`, `<ol>`, `<li>`, `<table>`, `<tr>`, `<td>`, `<img>`, `<a>`
- ✅ CSS样式：字体、颜色、对齐、行距等
- ✅ 图片：Base64、网络图片、本地图片

## 五、安全特性

- ✅ HTML内容清理：使用bleach库清理不安全的HTML标签和脚本
- ✅ 图片校验：文件类型、文件大小限制
- ✅ 权限检查：所有接口需要用户认证
- ✅ XSS防护：自动移除危险的脚本和事件处理器

## 六、依赖安装

```bash
pip install -r requirements.txt
```

主要依赖：
- `mammoth==1.6.0` - DOCX转HTML
- `python-docx==1.1.2` - DOCX操作
- `beautifulsoup4==4.12.3` - HTML解析
- `bleach==6.1.0` - HTML清理
- `Pillow==10.4.0` - 图片处理

## 七、注意事项

1. **图片处理**：
   - 上传的图片会自动压缩（最大1920px）
   - 图片按年月组织目录存储
   - 支持Base64、网络图片、本地图片

2. **文件存储**：
   - DOCX文件按年月组织目录：`media/documents/original/YYYY/MM/`
   - 图片文件按年月组织目录：`media/images/documents/YYYY/MM/`
   - 临时文件存储在：`media/temp/`

3. **性能优化**：
   - 大文件建议使用异步处理
   - 临时文件会自动清理（1小时后）
   - 建议使用缓存提高转换速度

4. **错误处理**：
   - 文件不存在：返回404
   - 格式错误：返回400
   - 转换失败：返回500，查看日志了解详情

## 八、完整工作流程示例

```javascript
// 1. 加载文档并转换为HTML供编辑器使用
const htmlData = await convertDocxToHtml(documentId);
editor.setContent(htmlData.html);

// 2. 用户在编辑器中编辑内容
// ... 用户编辑 ...

// 3. 保存时转换HTML回DOCX
const htmlContent = editor.getContent();
const result = await convertHtmlToDocx(documentId, htmlContent);

// 4. 上传图片（编辑器中）
async function handleImageUpload(file) {
  const result = await uploadImage(file, documentId);
  return result.data.url;
}
```

