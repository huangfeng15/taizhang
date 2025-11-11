# 台账系统 - HTTPS配置指南

## 📋 概述

本指南介绍如何为台账系统配置HTTPS自签名证书，解决浏览器"不安全连接"警告。

### ⚠️ 重要说明

- **适用环境**：开发测试环境、局域网内部使用
- **证书类型**：自签名证书（浏览器会显示警告，需手动信任）
- **生产环境**：请使用正规CA机构签发的证书（如Let's Encrypt）

---

## 🚀 快速开始

### 方式一：使用批处理文件（推荐）

```batch
# 双击运行即可，会自动检测并生成证书
start_server.bat
```

### 方式二：手动步骤

```bash
# 1. 生成SSL证书
python generate_ssl_cert.py

# 2. 启动HTTPS服务（端口3500）
python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key 0.0.0.0:3500
```

---

## 📝 详细步骤

### 步骤1：安装依赖

```bash
# 激活虚拟环境（如果使用）
.venv\Scripts\activate

# 安装HTTPS相关依赖
pip install -r requirements.txt
```

依赖包括：
- `cryptography` - 证书生成
- `django-extensions` - Django扩展功能
- `werkzeug` - WSGI工具
- `pyOpenSSL` - OpenSSL Python绑定

### 步骤2：生成自签名证书

运行证书生成脚本：

```bash
python generate_ssl_cert.py
```

生成的文件：
- `ssl_certs/server.crt` - SSL证书文件
- `ssl_certs/server.key` - 私钥文件

证书信息：
- **有效期**：365天（1年）
- **支持域名**：localhost, 127.0.0.1
- **加密算法**：RSA 2048位 + SHA256

### 步骤3：启动HTTPS服务

```bash
# 推荐：使用批处理文件
start_server.bat
```

或手动启动：

```bash
python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key 0.0.0.0:3500
```

服务启动后：
- **本机访问**：`https://127.0.0.1:3500/`
- **局域网访问**：`https://<服务器IP>:3500/`（例如：`https://10.168.3.240:3500/`）
- **监听地址**：`0.0.0.0:3500`（允许局域网访问）

---

## 🌐 浏览器访问指南

### Chrome / Edge

1. 访问 `https://127.0.0.1:3500/`
2. 看到"您的连接不是私密连接"警告
3. 点击 **「高级」**
4. 点击 **「继续前往 127.0.0.1（不安全）」**

### Firefox

1. 访问 `https://127.0.0.1:3500/`
2. 看到"警告：潜在的安全风险"
3. 点击 **「高级」**
4. 点击 **「接受风险并继续」**

### Safari (macOS)

1. 访问 `https://127.0.0.1:3500/`
2. 点击 **「显示详细信息」**
3. 点击 **「访问此网站」**
4. 输入系统密码确认

---

## 🔧 配置说明

### Django设置 (config/settings.py)

已添加以下HTTPS配置：

```python
# HTTPS安全配置
SECURE_SSL_REDIRECT = False  # 开发环境：False，生产环境：True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie安全（HTTPS环境下启用）
SESSION_COOKIE_SECURE = False  # HTTPS环境设为 True
CSRF_COOKIE_SECURE = False     # HTTPS环境设为 True

# 静态文件使用相对路径，自动适配HTTP/HTTPS
STATIC_URL = '/static/'
```

### 开发环境 vs 生产环境

| 配置项 | 开发环境 | 生产环境 |
|--------|---------|---------|
| `SECURE_SSL_REDIRECT` | `False` | `True` |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `True` |
| 证书类型 | 自签名 | CA签发 |

---

## 🔒 局域网访问

### 服务器端

1. 确保防火墙允许3500端口
2. 启动服务会自动监听 `0.0.0.0:3500`

```bash
# Windows防火墙规则（管理员权限）
netsh advfirewall firewall add rule name="Django HTTPS Port 3500" dir=in action=allow protocol=TCP localport=3500
```

### 客户端

1. 获取服务器IP地址（如 `10.168.3.240`）
2. 访问 `https://10.168.3.240:3500/`
3. 信任证书（同上述浏览器步骤）

