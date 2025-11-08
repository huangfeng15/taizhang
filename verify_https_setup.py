"""
HTTPS配置验证脚本
检查所有HTTPS相关配置是否正确
"""
import os
import sys
from pathlib import Path

def check_certificates():
    """检查证书文件"""
    print("\n[1/5] 检查SSL证书...")
    cert_dir = Path("ssl_certs")
    cert_file = cert_dir / "server.crt"
    key_file = cert_dir / "server.key"
    
    if cert_file.exists() and key_file.exists():
        print(f"  [OK] 证书文件存在: {cert_file}")
        print(f"  [OK] 私钥文件存在: {key_file}")
        return True
    else:
        print(f"  [FAIL] 证书文件缺失")
        return False

def check_dependencies():
    """检查Python依赖"""
    print("\n[2/5] 检查Python依赖...")
    deps = ['cryptography', 'django_extensions', 'werkzeug', 'OpenSSL']
    all_ok = True
    
    for dep in deps:
        try:
            __import__(dep)
            print(f"  [OK] {dep}")
        except ImportError:
            print(f"  [FAIL] {dep} 未安装")
            all_ok = False
    
    return all_ok

def check_django_settings():
    """检查Django配置"""
    print("\n[3/5] 检查Django配置...")
    
    # 设置Django环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        import django
        django.setup()
        from django.conf import settings
        
        # 检查INSTALLED_APPS
        if 'django_extensions' in settings.INSTALLED_APPS:
            print("  [OK] django_extensions 已添加到INSTALLED_APPS")
        else:
            print("  [WARN] django_extensions 未添加到INSTALLED_APPS")
        
        # 检查STATIC_URL
        if settings.STATIC_URL == '/static/':
            print(f"  [OK] STATIC_URL配置正确: {settings.STATIC_URL}")
        else:
            print(f"  [INFO] STATIC_URL: {settings.STATIC_URL}")
        
        # 检查HTTPS配置
        print(f"  [INFO] SECURE_SSL_REDIRECT: {settings.SECURE_SSL_REDIRECT}")
        print(f"  [INFO] SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
        print(f"  [INFO] CSRF_COOKIE_SECURE: {settings.CSRF_COOKIE_SECURE}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Django配置检查失败: {e}")
        return False

def check_startup_files():
    """检查启动文件"""
    print("\n[4/5] 检查启动文件...")
    
    files = {
        'generate_ssl_cert.py': '证书生成脚本',
        'start_https.py': 'HTTPS启动脚本',
        'start_https.bat': 'Windows批处理启动文件'
    }
    
    all_ok = True
    for filename, desc in files.items():
        if Path(filename).exists():
            print(f"  [OK] {desc}: {filename}")
        else:
            print(f"  [FAIL] {desc}缺失: {filename}")
            all_ok = False
    
    return all_ok

def check_static_files():
    """检查静态文件配置"""
    print("\n[5/5] 检查静态文件...")
    
    static_dirs = [
        Path('project/static/css'),
        Path('project/static/js'),
    ]
    
    for static_dir in static_dirs:
        if static_dir.exists():
            file_count = len(list(static_dir.glob('*')))
            print(f"  [OK] {static_dir} ({file_count} 个文件)")
        else:
            print(f"  [WARN] {static_dir} 不存在")
    
    return True

def main():
    """主验证流程"""
    print("="*70)
    print("HTTPS配置验证工具")
    print("="*70)
    
    results = []
    
    # 执行所有检查
    results.append(("证书文件", check_certificates()))
    results.append(("Python依赖", check_dependencies()))
    results.append(("Django配置", check_django_settings()))
    results.append(("启动文件", check_startup_files()))
    results.append(("静态文件", check_static_files()))
    
    # 汇总结果
    print("\n" + "="*70)
    print("验证结果汇总")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "[通过]" if passed else "[失败]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n[成功] 所有检查通过！可以启动HTTPS服务")
        print("\n启动命令:")
        print("  Windows: start_https.bat")
        print("  或手动: python start_https.py")
        print("\n访问地址: https://localhost:8000")
    else:
        print("\n[警告] 部分检查未通过，请修复后再启动")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[取消] 验证已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n[错误] 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)