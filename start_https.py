"""
HTTPS模式启动脚本
自动检测证书，使用runserver启动Django HTTPS服务
适用于开发测试环境
"""
import os
import sys
from pathlib import Path

def check_certificates():
    """检查SSL证书是否存在"""
    cert_dir = Path("ssl_certs")
    cert_file = cert_dir / "server.crt"
    key_file = cert_dir / "server.key"
    
    if not cert_file.exists() or not key_file.exists():
        print("\n" + "="*70)
        print("[错误] SSL证书未找到！")
        print("="*70)
        print("请先运行以下命令生成证书:")
        print("   python generate_ssl_cert.py")
        print("="*70 + "\n")
        sys.exit(1)
    
    return str(cert_file.absolute()), str(key_file.absolute())

def check_dependencies():
    """检查并安装必要的依赖"""
    try:
        import django_extensions
        import werkzeug
    except ImportError:
        print("\n" + "="*70)
        print("[安装] 正在安装HTTPS服务所需依赖...")
        print("="*70)
        import subprocess
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "django-extensions", "werkzeug", "pyOpenSSL"
            ])
            print("[成功] 依赖安装成功")
        except Exception as e:
            print(f"[错误] 依赖安装失败: {e}")
            print("\n请手动运行: pip install django-extensions werkzeug pyOpenSSL")
            sys.exit(1)

def main():
    """启动HTTPS服务"""
    print("\n" + "="*70)
    print("台账系统 - HTTPS模式启动")
    print("="*70)
    
    # 检查证书
    cert_file, key_file = check_certificates()
    print(f"[就绪] 证书文件: {cert_file}")
    print(f"[就绪] 私钥文件: {key_file}")
    
    # 检查依赖
    check_dependencies()
    
    # 设置Django环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # 启动参数
    host = "0.0.0.0"
    port = 3500
    
    print("\n" + "="*70)
    print("[启动] 正在启动HTTPS服务...")
    print("="*70)
    print(f"本地访问: https://localhost:{port}")
    print(f"局域网访问: https://10.168.3.240:{port}")
    print(f"监听地址: {host}:{port}")
    print("\n使用提示:")
    print("   - 首次访问浏览器会显示不安全警告，这是正常的")
    print("   - Chrome/Edge: 点击「高级」->「继续前往localhost(不安全)」")
    print("   - Firefox: 点击「高级」->「接受风险并继续」")
    print("   - 按 Ctrl+C 停止服务")
    print("="*70 + "\n")
    
    # 使用Django runserver_plus启动HTTPS服务
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line([
            'manage.py',
            'runserver_plus',
            f'{host}:{port}',
            '--cert-file', cert_file,
            '--key-file', key_file,
        ])
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("[停止] 服务已停止")
        print("="*70 + "\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[错误] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()