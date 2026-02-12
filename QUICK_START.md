# 🚀 快速开始指南

## 一键启动（推荐）

### 开发模式（热更新 + Conda环境）

```bash
dev_start.bat
```

**自动完成**：
- ✅ 停止旧进程
- ✅ 激活 `.conda` 环境
- ✅ 启用热更新
- ✅ 启动服务器

**修改代码后自动重新加载，无需重启！** 🔥

---

### 生产模式（无热更新 + Conda环境）

```bash
prod_start.bat
# 或
quick_start.bat
```

---

## 环境说明

### Conda 环境 🐍

项目使用本地 Conda 环境：`.conda`

**自动激活**：
- 所有启动脚本会自动检测并激活
- 无需手动运行 `conda activate`
- 环境独立，不污染全局

**手动管理**（可选）：
```bash
# 激活环境
conda activate .\.conda

# 安装新包
pip install package_name

# 更新依赖列表
pip freeze > requirements.txt
```

---

### 热更新 🔥

**开发模式**（`dev_start.bat`）：
- ✅ 热更新已启用
- ✅ 代码修改自动重新加载
- ✅ 无需手动重启

**生产模式**（`prod_start.bat`）：
- ❌ 热更新已禁用
- ✅ 性能更好
- ✅ 稳定性更高

---

## 常见操作

### 首次运行

```bash
# 1. 安装依赖（如果还没装）
.\.conda\python.exe -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 2. 配置数据库
copy conf\env.example.py conf\env.py
# 编辑 conf\env.py 配置数据库连接

# 3. 初始化数据库和组织架构
migrate_and_init.bat
# 或手动执行：
# .\.conda\python.exe manage.py migrate
# .\.conda\python.exe manage.py init -y
# .\.conda\python.exe scripts\init_test_organization.py

# 4. 启动开发服务器
dev_start.bat
```

### 数据库迁移（新增功能）

```bash
# 方案1：一键迁移和初始化（推荐）
migrate_and_init.bat

# 方案2：仅创建迁移文件
create_migrations.bat

# 方案3：手动执行
.\.conda\python.exe manage.py makemigrations
.\.conda\python.exe manage.py migrate
.\.conda\python.exe scripts\init_test_organization.py
```

**测试账号**（初始化后可用）：
- `hq_admin` / `123456` - 总所管理
- `branch_manager` / `123456` - 分所管理
- `team_leader` / `123456` - 团队管理
- `sales_rep` / `123456` - 销售
- `sales_rep2` / `123456` - 销售

### 日常开发

```bash
# 启动服务
dev_start.bat

# 修改代码
# ... 编辑文件，保存后自动重新加载 ...

# 安装新包
.\.conda\python.exe -m pip install new-package
.\.conda\python.exe -m pip freeze > requirements.txt

# 数据库迁移（添加新字段/表）
create_migrations.bat
.\.conda\python.exe manage.py migrate
```

### 部署生产

```bash
# 生产模式启动
prod_start.bat

# 或使用 Gunicorn（Linux）
gunicorn -c gunicorn_conf.py application.asgi:application
```

---

## 故障排除

### 问题：Conda 环境激活失败

**现象**：
```
[警告] 激活本地环境失败，尝试使用系统 Python
```

**解决**：
```bash
# 1. 检查 conda 是否安装
conda --version

# 2. 如果未安装，下载 Miniconda
# https://docs.conda.io/en/latest/miniconda.html

# 3. 初始化 conda
conda init cmd.exe

# 4. 重启命令行窗口
```

### 问题：热更新不工作

**检查**：
```bash
# 确认使用了开发模式启动
dev_start.bat

# 或手动设置环境变量
set ENV=development
python main.py
```

### 问题：端口被占用

**解决**：
```bash
# 查找占用 8000 端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID [进程ID] /F

# 或直接运行启动脚本（会自动停止旧进程）
dev_start.bat
```

---

## 访问服务

启动成功后，访问：

- **API 文档**: http://localhost:8000/api/docs/
- **Admin 后台**: http://localhost:8000/admin/
- **API 根路径**: http://localhost:8000/api/

---

## 详细文档

- [完整 README](README.md)
- [数据库迁移操作指南](docs/数据库迁移操作指南.md) ⭐ 新增
- [组织架构实现方案](docs/组织架构实现方案-最终版.md) ⭐ 新增
- [需求分析与实现计划](docs/需求分析与实现计划.md) ⭐ 新增
- [Conda环境使用说明](docs/Conda环境使用说明.md)
- [热更新配置说明](docs/热更新配置说明.md)
- [案件管理API文档](docs/案件管理API文档.md)
- [案件立案与删除API文档](docs/案件立案与删除API文档.md)

---

## 技术栈

- Python 3.11.x
- Django 4.2
- Django REST Framework
- Uvicorn (ASGI Server)
- MySQL 8+ / PostgreSQL
- Redis (可选)

---

**Happy Coding! 🎉**

