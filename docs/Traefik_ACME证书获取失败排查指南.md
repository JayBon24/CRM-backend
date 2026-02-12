# Traefik ACME 证书获取失败排查指南

## 问题描述

Traefik 无法获取 Let's Encrypt SSL 证书，常见的错误类型：

### 错误类型 1: 网络连接错误

```
Unable to obtain ACME certificate for domains "frps.izhule.cn": 
cannot get ACME client get directory at 'https://acme-v02.api.letsencrypt.org/directory': 
Get "https://acme-v02.api.letsencrypt.org/directory": 
dial tcp 172.65.32.248:443: connect: no route to host
```

### 错误类型 2: TLS 验证错误（新增）

```
Error renewing certificate from LE: {www.izhule.cn [art.izhule.cn admin.izhule.cn]}" 
ACME CA="https://acme-v02.api.letsencrypt.org/directory" 
error="error: one or more domains had a problem:
[www.izhule.cn] acme: error: 400 :: urn:ietf:params:acme:error:tls :: 120.24.108.115: remote error: tls: unrecognized name
```

## 原因分析

### 错误类型 1: `no route to host` 错误

表示服务器无法路由到目标主机，可能的原因：

1. **网络连接问题**：服务器无法访问外网
2. **防火墙阻止**：出站 HTTPS (443) 连接被阻止
3. **DNS 解析问题**：无法解析 Let's Encrypt 服务器域名
4. **路由配置问题**：网络路由表配置错误
5. **代理设置问题**：需要配置代理但未配置

### 错误类型 2: `tls: unrecognized name` 错误

表示 Let's Encrypt 在验证域名时，遇到了 TLS 证书不匹配的问题，可能的原因：

1. **证书域名不匹配**：服务器 443 端口上的证书不是针对请求验证的域名
2. **默认证书问题**：Traefik 或其他服务使用了错误的默认证书
3. **端口冲突**：多个服务同时监听 443 端口，Let's Encrypt 连接到了错误的服务
4. **旧证书残留**：之前配置的证书还在使用，但域名已更改
5. **SNI（Server Name Indication）问题**：服务器没有正确响应 SNI 请求
6. **DNS 解析问题**：域名 DNS 记录指向了错误的 IP 地址或服务器

## 排查步骤

### 1. 检查网络连接

在服务器上测试能否访问 Let's Encrypt 服务器：

```bash
# 测试 DNS 解析
nslookup acme-v02.api.letsencrypt.org

# 测试 HTTPS 连接
curl -I https://acme-v02.api.letsencrypt.org/directory

# 或使用 wget
wget -O- https://acme-v02.api.letsencrypt.org/directory

# 测试端口连通性
telnet acme-v02.api.letsencrypt.org 443
# 或使用 nc
nc -zv acme-v02.api.letsencrypt.org 443
```

### 2. 检查防火墙规则

```bash
# 检查防火墙状态（CentOS/RHEL）
systemctl status firewalld

# 检查出站规则
iptables -L OUTPUT -n -v

# 检查是否有阻止 443 端口的规则
iptables -L -n | grep 443

# 如果使用 firewalld，临时允许所有出站连接（测试用）
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="0.0.0.0/0" accept'
firewall-cmd --reload
```

### 3. 检查 Docker 网络配置

```bash
# 检查 Docker 网络
docker network ls

# 检查 Traefik 容器的网络配置
docker inspect traefik | grep -A 20 "Networks"

# 检查路由表
ip route show

# 检查默认网关
ip route | grep default
```

### 4. 检查 DNS 配置

```bash
# 检查系统 DNS 配置
cat /etc/resolv.conf

# 检查 Docker DNS 配置
docker inspect traefik | grep -i dns

# 测试 DNS 解析
dig acme-v02.api.letsencrypt.org
nslookup acme-v02.api.letsencrypt.org
```

### 5. 在 Traefik 容器内测试（重要！）

**如果宿主机可以访问外网，但容器内无法访问，问题在 Docker 网络配置。**

