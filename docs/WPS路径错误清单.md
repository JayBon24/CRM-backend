# WPS 文档路径错误清单

## 错误总结

根据后端代码检查，文档中的路径存在以下错误：

### 错误 1：路径中使用单数 `document` 而不是复数 `documents`

**后端实际路由配置：**
- `router.register(r'documents', CaseDocumentViewSet)` - 注意是复数 `documents`
- 主路由：`path("api/case/", include("case_management.urls"))`

**文档中的错误路径：**
- ❌ `/api/case/document/wps/edit-config/`
- ❌ `/api/case/document/wps/save/<document_id>/`
- ❌ `/api/case/document/wps/download/<document_id>/`

**正确的路径应该是：**
- ✅ `/api/case/documents/{id}/wps/edit-config/` （如果是 detail action）
- ✅ `/api/case/documents/wps/edit-config/` （如果是 list action）
- ✅ `/api/case/documents/{id}/wps/save/` （detail action）
- ✅ `/api/case/documents/{id}/wps/download/` （detail action）

### 错误 2：路径格式不一致

**文档中的路径：**
- ❌ `/api/case/document/wps/edit-config/` （混合格式）
- ❌ `/api/case/document/wps/save/<document_id>/` （使用 `<document_id>` 占位符）

**正确的格式：**
- ✅ 如果是 detail action：`/api/case/documents/{id}/wps/edit-config/`
- ✅ 如果是 list action：`/api/case/documents/wps/edit-config/`

## 需要前端修改的路径

### 1. 获取 WPS 配置接口

**错误路径：**
```typescript
POST /api/case/document/wps/edit-config/
```

**正确路径（需要确认是 detail 还是 list action）：**
```typescript
// 如果是 detail action（需要 document_id）
POST /api/case/documents/{document_id}/wps/edit-config/

// 如果是 list action（不需要 document_id）
POST /api/case/documents/wps/edit-config/
```

**代码修改：**
```typescript
// 修改前
const response = await request.post('/api/case/document/wps/edit-config/', {
  documentId,
  mode,
});

// 修改后（detail action）
const response = await request.post(`/api/case/documents/${documentId}/wps/edit-config/`, {
  mode,
});

// 或（list action）
const response = await request.post('/api/case/documents/wps/edit-config/', {
  documentId,
  mode,
});
```

### 2. 文档保存接口

**错误路径：**
```typescript
POST /api/case/document/wps/save/${documentId}/
```

**正确路径：**
```typescript
POST /api/case/documents/${documentId}/wps/save/
```

**代码修改：**
```typescript
// 修改前
const response = await request.post(
  `/api/case/document/wps/save/${documentId}/`,
  formData,
);

// 修改后
const response = await request.post(
  `/api/case/documents/${documentId}/wps/save/`,
  formData,
);
```

### 3. 文档下载接口

**错误路径：**
```typescript
GET /api/case/document/wps/download/${documentId}/
```

**正确路径：**
```typescript
GET /api/case/documents/${documentId}/wps/download/
```

**代码修改：**
```typescript
// 修改前
const response = await request.get(
  `/api/case/document/wps/download/${documentId}/`,
);

// 修改后
const response = await request.get(
  `/api/case/documents/${documentId}/wps/download/`,
);
```

## 其他需要注意的路径

### 文档转换接口（这些是正确的）

这些路径是正确的，因为它们是独立的路由，不是 ViewSet：

- ✅ `/api/case/document/convert/docx-to-html/`
- ✅ `/api/case/document/convert/html-to-docx/`
- ✅ `/api/case/document/upload-image/`

### 文档列表和详情（这些是正确的）

- ✅ `/api/case/documents/` （列表）
- ✅ `/api/case/documents/{id}/` （详情）

## 重要提示

1. **所有 WPS 相关的路径都需要使用复数 `documents` 而不是单数 `document`**
2. **路径格式应该遵循 Django REST Framework 的约定：**
   - List action: `/api/case/documents/action_name/`
   - Detail action: `/api/case/documents/{id}/action_name/`
3. **需要确认后端是否已实现这些 WPS 相关的 action：**
   - 如果后端没有实现，需要先实现这些 action
   - 如果后端已实现，需要确认是 detail action 还是 list action

## 建议的修改步骤

1. **确认后端实现：** 检查 `CaseDocumentViewSet` 中是否有 `wps/edit-config`、`wps/save`、`wps/download` 这些 action
2. **确认 action 类型：** 确认是 detail action（需要 `{id}`）还是 list action（不需要 `{id}`）
3. **修改前端代码：** 根据后端实现修改所有相关路径
4. **更新文档：** 修正文档中的路径错误

