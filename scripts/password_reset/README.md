# 密码重置工具集

本目录包含用于检查和重置 superadmin 账号密码的工具脚本。

## 文件说明

### Python 脚本

1. **check_password_format.py** - 检查密码格式（不依赖Django）
   - 直接连接数据库检查密码格式
   - 不需要Django环境

2. **check_and_reset_password.py** - 检查并重置密码（需要Django环境）
   - 需要Django环境
   - 可以检查密码格式并重置密码

3. **fix_superadmin_simple.py** - 简单解锁脚本（不依赖Django）
   - 直接使用SQL解锁账号
   - 不重置密码，只解锁

4. **direct_fix_superadmin.py** - 直接修复脚本（部分依赖Django）
   - 尝试使用Django生成密码哈希
   - 如果Django不可用，只解锁账号

5. **fix_superadmin_cmd.py** - Django shell命令脚本
   - 需要在Django shell中执行
   - 使用方法：`python manage.py shell` 然后 `exec(open('scripts/password_reset/fix_superadmin_cmd.py').read())`

6. **fix_superadmin.py** - Django shell脚本
   - 纯Django shell脚本
   - 使用方法：`python manage.py shell` 然后 `exec(open('scripts/password_reset/fix_superadmin.py').read())`

7. **reset_superadmin.py** - 重置密码脚本
   - Django shell脚本
   - 使用方法：`python manage.py shell` 然后 `exec(open('scripts/password_reset/reset_superadmin.py').read())`

8. **generate_password_hash.py** - 密码哈希生成工具
   - 生成MD5哈希
   - 提示如何使用Django生成PBKDF2哈希

### SQL 脚本

- **unlock_and_reset_sql.sql** - SQL解锁脚本
  - 直接使用SQL解锁账号
  - 不重置密码

### 文档

- **修复superadmin账号说明.md** - 完整的使用说明文档

## 使用方法

### 方法1: 使用Django管理命令（推荐）

```bash
# 在项目根目录执行
cd lsl/lsl-backend
conda activate lsl  # 或激活其他Python环境
python manage.py fix_superadmin
```

### 方法2: 使用Django Shell

```bash
# 在项目根目录执行
cd lsl/lsl-backend
conda activate lsl
python manage.py shell
```

然后在shell中执行：

```python
exec(open('scripts/password_reset/fix_superadmin.py').read())
```

### 方法3: 直接运行Python脚本（需要Django环境）

```bash
# 在项目根目录执行
cd lsl/lsl-backend
conda activate lsl
python scripts/password_reset/check_and_reset_password.py
```

### 方法4: 使用SQL脚本（只解锁，不重置密码）

```bash
# 在项目根目录执行
cd lsl/lsl-backend
# 使用MySQL客户端执行
mysql -h 171.80.10.200 -P 33060 -u root -p < scripts/password_reset/unlock_and_reset_sql.sql
```

## 注意事项

1. **路径问题**: 所有脚本中的路径引用已更新为相对于项目根目录
2. **Django环境**: 需要Django环境的脚本必须在项目根目录执行，或在脚本所在目录执行时确保路径正确
3. **数据库配置**: 脚本中的数据库配置来自 `conf/env.py`，确保该文件存在且配置正确
4. **密码格式**: 根据 `dvadmin/system/models.py` 的逻辑，密码会先MD5再PBKDF2

## 默认账号密码

重置后的默认账号密码：
- **账号**: `superadmin`
- **密码**: `admin123456`

## 相关文件位置

- Django管理命令: `dvadmin/system/management/commands/fix_superadmin.py`
- 用户模型: `dvadmin/system/models.py`
- 登录视图: `dvadmin/system/views/login.py`

