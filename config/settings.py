"""
Django settings for procurement_system project.
"""

import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

# 允许局域网访问
default_allowed_hosts = ['127.0.0.1', 'localhost', '0.0.0.0', '*']
env_allowed_hosts = [
    host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if host.strip()
]
ALLOWED_HOSTS = env_allowed_hosts or default_allowed_hosts

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # HTTPS支持（开发测试用）
    'django_extensions',
    
    # 业务应用
    'project.apps.ProjectConfig',
    'procurement.apps.ProcurementConfig',
    'contract.apps.ContractConfig',
    'payment.apps.PaymentConfig',
    'settlement.apps.SettlementConfig',
    'pdf_import.apps.PdfImportConfig',  # PDF智能导入
    'supplier_eval.apps.SupplierEvalConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'project.middleware.LoginRequiredMiddleware',  # 全局登录验证中间件
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'project' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'project.context_processors.global_filter_options',
            ],
            'debug': DEBUG,  # 启用模板调试
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # 防止数据库锁定
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# ============================================================================
# 会话（Session）配置
# ============================================================================
# 会话有效期：12小时（单位：秒）
SESSION_COOKIE_AGE = 12 * 60 * 60  # 12小时 = 43200秒

# 关闭浏览器后会话是否失效（False表示会话保持到SESSION_COOKIE_AGE到期）
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# 每次请求都更新会话的过期时间（保持活跃状态）
SESSION_SAVE_EVERY_REQUEST = True

# 会话Cookie的名称
SESSION_COOKIE_NAME = 'procurement_sessionid'

# 会话引擎（默认使用数据库存储）
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Static files (CSS, JavaScript, Images)
# 使用相对路径，自动适配HTTP/HTTPS
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload settings
DATA_UPLOAD_MAX_NUMBER_FILES = 100  # 允许上传的最大文件数量
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB - 单个文件在内存中的最大大小
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB - 总请求大小限制

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# 登录认证配置
# ============================================================================
# 登录URL
LOGIN_URL = '/accounts/login/'

# 登录成功后的重定向URL
LOGIN_REDIRECT_URL = '/'

# 登出后的重定向URL
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Admin site customization
ADMIN_SITE_HEADER = '项目采购与成本管理系统'
ADMIN_SITE_TITLE = '采购管理'
ADMIN_INDEX_TITLE = '欢迎使用项目采购与成本管理系统'


# PDF智能导入配置
PDF_IMPORT_CONFIG = {
    'UPLOAD_DIR': MEDIA_ROOT / 'pdf_uploads',
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_EXTENSIONS': ['.pdf'],
    'CONFIG_DIR': BASE_DIR / 'pdf_import' / 'config',
    'ENABLE_ASYNC': False,  # 是否启用异步处理（需要Celery）
    'SESSION_EXPIRY_HOURS': 24,  # 会话默认过期时间（小时）
    'DRAFT_EXPIRY_HOURS': 72,  # 草稿过期时间（小时）
}

# ============================================================================
# HTTPS安全配置（开发测试环境）
# ============================================================================
# 注意：以下配置适用于使用自签名证书的开发环境
# 生产环境需要使用正规CA签发的证书，并启用更严格的安全设置

# HTTPS重定向（开发环境关闭，生产环境开启）
SECURE_SSL_REDIRECT = False  # 生产环境设为 True

# 代理HTTPS头处理（如果使用Nginx等反向代理）
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie安全设置（HTTPS环境下启用）
SESSION_COOKIE_SECURE = False  # HTTPS环境设为 True
CSRF_COOKIE_SECURE = False     # HTTPS环境设为 True

# HSTS设置（生产环境启用）
# SECURE_HSTS_SECONDS = 31536000  # 1年
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# 确保静态文件路径使用相对路径，自动适配协议
# Django会根据请求协议自动生成正确的URL