⚠️ **注意**：每台客户端都需要手动信任证书

---

## ✅ 功能验证清单

启动HTTPS后，请验证以下功能正常：

- [ ] 登录功能正常
- [ ] 页面样式加载正常（CSS）
- [ ] JavaScript功能正常
- [ ] 表单提交正常
- [ ] 文件上传下载正常
- [ ] PDF导入功能正常
- [ ] 报表导出功能正常
- [ ] 图片/静态资源加载正常

### 检查静态资源

在浏览器开发者工具（F12）中：

1. **Console标签**：确认无错误
2. **Network标签**：确认静态文件（CSS/JS）状态码为200
3. **Sources标签**：确认静态文件加载完整

---

## 🐛 常见问题

### 问题1：证书生成失败

**错误信息**：
```
ModuleNotFoundError: No module named 'cryptography'
```

**解决方案**：
```bash
pip install cryptography
```

### 问题2：启动失败

**错误信息**：
```
ModuleNotFoundError: No module named 'django_extensions'
```

**解决方案**：
```bash
pip install django-extensions werkzeug pyOpenSSL
```

或直接：
```bash
pip install -r requirements.txt
```

### 问题3：浏览器持续显示不安全

**原因**：自签名证书本身就会被浏览器标记为不安全

**说明**：这是正常现象，点击"继续访问"即可使用

**如需移除警告**：
- 方案1：使用HTTP访问（不推荐）
- 方案2：使用正规CA签发的证书
- 方案3：将自签名证书添加到系统信任列表（高级操作）

### 问题4：静态文件404错误

**检查项**：
1. 确认 `STATIC_URL = '/static/'` 使用相对路径
2. 运行静态文件收集：
   ```bash
   python manage.py collectstatic
   ```

### 问题5：CSRF验证失败

**原因**：Cookie设置问题

**解决方案**：
确保 `config/settings.py` 中：
```python
CSRF_COOKIE_SECURE = False  # 开发环境设为False
SESSION_COOKIE_SECURE = False
```

### 问题6：局域网访问被拒绝

**检查项**：
1. 防火墙是否允许3500端口
2. 服务是否监听 `0.0.0.0`（而非 `127.0.0.1`）
3. 客户端网络是否可达

---

## 🔄 HTTP与HTTPS切换

### 使用HTTPS（推荐）

```bash
# 使用批处理文件启动
start_server.bat
```

访问：`https://127.0.0.1:3500/`

### 使用HTTP（不推荐）

```bash
python manage.py runserver 0.0.0.0:3500
```

访问：`http://127.0.0.1:3500/`

两种模式可自由切换，不影响数据和功能。

---

## 📊 性能影响

### HTTPS开销

- **加密/解密**：增加约5-10ms延迟
- **首次握手**：约50-100ms
- **后续请求**：使用会话复用，影响极小

### 开发环境

对于本地开发，HTTPS性能影响可忽略不计。

---

## 🔐 安全最佳实践

### 开发环境

✅ **可以使用**：
- 自签名证书
- 关闭HSTS
- Cookie Secure设为False

### 生产环境

✅ **必须做到**：
- 使用CA签发的证书（Let's Encrypt等）
- 启用 `SECURE_SSL_REDIRECT = True`
- 启用 `SESSION_COOKIE_SECURE = True`
- 启用 `CSRF_COOKIE_SECURE = True`
- 启用HSTS头
- 定期更新证书

---

## 📚 相关文档

- [Django HTTPS配置官方文档](https://docs.djangoproject.com/en/stable/topics/security/#ssl-https)
- [Let's Encrypt免费证书](https://letsencrypt.org/)
- [系统安全最佳实践](./安全最佳实践.md)

---

## 🆘 技术支持

如遇到问题：

1. 查看控制台错误信息
2. 检查浏览器开发者工具
3. 查看Django日志输出
4. 参考本文档"常见问题"章节

---

## 📅 维护记录

- **2025-01-06**：创建HTTPS配置指南
- 证书有效期：365天，到期需重新生成

---

**文档版本**: v1.0
**最后更新**: 2025-01-06