```bash
# 进入 Traefik 容器
docker exec -it traefik sh

# 在容器内测试连接
wget -O- https://acme-v02.api.letsencrypt.org/directory
# 或
curl -I https://acme-v02.api.letsencrypt.org/directory

# 测试 DNS 解析
nslookup acme-v02.api.letsencrypt.org

# 如果容器内没有 wget/curl，使用 ping 测试 DNS
ping -c 3 acme-v02.api.letsencrypt.org

# 检查容器内的 DNS 配置
cat /etc/resolv.conf

# 检查容器内的路由表
ip route show
```

**如果容器内无法访问外网，参考下面的 Docker 网络修复方案。**

### 6. 针对 "tls: unrecognized name" 错误的排查步骤

**如果遇到 `tls: unrecognized name` 错误，说明 Let's Encrypt 可以连接到服务器，但遇到了证书不匹配的问题。**

#### 6.1 检查域名 DNS 解析

```bash
# 检查域名是否正确解析到服务器 IP
nslookup www.izhule.cn
nslookup art.izhule.cn
nslookup admin.izhule.cn

# 使用 dig 获取更详细信息
dig www.izhule.cn +short
dig art.izhule.cn +short
dig admin.izhule.cn +short

# 确认所有域名都指向正确的服务器 IP
# 如果错误日志显示 IP 是 120.24.108.115，确认域名是否都指向这个 IP
```

#### 6.2 检查 443 端口的服务

```bash
# 检查是否有服务在监听 443 端口
netstat -tlnp | grep 443
# 或
ss -tlnp | grep 443

# 检查 Docker 容器的端口映射
docker ps | grep 443
docker port traefik  # 查看 Traefik 的端口映射

# 检查是否有多个服务同时监听 443 端口
# 如果有，需要停止冲突的服务或修改配置
```

#### 6.3 测试 HTTPS 连接和证书

```bash
# 测试 HTTPS 连接，查看服务器返回的证书
openssl s_client -connect www.izhule.cn:443 -servername www.izhule.cn < /dev/null

# 查看证书的详细信息，特别关注：
# - Subject Alternative Name (SAN) 字段
# - 证书是否包含验证的域名
# - 证书是否过期

# 使用 curl 测试（会显示证书信息）
curl -vI https://www.izhule.cn 2>&1 | grep -i "subject\|issuer\|expire"

# 测试所有需要证书的域名
for domain in www.izhule.cn art.izhule.cn admin.izhule.cn; do
  echo "Testing $domain:"
  openssl s_client -connect $domain:443 -servername $domain < /dev/null 2>&1 | grep -i "subject\|verify\|error"
done
```

#### 6.4 检查 Traefik 配置

```bash
# 查看 Traefik 的配置
docker exec traefik cat /etc/traefik/traefik.yml  # 或你的配置文件路径

# 检查是否有默认证书配置
# 如果有 defaultCertificate，确认它是否影响了新证书的获取

# 检查证书存储位置
docker exec traefik ls -la /letsencrypt/  # 或你的证书存储路径
docker exec traefik cat /letsencrypt/acme.json  # 查看现有证书（注意：可能需要解码）

# 检查 Traefik 日志中的详细错误
docker logs traefik | grep -i "acme\|certificate\|tls"
```

#### 6.5 检查是否有其他反向代理或负载均衡器

```bash
# 检查是否有 Nginx、Apache 或其他反向代理在 Traefik 前面
ps aux | grep -E "nginx|apache|httpd"

# 检查是否有云服务商的负载均衡器（如阿里云 SLB、AWS ELB）
# 这些可能需要单独配置 SSL 证书

# 检查防火墙规则，确认 443 端口流量正确路由到 Traefik
iptables -t nat -L -n | grep 443
```

## 解决方案

### ⚠️ 重要：如果宿主机可以访问外网，但容器内无法访问

**这是 Docker 容器网络问题，需要检查 Docker 网络配置。**

#### 诊断步骤

```bash
# 1. 在 Traefik 容器内测试（最关键）
docker exec -it traefik wget -O- https://acme-v02.api.letsencrypt.org/directory

# 2. 检查 Docker 网络
docker network inspect bridge  # 或 traefik 使用的网络
docker network inspect traefik-public  # 如果使用自定义网络

# 3. 检查 Traefik 容器的 DNS 配置
docker inspect traefik | grep -A 10 "Dns"

# 4. 检查 Docker 守护进程的 DNS 配置
cat /etc/docker/daemon.json  # 如果存在
```

#### Docker 网络修复方案

