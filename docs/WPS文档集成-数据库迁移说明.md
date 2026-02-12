# WPS文档集成 - 数据库迁移说明

## 问题描述

错误信息：`Unknown column 'case_document.wps_file_id' in 'field list'`

**原因：** 迁移文件已创建但尚未执行，数据库中缺少新增的WPS相关字段。

## 解决方案

### 方法一：执行迁移（推荐）

**步骤：**

1. **激活虚拟环境**（如果使用虚拟环境）
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **检查迁移文件**
   ```bash
   python manage.py showmigrations case_management
   ```
   应该能看到 `0016_add_wps_fields` 显示为 `[ ]`（未执行）

3. **执行迁移**
   ```bash
   python manage.py migrate case_management
   ```
   或者执行所有迁移：
   ```bash
   python manage.py migrate
   ```

4. **验证迁移**
   ```bash
   python manage.py showmigrations case_management
   ```
   应该能看到 `0016_add_wps_fields` 显示为 `[X]`（已执行）

### 方法二：手动执行SQL（如果迁移失败）

如果迁移执行失败，可以手动执行SQL：

```sql
-- 添加WPS相关字段到case_document表
ALTER TABLE case_document 
ADD COLUMN IF NOT EXISTS wps_file_id VARCHAR(100) NULL COMMENT 'WPS文件ID',
ADD COLUMN IF NOT EXISTS wps_edit_token VARCHAR(500) NULL COMMENT 'WPS编辑令牌',
ADD COLUMN IF NOT EXISTS wps_edit_url VARCHAR(500) NULL COMMENT 'WPS编辑URL',
ADD COLUMN IF NOT EXISTS last_edit_time DATETIME NULL COMMENT '最后编辑时间',
ADD COLUMN IF NOT EXISTS last_editor_id BIGINT NULL COMMENT '最后编辑人ID',
ADD COLUMN IF NOT EXISTS wps_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用WPS编辑';

-- 创建WPS编辑记录表
CREATE TABLE IF NOT EXISTS wps_edit_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id BIGINT NOT NULL COMMENT '文档ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    user_name VARCHAR(100) NULL COMMENT '用户名',
    file_id VARCHAR(100) NULL COMMENT 'WPS文件ID',
    edit_token VARCHAR(500) NULL COMMENT '编辑令牌',
    edit_mode VARCHAR(20) DEFAULT 'edit' COMMENT '编辑模式：view/edit',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始编辑时间',
    end_time DATETIME NULL COMMENT '结束编辑时间',
    save_count INT DEFAULT 0 COMMENT '保存次数',
    status VARCHAR(20) DEFAULT 'editing' COMMENT '状态：editing/completed/cancelled',
    ip_address VARCHAR(50) NULL COMMENT 'IP地址',
    user_agent VARCHAR(500) NULL COMMENT '用户代理',
    description VARCHAR(255) NULL,
    modifier VARCHAR(255) NULL,
    dept_belong_id VARCHAR(255) NULL,
    update_datetime DATETIME NULL,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    creator_id BIGINT NULL,
    FOREIGN KEY (document_id) REFERENCES case_document(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WPS编辑记录表';

-- 创建WPS回调日志表
CREATE TABLE IF NOT EXISTS wps_callback_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id BIGINT NULL COMMENT '文档ID',
    file_id VARCHAR(100) NULL COMMENT 'WPS文件ID',
    event_type VARCHAR(50) NOT NULL COMMENT '事件类型',
    event_data JSON NULL COMMENT '事件数据',
    callback_data TEXT NULL COMMENT '回调原始数据',
    status VARCHAR(20) DEFAULT 'success' COMMENT '处理状态：success/failed',
    error_message TEXT NULL COMMENT '错误信息',
    description VARCHAR(255) NULL,
    modifier VARCHAR(255) NULL,
    dept_belong_id VARCHAR(255) NULL,
    update_datetime DATETIME NULL,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    creator_id BIGINT NULL,
    FOREIGN KEY (document_id) REFERENCES case_document(id) ON DELETE SET NULL,
    INDEX idx_document_id (document_id),
    INDEX idx_event_type (event_type),
    INDEX idx_create_datetime (create_datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WPS回调日志表';
```

**注意：** 如果使用表前缀（如 `lsl_`），需要在表名前加上前缀。

### 方法三：标记迁移为已执行（如果已经手动创建了表）

如果已经手动创建了表，可以标记迁移为已执行：

```bash
python manage.py migrate case_management 0016_add_wps_fields --fake
```

## 验证

执行迁移后，可以通过以下方式验证：

### 1. 检查数据库表结构

```sql
-- 检查case_document表是否有新字段
DESCRIBE case_document;

-- 应该能看到以下字段：
-- wps_file_id
-- wps_edit_token
-- wps_edit_url
-- last_edit_time
-- last_editor_id
-- wps_enabled

-- 检查新表是否存在
SHOW TABLES LIKE 'wps_%';
-- 应该能看到：
-- wps_edit_record
-- wps_callback_log
```

### 2. 测试API

```bash
# 测试获取WPS配置接口
curl -X POST http://localhost:8000/api/case/document/wps/edit-config/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"documentId": 1, "mode": "edit"}'
```

如果不再报错，说明迁移成功。

## 常见问题

### Q1: 迁移时提示表已存在

**A:** 如果表已存在，可能是之前手动创建过。可以：
- 使用 `--fake` 标记迁移为已执行
- 或者删除表后重新执行迁移

### Q2: 迁移时提示字段已存在

**A:** 可以使用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 语法，或者：
- 先删除字段：`ALTER TABLE case_document DROP COLUMN wps_file_id;`
- 然后重新执行迁移

### Q3: 迁移后还是报错

**A:** 检查：
1. 是否重启了Django服务
2. 是否正确执行了迁移
3. 数据库连接是否正常
4. 查看Django日志确认具体错误

## 回滚迁移（如果需要）

如果需要回滚迁移：

```bash
python manage.py migrate case_management 0015_add_case_document_sort_order
```

这会回滚到迁移 `0015_add_case_document_sort_order`，撤销 `0016_add_wps_fields` 的所有更改。

**注意：** 回滚会删除新创建的表和字段，请谨慎操作！

