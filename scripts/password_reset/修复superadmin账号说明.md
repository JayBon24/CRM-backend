# 修复superadmin账号说明

## 问题分析结果

### 1. 账号状态检查
- ✅ **账号状态**: 已激活 (is_active = 1)
- ✅ **登录错误次数**: 已重置为0
- ✅ **密码格式**: PBKDF2 (Django标准格式)

### 2. 问题根源
根据代码分析，问题出在密码验证逻辑：

1. **密码存储方式** (`dvadmin/system/models.py` 第79-81行):
   ```python
   def set_password(self, raw_password):
       if raw_password:
           super().set_password(hashlib.md5(raw_password.encode(encoding="UTF-8")).hexdigest())
   ```
   - 密码会先进行MD5哈希，然后再传给Django的`set_password`进行PBKDF2哈希
   - 这导致密码存储格式为：`MD5(原始密码) -> PBKDF2(MD5值)`

2. **密码验证方式** (`dvadmin/system/views/login.py` 第100-104行):
   - Django的`check_password`会使用PBKDF2验证
   - 但验证时输入的是原始密码，而存储的是MD5后的PBKDF2值
   - 这导致密码验证失败

3. **账号锁定机制** (`dvadmin/system/views/login.py` 第127-134行):
   - 登录失败5次后，账号会被锁定 (`is_active = False`)
   - 账号被锁定后无法登录

## 解决方案

### 方案1: 使用Django Shell重置密码（推荐）

**前提条件**: 需要有Django环境（可以运行`python manage.py shell`）

**操作步骤**:

1. 进入项目目录:
   ```bash
   cd lsl/lsl-backend
   ```
   
   **注意**: 如果使用本目录中的脚本，需要在项目根目录执行，脚本会自动处理路径。

2. 激活Python环境（如果有虚拟环境）:
   ```bash
   # 如果有conda环境
   conda activate lsl
   # 或者
   # 如果有venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 进入Django shell:
   ```bash
   python manage.py shell
   ```

4. 执行以下代码:
   ```python
   from dvadmin.system.models import Users
   import hashlib
   from django.contrib.auth.hashers import make_password

   # 获取用户
   user = Users.objects.get(username='superadmin')
   
   # 解锁账号（确保已解锁）
   user.is_active = True
   user.login_error_count = 0
   
   # 重置密码
   # 注意：根据models.py的逻辑，密码会先MD5再PBKDF2
   raw_password = 'admin123456'
   md5_hash = hashlib.md5(raw_password.encode('utf-8')).hexdigest()
   user.password = make_password(md5_hash)
   
   # 保存
   user.save()
   
   print('密码已重置为: admin123456')
   print('账号已解锁')
   ```

   或者使用本目录中的脚本:
   ```python
   exec(open('scripts/password_reset/fix_superadmin.py').read())
   ```

5. 退出shell:
   ```python
   exit()
   ```

### 方案2: 使用管理命令（如果已创建）

如果已经创建了管理命令 `fix_superadmin.py`，可以直接执行:

```bash
# 在项目根目录执行
cd lsl/lsl-backend
python manage.py fix_superadmin
```

### 方案3: 直接运行Python脚本（需要Django环境）

```bash
# 在项目根目录执行
cd lsl/lsl-backend
conda activate lsl
python scripts/password_reset/check_and_reset_password.py
```

### 方案4: 直接使用SQL解锁（密码需要Django生成）

如果Django环境暂时不可用，可以先解锁账号:

```sql
-- 解锁账号
UPDATE lsl_system_users 
SET is_active = 1, 
    login_error_count = 0
WHERE username = 'superadmin';
```

**注意**: 密码重置仍然需要Django环境，因为PBKDF2哈希需要使用Django的`make_password`函数生成。

## 验证登录

重置密码后，使用以下账号密码登录:

- **账号**: `superadmin`
- **密码**: `admin123456`

## 根本解决方案（可选）

为了避免将来再次出现此问题，建议修复 `dvadmin/system/models.py` 中的 `set_password` 方法:

```python
def set_password(self, raw_password):
    if raw_password:
        # 直接使用原始密码，让Django的set_password处理哈希
        # 注意：这会导致现有密码无法使用，需要迁移
        super().set_password(raw_password)
```

**警告**: 修改此方法后，所有现有用户的密码都需要重新设置！

## 当前状态

✅ **账号已解锁** - 已通过SQL直接解锁
⏳ **密码待重置** - 需要Django环境来生成正确的PBKDF2哈希

## 下一步操作

1. 确保Django环境可用（可以运行`python manage.py shell`）
2. 使用方案1重置密码
3. 使用新密码登录测试

## 脚本位置

所有密码重置相关的脚本已移动到 `scripts/password_reset/` 目录，包括：
- `check_and_reset_password.py` - 检查并重置密码（需要Django环境）
- `check_password_format.py` - 检查密码格式（不依赖Django）
- `fix_superadmin_simple.py` - 简单解锁脚本（不依赖Django）
- `fix_superadmin.py` - Django shell脚本
- `unlock_and_reset_sql.sql` - SQL解锁脚本
- 更多脚本请查看 `scripts/password_reset/README.md`