**方案 A: 配置 Docker 守护进程使用系统 DNS**

创建或编辑 `/etc/docker/daemon.json`：

```json
{
  "dns": ["8.8.8.8", "8.8.4.4", "114.114.114.114"],
  "dns-opts": ["timeout:2", "attempts:3"]
}
```

然后重启 Docker 服务：

```bash
systemctl restart docker
# 重启 Traefik 容器
docker restart traefik
```

**方案 B: 在 Docker Compose 中配置 DNS**

如果 Traefik 使用 Docker Compose 部署，添加 DNS 配置：

```yaml
services:
  traefik:
    dns:
      - 8.8.8.8
      - 8.8.4.4
      - 114.114.114.114
    # 或使用环境变量
    environment:
      - TRAEFIK_LOG_LEVEL=INFO
```

**方案 C: 检查 Docker 网络模式**

```bash
# 检查 Traefik 容器的网络模式
docker inspect traefik | grep -i "NetworkMode"

# 如果使用 bridge 模式，确保网络配置正确
# 如果使用 host 模式，应该可以直接访问外网
```

**方案 D: 修复 iptables 和 IP 转发问题（关键！）**

如果容器路由正常但无法访问外网，通常是 iptables 或 IP 转发问题：

```bash
# 1. 检查 IP 转发是否启用
sysctl net.ipv4.ip_forward
# 应该返回 net.ipv4.ip_forward = 1
# 如果是 0，需要启用：
sysctl -w net.ipv4.ip_forward=1
# 永久生效：
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# 2. 检查 iptables NAT 规则
iptables -t nat -L -n -v | grep MASQUERADE

# 3. 检查 Docker 的 iptables 规则
iptables -L DOCKER -n -v
iptables -t nat -L POSTROUTING -n -v

# 4. 如果 Docker 的 MASQUERADE 规则缺失，重启 Docker
systemctl restart docker

# 5. 检查 firewalld 是否影响 Docker（关键！）
systemctl status firewalld
# 如果 firewalld 运行，检查是否允许 Docker 网络转发
firewall-cmd --list-all-zones | grep -A 5 docker
firewall-cmd --query-masquerade
firewall-cmd --list-forward-ports

# 如果 firewalld 阻止了 Docker 网络，需要配置：
# 方法 1：允许 Docker 网络接口（推荐）
firewall-cmd --permanent --zone=public --add-interface=docker0
firewall-cmd --permanent --zone=public --add-interface=br-*
firewall-cmd --reload

# 方法 2：在 firewalld 中启用 masquerade（如果未启用）
firewall-cmd --permanent --add-masquerade
firewall-cmd --reload

# 方法 3：检查 firewalld 的 FORWARD 链规则（关键！）
iptables -L FORWARD -n -v | grep -i firewalld
iptables -L FORWARD -n -v | grep -i docker

# 如果 firewalld 的 FORWARD 链阻止了 Docker 流量，需要添加规则：
# 允许 Docker 网络转发
firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 0 -i br-03f21b39eef0 -j ACCEPT
firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 0 -o br-03f21b39eef0 -j ACCEPT
firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 0 -i docker0 -j ACCEPT
firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 0 -o docker0 -j ACCEPT
firewall-cmd --reload

# 方法 4：如果以上无效，临时禁用 firewalld 测试（仅用于诊断）
# systemctl stop firewalld
# 如果禁用后可以访问，说明是 firewalld 的 FORWARD 规则问题
# 测试完成后记得重启 firewalld
# systemctl start firewalld
```

**方案 E: 使用 host 网络模式（临时测试）**

如果其他方案无效，可以临时使用 host 网络模式测试：

```yaml
services:
  traefik:
    network_mode: "host"
```

**注意**：host 模式会暴露所有端口到宿主机，仅用于测试。

### 方案 1: 配置 DNS 服务器（推荐）

如果 DNS 解析有问题，在 Traefik 配置中指定 DNS 服务器：

```yaml
# docker-compose.yml 或 Traefik 配置
services:
  traefik:
    dns:
      - 8.8.8.8
      - 8.8.4.4
      - 114.114.114.114
    # 或使用环境变量
    environment:
      - TRAEFIK_LOG_LEVEL=INFO
```

### 方案 2: 配置 HTTP 代理（如果需要）

