# 批量更新打印数量API对接文档

## API 概述

**接口名称**：批量更新文档打印数量  
**接口路径**：`/api/case/documents/batch-update-print-count/`  
**请求方法**：`POST`  
**Content-Type**：`application/json`  

## 请求参数

### 请求头 (Headers)

```http
Content-Type: application/json
Authorization: Bearer {token}  # 如果需要认证
```

### 请求体 (Body)

```json
{
  "documents": [
    {
      "id": 1,
      "print_count": 3
    },
    {
      "id": 5,
      "print_count": 2
    },
    {
      "id": 8,
      "print_count": 1
    }
  ]
}
```

### 参数说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| documents | Array | 是 | 需要更新的文档列表 |
| documents[].id | Integer | 是 | 文档ID（CaseDocument的主键） |
| documents[].print_count | Integer | 是 | 打印数量，范围：1-99 |

### 参数验证规则

- `documents` 数组不能为空
- `id` 必须是有效的文档ID
- `print_count` 必须是1到99之间的整数

## 响应格式

### 成功响应

**HTTP 状态码**：200

```json
{
  "code": 2000,
  "msg": "成功更新 3 个文档的打印数量",
  "data": {
    "updated_count": 3,
    "updated_documents": [
      {
        "id": 1,
        "document_name": "起诉状.docx",
        "print_count": 3
      },
      {
        "id": 5,
        "document_name": "答辩状.docx",
        "print_count": 2
      },
      {
        "id": 8,
        "document_name": "证据清单.pdf",
        "print_count": 1
      }
    ]
  }
}
```

### 错误响应

#### 1. 参数缺失或格式错误

**HTTP 状态码**：400

```json
{
  "code": 4000,
  "msg": "没有提供文档数据",
  "data": null
}
```

#### 2. 文档不存在

**HTTP 状态码**：404

```json
{
  "code": 4004,
  "msg": "部分文档不存在",
  "data": {
    "not_found_ids": [1, 5]
  }
}
```

#### 3. 打印数量超出范围

**HTTP 状态码**：400

```json
{
  "code": 4000,
  "msg": "打印数量必须在1到99之间",
  "data": {
    "invalid_values": [
      {"id": 1, "print_count": 100}
    ]
  }
}
```

#### 4. 服务器错误

**HTTP 状态码**：500

```json
{
  "code": 5000,
  "msg": "更新打印数量失败: 数据库错误",
  "data": null
}
```

## 后端实现示例

### Django REST Framework 实现

#### 1. 视图函数（ViewSet方式）

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import CaseDocument
from .serializers import CaseDocumentSerializer

