"""
生成自签名SSL证书
无需OpenSSL，使用Python直接生成
"""
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import ipaddress

# 生成私钥
print("正在生成私钥...")
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096,
    backend=default_backend()
)

# 证书主体信息
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Guangdong"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"Shenzhen"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Company"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"10.168.3.240"),
])

# 生成证书
print("正在生成证书...")
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
    datetime.utcnow() + timedelta(days=3650)  # 10年有效期
).add_extension(
    x509.SubjectAlternativeName([
        x509.IPAddress(ipaddress.IPv4Address(u"10.168.3.240")),
        x509.DNSName(u"10.168.3.240"),
        x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
        x509.DNSName(u"localhost"),
    ]),
    critical=False,
).sign(private_key, hashes.SHA256(), default_backend())

# 保存私钥
print("正在保存私钥到 ssl/key.pem...")
with open("ssl/key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# 保存证书
print("正在保存证书到 ssl/cert.pem...")
with open("ssl/cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("\n✅ 证书生成成功！")
print(f"证书位置: ssl/cert.pem")
print(f"私钥位置: ssl/key.pem")
print(f"有效期: 10年 (到 {(datetime.utcnow() + timedelta(days=3650)).strftime('%Y-%m-%d')})")
print("\n下一步:")
print("1. 安装必要的包: pip install django-extensions werkzeug pyopenssl")
print("2. 启动HTTPS服务器: python manage.py runserver_plus --cert-file ssl/cert.pem --key-file ssl/key.pem 0.0.0.0:3500")