如果服务器需要通过代理访问外网，配置 Traefik 使用代理：

```yaml
services:
  traefik:
    environment:
      - HTTP_PROXY=http://proxy.example.com:8080
      - HTTPS_PROXY=http://proxy.example.com:8080
      - NO_PROXY=localhost,127.0.0.1
```

### 方案 3: 使用自定义 DNS 解析器

在 Traefik 配置文件中添加自定义 DNS：

```yaml
# traefik.yml
log:
  level: INFO

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

certificatesResolvers:
  myresolver:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

# 添加 DNS 配置
experimental:
  plugins:
    acme:
      dnsChallenge:
        provider: "cloudflare"  # 或其他 DNS 提供商
```

### 方案 4: 临时使用自签名证书（不推荐用于生产）

如果无法立即解决网络问题，可以临时使用自签名证书：

```yaml
# 在 Traefik 配置中
certificatesResolvers:
  myresolver:
    acme:
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory  # 使用测试环境
      # 或
      # tlsChallenge: {}  # 使用 TLS 挑战而不是 HTTP 挑战
```

**注意**：测试环境的证书不会被浏览器信任，仅用于测试。

### 方案 5: 检查并修复路由表

```bash
# 查看路由表
ip route show

# 如果缺少默认路由，添加默认网关
# 替换 <gateway_ip> 为你的网关 IP
ip route add default via <gateway_ip>

# 永久保存（根据系统配置）
# CentOS/RHEL
vi /etc/sysconfig/network-scripts/ifcfg-eth0
# 添加或修改：
# GATEWAY=<gateway_ip>
```

### 方案 6: 使用外部证书管理器（备用方案）

如果持续无法解决网络问题，可以考虑：

1. **使用外部证书管理器**（如 cert-manager）手动获取证书
2. **使用其他证书提供商**（如 Cloudflare、ZeroSSL）
3. **使用内网 CA**（如果不需要公网信任）

### 针对 "tls: unrecognized name" 错误的解决方案

#### 方案 A: 移除或修复默认证书配置

如果 Traefik 配置中有 `defaultCertificate`，它可能会干扰新证书的获取：

```yaml
# traefik.yml 或 docker-compose.yml
# 移除或注释掉 defaultCertificate 配置
# certificates:
#   stores:
#     default:
#       defaultCertificate:
#         certFile: /path/to/cert.pem
#         keyFile: /path/to/key.pem
```

**或者**，确保默认证书包含所有需要验证的域名。

#### 方案 B: 清理旧证书并重新获取

```bash
# 1. 停止 Traefik 容器
docker stop traefik

# 2. 备份并删除旧证书（如果存在）
docker exec traefik ls -la /letsencrypt/acme.json
# 备份
docker cp traefik:/letsencrypt/acme.json ./acme.json.backup
# 删除（谨慎操作）
docker exec traefik rm /letsencrypt/acme.json

# 3. 确认没有冲突的服务在监听 443 端口
netstat -tlnp | grep 443
# 如果有其他服务，停止它们

# 4. 重启 Traefik 容器
docker start traefik

# 5. 查看日志，确认证书获取过程
docker logs -f traefik | grep -i acme
```

#### 方案 C: 使用 HTTP Challenge 而不是 TLS Challenge

如果当前使用的是 TLS Challenge，可以尝试切换到 HTTP Challenge：

```yaml
# traefik.yml
certificatesResolvers:
  myresolver:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web  # 使用 80 端口进行验证
      # 移除或注释掉 tlsChallenge
      # tlsChallenge: {}
```

**注意**：HTTP Challenge 需要 80 端口可访问，TLS Challenge 需要 443 端口可访问。

#### 方案 D: 修复 DNS 解析问题

如果域名 DNS 记录不正确：

```bash
# 1. 检查当前 DNS 记录
dig www.izhule.cn +short
dig art.izhule.cn +short
dig admin.izhule.cn +short

# 2. 确认所有域名都指向正确的服务器 IP（如 120.24.108.115）
# 如果 DNS 记录不正确，需要在 DNS 提供商处修改

# 3. 等待 DNS 传播（通常需要几分钟到几小时）
# 可以使用在线工具检查全球 DNS 解析情况

# 4. 验证 DNS 解析后，重新尝试获取证书
docker restart traefik
docker logs -f traefik | grep -i acme
```

