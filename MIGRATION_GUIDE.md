# 数据库迁移执行指南

## 迁移文件说明

本次迁移包含两个迁移文件：

1. **case_management/migrations/0021_add_case_relations.py**
   - 在 `case_management` 表中添加：
     - `customer_id` (关联客户)
     - `owner_user_id` (经办人/销售)
     - `owner_user_name` (经办人姓名)
     - `contract_id` (关联合同)
   - 添加相应的索引

2. **customer_management/migrations/0012_add_contract_case_relation.py**
   - 在 `customer_contract` 表中添加：
     - `case_id` (关联案件)
   - 添加相应的索引

## 执行步骤

### 1. 激活虚拟环境（如果使用）

```bash
# Windows (conda)
conda activate .\.conda

# 或使用系统Python
python --version
```

### 2. 检查迁移状态

```bash
cd lsl/lsl-backend
python manage.py showmigrations case_management
python manage.py showmigrations customer_management
```

### 3. 检查迁移文件是否有冲突

```bash
python manage.py makemigrations --dry-run
```

如果输出为空，说明没有新的迁移需要创建，可以继续执行。

### 4. 执行迁移

**方式一：执行所有迁移（推荐）**
```bash
python manage.py migrate
```

**方式二：分别执行两个迁移**
```bash
python manage.py migrate case_management
python manage.py migrate customer_management
```

### 5. 验证迁移结果

```bash
# 检查迁移状态
python manage.py showmigrations case_management
python manage.py showmigrations customer_management

# 应该看到 0021_add_case_relations 和 0012_add_contract_case_relation 显示为 [X]
```

### 6. 验证数据库表结构

```sql
-- 检查 case_management 表
DESC case_management;
SHOW INDEX FROM case_management;

-- 检查 customer_contract 表
DESC customer_contract;
SHOW INDEX FROM customer_contract;
```

## 常见错误及解决方案

### 错误1: "No such table: case_management"

**原因**: 数据库表不存在

**解决**: 先执行基础迁移
```bash
python manage.py migrate case_management 0001_initial
python manage.py migrate
```

### 错误2: "django.db.utils.OperationalError: (1050, "Table 'xxx' already exists")"

**原因**: 表已存在，但迁移记录不一致

**解决**: 
```bash
# 标记迁移为已执行（如果表结构已正确）
python manage.py migrate case_management 0021_add_case_relations --fake

# 或重置迁移（谨慎使用，会丢失数据）
python manage.py migrate case_management zero
python manage.py migrate case_management
```

### 错误3: "django.db.utils.IntegrityError: (1215, 'Cannot add foreign key constraint')"

**原因**: 外键约束失败（但我们已经设置了 `db_constraint=False`，不应该出现此错误）

**解决**: 检查迁移文件中的 `db_constraint=False` 是否正确设置

### 错误4: "django.db.utils.OperationalError: (1060, "Duplicate column name")"

**原因**: 字段已存在

**解决**: 
```bash
# 检查数据库表结构
DESC case_management;

# 如果字段已存在，标记迁移为已执行
python manage.py migrate case_management 0021_add_case_relations --fake
```

### 错误5: 循环依赖错误

**原因**: 迁移文件的依赖关系有问题

**解决**: 检查迁移文件的 dependencies：
- `0021_add_case_relations` 依赖于 `0020_merge_20251108_0151` 和 `0011_merge_0007_feedback_0010_customer_grade_collection_source`
- `0012_add_contract_case_relation` 依赖于 `0021_add_case_relations`

## 回滚迁移（如果需要）

```bash
# 回滚到指定迁移
python manage.py migrate case_management 0020_merge_20251108_0151
python manage.py migrate customer_management 0011_merge_0007_feedback_0010_customer_grade_collection_source
```

## 注意事项

1. **备份数据库**: 执行迁移前建议备份数据库
2. **测试环境**: 先在测试环境执行，确认无误后再在生产环境执行
3. **字段为NULL**: 所有新增字段都设置为 `NULL=True`，不会影响现有数据
4. **索引**: 已添加索引以提高查询性能
5. **外键约束**: 使用 `db_constraint=False`，避免数据库级外键约束

## 验证数据

迁移执行后，可以验证数据：

```python
# 在Django shell中执行
python manage.py shell

from case_management.models import CaseManagement
from customer_management.models import Contract

# 检查字段是否存在
case = CaseManagement.objects.first()
print(hasattr(case, 'customer_id'))
print(hasattr(case, 'owner_user_id'))
print(hasattr(case, 'contract_id'))

contract = Contract.objects.first()
print(hasattr(contract, 'case_id'))
```
