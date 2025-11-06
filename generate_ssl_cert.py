"""
SSL自签名证书生成工具
用途：为本地Django项目生成HTTPS证书
安全说明：仅用于开发测试环境，生产环境请使用正规CA签发的证书
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

def install_cryptography():
    """安装cryptography库"""
    print("[安装] 正在安装cryptography库...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
        print("[成功] cryptography安装成功")
        return True
    except Exception as e:
        print(f"[错误] 安装失败: {e}")
        return False

def generate_self_signed_cert():
    """生成自签名证书"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        import ipaddress
    except ImportError:
        print("[错误] 缺少cryptography库")
        if install_cryptography():
            # 重新导入
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            import ipaddress
        else:
            sys.exit(1)
    
    # 创建证书存放目录
    cert_dir = Path("ssl_certs")
    cert_dir.mkdir(exist_ok=True)
    
    print("\n" + "="*70)
    print("台账系统 - SSL自签名证书生成工具")
    print("="*70)
    print("正在生成证书...")
    
    # 1. 生成私钥（2048位RSA）
    print("  [1/5] 生成RSA私钥...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # 2. 配置证书主题信息
    print("  [2/5] 配置证书信息...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Guangdong"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Shenzhen"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TaiZhang System"),
        x509.NameAttribute(NameOID.COMMON_NAME, "10.168.3.240"),
    ])
    
    # 3. 创建证书（有效期1年）
    print("  [3/5] 创建证书...")
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)  # 有效期1年
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address("10.168.3.240")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # 4. 保存私钥
    key_file = cert_dir / "server.key"
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # 5. 保存证书
    cert_file = cert_dir / "server.crt"
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # 显示结果
    print("\n" + "="*70)
    print("[成功] 证书生成成功！")
    print("="*70)
    print(f"证书文件: {cert_file.absolute()}")
    print(f"私钥文件: {key_file.absolute()}")
    print(f"有效期: 365天 (至 {(datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')})")
    print(f"支持域名/IP: localhost, 127.0.0.1, 10.168.3.240")
    print("\n" + "="*70)
    print("下一步操作：")
    print("="*70)
    print("[步骤1] 运行启动命令:")
    print("        Windows: start_https.bat")
    print("        或手动: python start_https.py")
    print("\n[步骤2] 访问系统:")
    print("        本地访问: https://localhost:3500")
    print("        局域网访问: https://10.168.3.240:3500")
    print("\n[步骤3] 浏览器会提示不安全:")
    print("        - Chrome/Edge: 点击「高级」->「继续前往localhost(不安全)」")
    print("        - Firefox: 点击「高级」->「接受风险并继续」")
    print("\n[提示] 这是开发测试用的自签名证书，浏览器会显示不安全警告是正常的")
    print("       局域网内其他设备访问时也需要手动信任证书")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        generate_self_signed_cert()
    except KeyboardInterrupt:
        print("\n\n[取消] 操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n[错误] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)