#### 方案 E: 检查并修复端口冲突

如果有多个服务监听 443 端口：

```bash
# 1. 查找所有监听 443 端口的进程
netstat -tlnp | grep 443
ss -tlnp | grep 443

# 2. 检查 Docker 容器的端口映射
docker ps --format "table {{.Names}}\t{{.Ports}}"

# 3. 停止冲突的服务
# 例如，如果有 Nginx 在监听 443：
systemctl stop nginx
# 或停止冲突的容器
docker stop <container-name>

# 4. 确保只有 Traefik 监听 443 端口
netstat -tlnp | grep 443

# 5. 重启 Traefik 并重新获取证书
docker restart traefik
```

#### 方案 F: 使用 DNS Challenge（如果 HTTP/TLS Challenge 都失败）

DNS Challenge 不需要开放端口，但需要配置 DNS API：

```yaml
# traefik.yml
certificatesResolvers:
  myresolver:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      dnsChallenge:
        provider: cloudflare  # 或其他支持的 DNS 提供商
        # 需要配置相应的环境变量或 API 密钥
```

**注意**：需要配置 DNS 提供商的 API 密钥，具体配置参考 Traefik 文档。

#### 方案 G: 临时禁用 HTTPS 自动重定向（测试用）

如果问题是由于 Traefik 的自动 HTTPS 重定向导致的，可以临时禁用：

```yaml
# traefik.yml
entryPoints:
  web:
    address: ":80"
    # 临时注释掉重定向
    # http:
    #   redirections:
    #     entryPoint:
    #       to: websecure
    #       scheme: https
  websecure:
    address: ":443"
```

**注意**：这只是用于诊断，生产环境应该使用 HTTPS。

#### 方案 H: 检查云服务商负载均衡器配置

如果服务器前面有云服务商的负载均衡器（如阿里云 SLB、AWS ELB）：

1. **确认负载均衡器是否终止 SSL**：如果负载均衡器终止了 SSL，Traefik 可能无法获取证书
2. **配置直通模式**：将负载均衡器配置为直通模式，让 SSL 终止在 Traefik
3. **在负载均衡器上配置证书**：如果使用负载均衡器终止 SSL，需要在负载均衡器上配置证书，而不是 Traefik

#### 方案 I: 增加日志级别获取详细信息

```yaml
# traefik.yml
log:
  level: DEBUG  # 改为 DEBUG 获取更详细的错误信息
```

然后查看详细日志：

```bash
docker logs -f traefik | grep -i -A 10 "acme\|certificate\|tls\|error"
```

## 验证修复

修复后，验证证书获取是否成功：

```bash
# 查看 Traefik 日志
docker logs -f traefik | grep -i acme

# 检查证书文件（如果使用文件存储）
ls -la /path/to/letsencrypt/acme.json

# 测试域名访问
curl -I https://frps.izhule.cn

# 检查证书信息
openssl s_client -connect frps.izhule.cn:443 -servername frps.izhule.cn
```

## 常见问题

### Q: 为什么会出现 "no route to host" 错误？

A: 这通常表示：
- 网络路由配置错误
- 防火墙阻止了出站连接
- 服务器无法访问外网
- DNS 解析失败导致无法找到目标主机

### Q: 如何确认是网络问题还是 Traefik 配置问题？

A: 在服务器上直接测试：
```bash
curl -I https://acme-v02.api.letsencrypt.org/directory
```
如果这个命令也失败，说明是网络问题，不是 Traefik 配置问题。

### Q: 可以临时禁用 HTTPS 吗？

A: 可以，但需要修改 Traefik 配置，移除证书解析器配置，只使用 HTTP。**不推荐用于生产环境**。

### Q: 如何查看详细的错误信息？

A: 增加 Traefik 日志级别：
```yaml
log:
  level: DEBUG  # 改为 DEBUG 获取更详细信息
```

### Q: 为什么会出现 "tls: unrecognized name" 错误？

A: 这个错误表示 Let's Encrypt 在验证域名时，连接到了服务器的 443 端口，但服务器返回的证书不匹配验证的域名。常见原因：

