# frps Docker 部署指南

## 📋 配置说明

### ✅ 已优化内容

1. **添加了 HTTP/HTTPS 端口配置**
   - `vhost_http_port = 8080` - HTTP 代理端口（内部端口，因为 80 被 Traefik 占用）
   - `vhost_https_port = 8443` - HTTPS 代理端口（内部端口，因为 443 被 Traefik 占用）

2. **添加了端口映射**
   - `8080:8080` - HTTP 代理（内部端口，Traefik 会转发）
   - `8443:8443` - HTTPS 代理（内部端口，Traefik 会转发）
   - **注意**：80/443 端口被 Traefik 占用，frps 使用内部端口，通过域名访问

3. **添加了日志卷挂载**
   - 方便查看和管理日志

4. **添加了高级配置**
   - 连接池、心跳超时等配置

5. **添加了 Traefik 配置**
   - 管理面板通过域名访问：`https://frps.izhule.cn`
   - 自动 HTTPS（Let's Encrypt）
   - HTTP 自动重定向到 HTTPS

## 🚀 快速开始

### 1. 修改配置

**⚠️ 重要：必须修改以下配置**

编辑 `frps.ini`：
```ini
# 修改为强密码（建议使用随机字符串）
token = your_strong_password_here

# 修改管理面板密码
dashboard_user = admin
dashboard_pwd = your_strong_password_here
```

### 2. 创建日志目录（可选）

```bash
mkdir -p logs
```

### 3. 确保 Traefik 网络存在

```bash
# 如果 traefik-public 网络不存在，创建它
docker network create traefik-public
```

### 4. 启动服务

```bash
# 启动 frps 服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

### 5. 访问管理面板

**通过 Traefik 域名访问（推荐）：**
- 访问地址：`https://frps.izhule.cn`
- 用户名：admin（或你在配置中设置的）
- 密码：admin（或你在配置中设置的）

**注意：**
- Traefik 会自动处理 HTTPS 证书（Let's Encrypt）
- HTTP 请求会自动重定向到 HTTPS
- 确保域名 `frps.izhule.cn` 已解析到服务器 IP

## 🔧 客户端配置

在本地 Windows 机器上配置 `frpc.ini`：

```ini
[common]
server_addr = your_server_ip_or_domain
server_port = 7000
token = your_strong_password_here  # 与服务端保持一致

[web_https]
type = https
local_ip = 127.0.0.1
local_port = 8000
custom_domains = api.yourdomain.com
```

## 📝 WPS 回调配置

在 WPS 配置中填入：
```
回调地址：https://api.yourdomain.com/api/case/document/wps/callback/
```

**注意：**
1. 确保域名已解析到服务器 IP
2. 如果使用 HTTPS，需要配置 SSL 证书（推荐使用 Nginx + Let's Encrypt 或 Traefik）
3. Django 的 `ALLOWED_HOSTS` 需要包含你的域名

## 🌐 Traefik 配置说明

### 配置详情

- **管理面板域名**：`frps.izhule.cn`（通过 Traefik 访问）
- **HTTPS**：自动通过 Let's Encrypt 获取证书
- **HTTP 重定向**：自动重定向到 HTTPS
- **网络**：使用 `traefik-public` 网络
- **端口说明**：
  - 80/443 端口被 Traefik 占用
  - frps 使用内部端口 8080/8443
  - 客户端通过域名访问，Traefik 自动路由到 frps

### 重要说明

**端口冲突处理：**
- 由于 80/443 端口被 Traefik 占用，frps 使用内部端口 8080/8443
- 客户端配置的域名（如 `api.yourdomain.com`）的请求会：
  1. 首先到达 Traefik（监听 80/443）
  2. Traefik 根据域名路由规则转发到 frps 的内部端口（8080/8443）
  3. frps 根据 Host header 判断应该转发到哪个客户端

**Traefik TCP 路由配置（可选）：**

如果你的客户端配置了多个域名，需要在 Traefik 中配置 TCP 路由，将对应域名的流量转发到 frps。例如：

```yaml
# 在 Traefik 配置中添加 TCP 路由
tcp:
  routers:
    frps-http:
      rule: "HostSNI(`*`)"  # 或指定具体域名
      service: frps-http
      entryPoints:
        - web
    frps-https:
      rule: "HostSNI(`*`)"  # 或指定具体域名
      service: frps-https
      entryPoints:
        - websecure
  services:
    frps-http:
      loadBalancer:
        servers:
          - address: "frps:8080"
    frps-https:
      loadBalancer:
        servers:
          - address: "frps:8443"
```

或者，更简单的方式是使用 Traefik 的 HTTP 路由，将特定域名转发到 frps。

### Traefik 要求

确保你的 Traefik 配置包含：

1. **Entrypoints**：
   - `web`：HTTP 入口（通常 80 端口）
   - `websecure`：HTTPS 入口（通常 443 端口）

2. **Certificate Resolver**：
   - `letsencrypt`：Let's Encrypt 证书解析器

3. **Docker Provider**：
   - 启用 Docker provider 以自动发现服务

### 域名 DNS 配置

在域名管理平台添加 A 记录：
- **主机记录**：`frps`
- **记录类型**：`A`
- **记录值**：服务器 IP 地址
- **TTL**：600（10分钟）

### 验证 Traefik 配置

```bash
# 检查容器是否在 traefik-public 网络中
docker network inspect traefik-public

# 查看 Traefik 日志
docker logs traefik

# 测试域名访问
curl -I https://frps.izhule.cn
```

## 🔒 安全建议

1. **修改默认密码**
   - `token` 必须修改为强密码
   - `dashboard_pwd` 必须修改为强密码

2. **防火墙配置**
   ```bash
   # 开放必要端口
   firewall-cmd --permanent --add-port=7000/tcp  # frp 客户端连接端口
   firewall-cmd --permanent --add-port=80/tcp    # Traefik HTTP（已开放）
   firewall-cmd --permanent --add-port=443/tcp    # Traefik HTTPS（已开放）
   # 注意：8080/8443 是内部端口，不需要在防火墙开放
   firewall-cmd --reload
   ```

3. **限制管理面板访问**
   - 考虑使用防火墙只允许特定 IP 访问
   - 或使用 Traefik 中间件添加 IP 白名单

4. **HTTPS 配置（已配置）**
   - Traefik 自动处理 HTTPS（Let's Encrypt）
   - HTTP 自动重定向到 HTTPS
   - 无需手动配置 SSL 证书

## 📊 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f frps

# 查看状态
docker-compose ps

# 进入容器
docker exec -it frps sh
```

## 🐛 故障排查

### 1. 端口被占用
```bash
# 检查端口占用
netstat -tulpn | grep -E '7000|7500|80|443'

# 或使用 ss
ss -tulpn | grep -E '7000|7500|80|443'
```

### 2. 查看日志
```bash
# Docker 日志
docker-compose logs -f frps

# 容器内日志文件
docker exec frps cat /var/log/frps.log
```

### 3. 测试连接
```bash
# 测试服务端端口
telnet your_server_ip 7000

# 或使用 nc
nc -zv your_server_ip 7000
```

## 📚 参考文档

- frp 官方文档：https://gofrp.org/docs/
- Docker 镜像：https://hub.docker.com/r/snowdreamtech/frps

