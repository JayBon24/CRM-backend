## lsl-backend

后端服务（Django 4.2），推荐使用 Python 3.11.x。

> 🚀 **快速开始**: 查看 [QUICK_START.md](QUICK_START.md) 一键启动指南
>
> 💡 **新功能**: 
> - ✅ Conda 环境自动激活
> - ✅ 热更新智能切换
> - ✅ 一键启动脚本

### 运行环境
- Python 3.11.x
- 可选：MySQL 8+/PostgreSQL、Redis（用于 channels/celery）

### 一、创建虚拟环境并安装依赖（使用国内源）

#### 方式1：使用 Conda（推荐）✨

**本项目已包含 `.conda` 本地环境，所有启动脚本会自动检测并激活！**

```bash
# 如果没有 .conda 环境，创建一个：
conda create --prefix .\.conda python=3.11

# 激活环境并安装依赖
conda activate .\.conda
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

pip install PyJWT==2.8.0 -i https://mirrors.aliyun.com/pypi/simple/
```

> 💡 使用 `dev_start.bat` 启动时会**自动激活 conda 环境**，无需手动激活！

#### 方式2：使用 Venv

Windows（cmd）：
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

Linux/macOS：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 可选：持久设置 pip 国内镜像（任选其一）
```bash
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

### 二、配置环境
复制示例配置为实际配置并根据需要修改数据库/Redis 等：

Windows（cmd）：
```bat
copy conf\env.example.py conf\env.py
```

Linux/macOS：
```bash
cp conf/env.example.py conf/env.py
```

默认使用 `DATABASE_ENGINE = "django.db.backends.mysql"`，如需 SQLite/PostgreSQL 请在 `conf/env.py` 调整。

### 三、初始化数据库
```bash
python manage.py migrate
python manage.py init -y
```

如需收集静态资源（生产环境）：
```bash
python manage.py collectstatic
```

### 四、启动服务

#### 开发模式（带热更新 🔥）

**Windows（推荐）**：
```bash
dev_start.bat
```

**Linux/macOS**：
```bash
chmod +x dev_start.sh
./dev_start.sh
# 或直接运行
ENV=development python main.py
```

**手动启动（带热更新）**：
```bash
uvicorn application.asgi:application --reload --host 0.0.0.0 --port 8000
```

> 💡 开发模式下，修改代码后会自动重新加载，无需手动重启服务器！

#### 生产模式（无热更新）

**Windows**：
```bash
prod_start.bat
# 或
quick_start.bat
```

**Linux/macOS**：
```bash
ENV=production python main.py
# 或
gunicorn -c gunicorn_conf.py application.asgi:application
# 或
uvicorn application.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

#### Django 自带开发服务器（可选）：
```bash
python manage.py runserver 0.0.0.0:8000
```

> ⚠️ 生产环境请勿使用 Django runserver，推荐使用 Gunicorn 或 Uvicorn 多进程模式

### 五、可选组件

Channels（WebSocket）：
- 默认使用内存通道层，可直接运行。
- 如需 Redis，请在 `application/settings.py` 启用 `channels_redis` 配置并确保 Redis 在线。

Celery（任务队列，可选，如使用到定时/异步任务）：
```bash
celery -A application worker -l info
celery -A application beat -l info
```

### 六、环境与功能说明

#### Conda 环境（自动支持）🐍

项目**自动检测并激活** `.conda` 本地环境：
- ✅ 所有启动脚本自动激活
- ✅ 无需手动 `conda activate`
- ✅ 环境隔离，依赖独立

详细说明：[Conda环境使用说明](docs/Conda环境使用说明.md)

#### 热更新（智能切换）🔥

- **开发模式**: 自动启用热更新，代码修改后自动重新加载
- **生产模式**: 自动禁用热更新，保证性能和稳定性

详细说明：[热更新配置文档](docs/热更新配置说明.md)

### 常见问题
- 安装慢：请确认使用了国内源（见上文 pip 镜像设置）。
- 数据库连接失败：检查 `conf/env.py` 中的 `DATABASE_HOST`、`DATABASE_USER`、`DATABASE_PASSWORD`、`DATABASE_PORT`。
- 静态资源 404（生产）：执行 `python manage.py collectstatic` 并正确配置静态资源服务。
- 热更新未生效：确认使用 `dev_start.bat` 或设置 `ENV=development` 环境变量。


# 修改或者新增模型之后，运行以下命令，会自动迁移数据库（创建迁移文件并执行迁移）
python manage.py makemigrations customer_management
python manage.py migrate



测试登录用户名与密码：
superadmin
admin12456