1. **默认证书问题**：Traefik 使用了错误的默认证书
2. **旧证书残留**：之前的证书还在使用，但域名已更改
3. **端口冲突**：多个服务同时监听 443 端口，Let's Encrypt 连接到了错误的服务
4. **DNS 解析错误**：域名 DNS 记录指向了错误的 IP 或服务器
5. **SNI 问题**：服务器没有正确响应 Server Name Indication 请求

**排查步骤**：
```bash
# 1. 检查域名 DNS 解析
dig www.izhule.cn +short

# 2. 测试 HTTPS 连接和证书
openssl s_client -connect www.izhule.cn:443 -servername www.izhule.cn < /dev/null

# 3. 检查是否有端口冲突
netstat -tlnp | grep 443

# 4. 查看 Traefik 配置中的默认证书
docker exec traefik cat /etc/traefik/traefik.yml | grep -i certificate
```

### Q: 如何确认是证书问题还是 DNS 问题？

A: 执行以下测试：

```bash
# 1. 测试 DNS 解析
dig www.izhule.cn +short
# 如果返回的 IP 不是你的服务器 IP，说明是 DNS 问题

# 2. 测试 HTTPS 连接
curl -vI https://www.izhule.cn 2>&1 | grep -i "subject\|issuer\|error"
# 查看证书信息，确认证书是否包含验证的域名

# 3. 测试从外部访问
# 使用在线工具（如 https://www.ssllabs.com/ssltest/）测试域名
# 查看证书详情和域名匹配情况
```

### Q: "tls: unrecognized name" 和 "no route to host" 有什么区别？

A: 

- **"no route to host"**：服务器无法连接到 Let's Encrypt 服务器，这是网络连接问题
- **"tls: unrecognized name"**：服务器可以连接到 Let's Encrypt，也可以连接到你的服务器，但证书不匹配，这是证书配置问题

**快速判断**：
```bash
# 如果这个命令失败，说明是网络问题（no route to host）
curl -I https://acme-v02.api.letsencrypt.org/directory

# 如果这个命令失败或显示证书错误，说明是证书问题（tls: unrecognized name）
curl -vI https://www.izhule.cn
```

## 预防措施

### 针对网络连接问题（no route to host）

1. **确保服务器可以访问外网**
   - 检查防火墙规则
   - 验证网络连接

2. **配置正确的 DNS 服务器**
   - 使用可靠的 DNS 服务器（如 8.8.8.8, 114.114.114.114）

3. **监控证书过期**
   - 设置监控告警
   - 定期检查证书状态

4. **使用证书自动续期**
   - 确保 Traefik 可以正常访问 Let's Encrypt 服务器
   - 定期检查日志

### 针对证书验证问题（tls: unrecognized name）

1. **确保 DNS 记录正确**
   - 定期检查域名 DNS 解析
   - 确保所有需要证书的域名都指向正确的服务器 IP
   - 使用 DNS 监控工具监控 DNS 变化

2. **避免端口冲突**
   - 确保只有 Traefik 监听 443 端口
   - 停止其他可能冲突的服务（如 Nginx、Apache）
   - 检查 Docker 容器的端口映射

3. **正确配置默认证书**
   - 如果使用 `defaultCertificate`，确保它包含所有需要验证的域名
   - 或者移除 `defaultCertificate`，让 Traefik 自动获取证书

4. **使用 HTTP Challenge 而不是 TLS Challenge**
   - HTTP Challenge 通常更稳定，因为它使用 80 端口
   - TLS Challenge 需要 443 端口，可能更容易遇到证书问题

5. **定期清理旧证书**
   - 定期检查证书存储位置
   - 删除不再使用的旧证书
   - 确保证书文件权限正确

6. **监控证书获取状态**
   - 定期查看 Traefik 日志
   - 设置告警监控证书获取失败
   - 使用监控工具检查证书有效期

7. **验证 HTTPS 访问**
   - 定期测试所有域名的 HTTPS 访问
   - 使用在线工具（如 SSL Labs）检查证书状态
   - 确保证书包含所有需要的域名

## 相关资源

- [Let's Encrypt 官方文档](https://letsencrypt.org/docs/)
- [Traefik ACME 配置文档](https://doc.traefik.io/traefik/https/acme/)
- [Traefik 故障排查](https://doc.traefik.io/traefik/troubleshooting/)

