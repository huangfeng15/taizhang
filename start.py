"""
快捷启动脚本 - HTTPS服务器
使用方法：python start.py
"""
import os
import sys

def start_server():
    """启动HTTPS服务器"""
    print("=" * 50)
    print("项目采购管理系统 - HTTPS服务器")
    print("=" * 50)
    print()
    print("正在启动...")
    print("访问地址: https://10.168.3.240:3500")
    print()
    print("提示：按 Ctrl+C 停止服务器")
    print()
    
    # 构建启动命令
    cmd = "python manage.py runserver_plus --cert-file ssl/cert.pem --key-file ssl/key.pem 0.0.0.0:3500"
    
    # 执行命令
    os.system(cmd)

if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)