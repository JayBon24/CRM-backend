import multiprocessing
import os
import sys
import socket

root_path = os.getcwd()
sys.path.append(root_path)
import uvicorn
from application.settings import LOGGING, DEBUG


def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_startup_banner(host="0.0.0.0", port=8000, is_dev=True):
    """打印启动横幅"""
    import sys
    import io
    
    # 设置标准输出编码为UTF-8（Windows兼容）
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    local_ip = get_local_ip()
    
    # ANSI 颜色代码
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    banner = f"""
{CYAN}{'='*80}{RESET}
{BOLD}{MAGENTA}
   Law Smart Link Backend Server
{RESET}
{CYAN}{'='*80}{RESET}

{BOLD}{GREEN}[OK] Service Started Successfully!{RESET}

{BOLD}Access URLs:{RESET}
  {GREEN}->{RESET} Local:       {BLUE}http://localhost:{port}/{RESET}
  {GREEN}->{RESET} Local:       {BLUE}http://127.0.0.1:{port}/{RESET}
  {GREEN}->{RESET} Network:     {BLUE}http://{local_ip}:{port}/{RESET}

{BOLD}API Documentation:{RESET}
  {GREEN}->{RESET} Swagger:     {BLUE}http://localhost:{port}/admin-api/swagger/{RESET}
  {GREEN}->{RESET} ReDoc:        {BLUE}http://localhost:{port}/admin-api/redoc/{RESET}

{BOLD}Running Mode:{RESET}
  {GREEN}->{RESET} Environment:  {YELLOW}{'Development' if is_dev else 'Production'}{RESET}
  {GREEN}->{RESET} Debug Mode:   {YELLOW}{'ON (DEBUG=True)' if DEBUG else 'OFF (DEBUG=False)'}{RESET}
  {GREEN}->{RESET} Hot Reload:   {YELLOW}{'Enabled' if is_dev else 'Disabled'}{RESET}

{BOLD}Quick Actions:{RESET}
  {GREEN}->{RESET} Stop Server:  Press {RED}{BOLD}Ctrl + C{RESET}
  {GREEN}->{RESET} View Logs:    {BLUE}logs/server.log{RESET}

{BOLD}Tips:{RESET}
  {YELLOW}*{RESET} Configure database in {BLUE}conf/env.py{RESET}
  {YELLOW}*{RESET} API requires authentication, login at {BLUE}/admin-api/login/{RESET}
  {YELLOW}*{RESET} Code changes auto-reload in development mode
  {YELLOW}*{RESET} Check {BLUE}logs/error.log{RESET} for errors

{CYAN}{'='*80}{RESET}
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        # 如果仍然有编码问题，使用简化版本
        print("=" * 80)
        print("Law Smart Link Backend Server")
        print("=" * 80)
        print(f"[OK] Service Started Successfully!")
        print(f"Access: http://localhost:{port}/")
        print(f"API Docs: http://localhost:{port}/admin-api/swagger/")
        print(f"Mode: {'Development' if is_dev else 'Production'}")
        print("Press Ctrl+C to stop")
        print("=" * 80)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    # 判断是否为开发环境
    is_dev = os.environ.get('ENV', 'development') == 'development'
    
    workers = 4
    if os.sys.platform.startswith('win'):
        # Windows操作系统
        workers = None
    
    # 打印启动横幅
    print_startup_banner(host="0.0.0.0", port=8000, is_dev=is_dev)
    
    # 开发环境启用热更新，生产环境关闭
    uvicorn.run("application.asgi:application", reload=is_dev, host="0.0.0.0", port=8000, workers=workers,
                log_config=LOGGING)