class CaseDocumentViewSet(viewsets.ModelViewSet):
    queryset = CaseDocument.objects.all()
    serializer_class = CaseDocumentSerializer
    
    @action(detail=False, methods=['post'], url_path='batch-update-print-count')
    def batch_update_print_count(self, request):
        """
        批量更新文档打印数量
        
        请求参数：
        {
            "documents": [
                {"id": 1, "print_count": 3},
                {"id": 2, "print_count": 2}
            ]
        }
        """
        try:
            # 1. 获取请求数据
            documents_data = request.data.get('documents', [])
            
            # 2. 参数验证
            if not documents_data:
                return Response({
                    'code': 4000,
                    'msg': '没有提供文档数据',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(documents_data, list):
                return Response({
                    'code': 4000,
                    'msg': 'documents必须是数组',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 3. 验证打印数量范围
            invalid_values = []
            for item in documents_data:
                print_count = item.get('print_count', 0)
                if not (1 <= print_count <= 99):
                    invalid_values.append({
                        'id': item.get('id'),
                        'print_count': print_count
                    })
            
            if invalid_values:
                return Response({
                    'code': 4000,
                    'msg': '打印数量必须在1到99之间',
                    'data': {'invalid_values': invalid_values}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. 使用事务批量更新
            with transaction.atomic():
                # 提取所有文档ID
                document_ids = [item['id'] for item in documents_data]
                
                # 查询所有文档
                documents = CaseDocument.objects.filter(
                    id__in=document_ids,
                    is_deleted=False  # 只更新未删除的文档
                )
                
                # 检查是否所有文档都存在
                found_ids = set(documents.values_list('id', flat=True))
                requested_ids = set(document_ids)
                not_found_ids = requested_ids - found_ids
                
                if not_found_ids:
                    return Response({
                        'code': 4004,
                        'msg': '部分文档不存在',
                        'data': {'not_found_ids': list(not_found_ids)}
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # 创建ID到print_count的映射
                print_count_map = {
                    item['id']: item['print_count'] 
                    for item in documents_data
                }
                
                # 更新每个文档的print_count
                for document in documents:
                    document.print_count = print_count_map.get(document.id, 1)
                
                # 批量保存（性能优化）
                CaseDocument.objects.bulk_update(documents, ['print_count'])
                
                # 准备返回数据
                updated_documents = [
                    {
                        'id': doc.id,
                        'document_name': doc.document_name,
                        'print_count': doc.print_count
                    }
                    for doc in documents
                ]
            
            return Response({
                'code': 2000,
                'msg': f'成功更新 {len(documents)} 个文档的打印数量',
                'data': {
                    'updated_count': len(documents),
                    'updated_documents': updated_documents
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # 记录错误日志
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'批量更新打印数量失败: {str(e)}', exc_info=True)
            
            return Response({
                'code': 5000,
                'msg': f'更新打印数量失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

#### 2. URL 配置

```python
# urls.py
from rest_framework.routers import DefaultRouter
from .views import CaseDocumentViewSet

router = DefaultRouter()
router.register(r'case/documents', CaseDocumentViewSet, basename='casedocument')

urlpatterns = [
    # 其他URL配置
]

urlpatterns += router.urls
```

这样会自动生成以下URL：
- `POST /api/case/documents/batch-update-print-count/`

### 使用 APIView 方式实现

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

class BatchUpdatePrintCountView(APIView):
    """批量更新文档打印数量"""
    
    def post(self, request):
        try:
            documents_data = request.data.get('documents', [])
            
            if not documents_data:
                return Response({
                    'code': 4000,
                    'msg': '没有提供文档数据'
                })
            
            with transaction.atomic():
                document_ids = [item['id'] for item in documents_data]
                documents = CaseDocument.objects.filter(id__in=document_ids)
                
                print_count_map = {
                    item['id']: item['print_count'] 
                    for item in documents_data
                }
                
                for document in documents:
                    document.print_count = print_count_map.get(document.id, 1)
                
                CaseDocument.objects.bulk_update(documents, ['print_count'])
            
            return Response({
                'code': 2000,
                'msg': f'成功更新 {len(documents)} 个文档的打印数量',
                'data': {'updated_count': len(documents)}
            })
            
        except Exception as e:
            return Response({
                'code': 5000,
                'msg': f'更新失败: {str(e)}'
            })

# urls.py
urlpatterns = [
    path('api/case/documents/batch-update-print-count/', 
         BatchUpdatePrintCountView.as_view(), 
         name='batch-update-print-count'),
]
```

## 数据库模型

确保 `CaseDocument` 模型包含 `print_count` 字段：

```python
from django.db import models

class CaseDocument(models.Model):
    """案件文档模型"""
    
    # ... 其他字段
    
    document_name = models.CharField(max_length=255, verbose_name='文档名称')
    print_count = models.IntegerField(
        default=1, 
        verbose_name='打印数量',
        help_text='每次打印的份数，范围1-99'
    )
    
    # ... 其他字段
    
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
    
    class Meta:
        db_table = 'case_document'
        verbose_name = '案件文档'
        verbose_name_plural = verbose_name
        ordering = ['-id']
```

### 数据库迁移

如果是新增字段，需要创建迁移：

```bash
# 创建迁移文件
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

## 测试示例

### 使用 curl 测试

```bash
curl -X POST http://localhost:8000/api/case/documents/batch-update-print-count/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token_here" \
  -d '{
    "documents": [
      {"id": 1, "print_count": 3},
      {"id": 2, "print_count": 2},
      {"id": 3, "print_count": 1}
    ]
  }'
```

### 使用 Python requests 测试

```python
import requests

url = "http://localhost:8000/api/case/documents/batch-update-print-count/"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your_token_here"
}
data = {
    "documents": [
        {"id": 1, "print_count": 3},
        {"id": 2, "print_count": 2},
        {"id": 3, "print_count": 1}
    ]
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

### 使用 Postman 测试

1. **Method**: POST
2. **URL**: `http://localhost:8000/api/case/documents/batch-update-print-count/`
3. **Headers**:
   - `Content-Type`: `application/json`
   - `Authorization`: `Bearer {token}`
4. **Body** (raw JSON):
```json
{
  "documents": [
    {"id": 1, "print_count": 3},
    {"id": 2, "print_count": 2}
  ]
}
```

## 性能优化建议

1. **使用 bulk_update**：批量更新比循环调用 save() 性能高很多
2. **使用事务**：确保数据一致性
3. **添加索引**：给 `id` 字段添加索引（通常主键自动有）
4. **分批处理**：如果文档数量很大（>1000），可以分批处理

```python
# 分批处理示例
from django.db import transaction

BATCH_SIZE = 500

for i in range(0, len(documents_data), BATCH_SIZE):
    batch = documents_data[i:i + BATCH_SIZE]
    with transaction.atomic():
        # 处理批次
        pass
```

## 错误处理

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| 400 参数错误 | documents为空或格式错误 | 检查请求数据格式 |
| 404 文档不存在 | 文档ID不存在或已删除 | 检查文档ID是否正确 |
| 500 服务器错误 | 数据库错误或代码异常 | 查看服务器日志 |

## 安全建议

1. **权限验证**：确保用户有权限更新这些文档
2. **数据验证**：验证 print_count 范围
3. **SQL注入防护**：使用 ORM 查询（已内置防护）
4. **日志记录**：记录所有更新操作

```python
# 添加权限检查
from rest_framework.permissions import IsAuthenticated

class CaseDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def batch_update_print_count(self, request):
        # 检查用户是否有权限更新这些文档
        document_ids = [item['id'] for item in request.data.get('documents', [])]
        documents = CaseDocument.objects.filter(id__in=document_ids)
        
        # 验证用户是否是文档所属案件的成员
        for doc in documents:
            if not self.has_permission_for_case(request.user, doc.case_id):
                return Response({
                    'code': 4003,
                    'msg': '无权限操作此文档'
                })
        
        # ... 继续处理
```

## 前端调用示例

前端已实现的调用代码：

```typescript
const response = await request({
  url: '/api/case/documents/batch-update-print-count/',
  method: 'post',
  data: {
    documents: printCountUpdates
  }
})

if (response.code !== 2000) {
  ElMessage.error(response.msg || '更新打印数量失败')
  return
}

ElMessage.success('打印数量已更新到服务器')
```

