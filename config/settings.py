"""
Django settings for procurement_system project.
"""

import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-key-for-development-only-change-in-production'
    else:
        raise ValueError("生产环境必须通过DJANGO_SECRET_KEY环境变量设置SECRET_KEY")

# SECRET_KEY回退机制（用于密钥轮换，Django 5.2新特性）
SECRET_KEY_FALLBACKS = [
    os.environ.get('DJANGO_SECRET_KEY_OLD'),
] if os.environ.get('DJANGO_SECRET_KEY_OLD') else []

# 允许访问的主机（更安全的默认值；生产请通过环境变量显式配置）
default_allowed_hosts = ['127.0.0.1', 'localhost', '10.168.3.240']
env_allowed_hosts = [
    host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if host.strip()
]
ALLOWED_HOSTS = env_allowed_hosts if env_allowed_hosts else default_allowed_hosts

# ============================================================================
# 安全头部配置（Django最佳实践）
# ============================================================================
# 防止MIME类型嗅探
SECURE_CONTENT_TYPE_NOSNIFF = True

# 跨域opener策略
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# X-Frame-Options（防止点击劫持）
X_FRAME_OPTIONS = 'DENY'

# Referrer策略
SECURE_REFERRER_POLICY = 'same-origin'

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

    # Django REST Framework 与 OpenAPI 文档
    'rest_framework',
    'drf_spectacular',

    # 业务应用
    'project.apps.ProjectConfig',
    'procurement.apps.ProcurementConfig',
    'contract.apps.ContractConfig',
    'payment.apps.PaymentConfig',
    'settlement.apps.SettlementConfig',
    'pdf_import.apps.PdfImportConfig',  # PDF智能导入
    'supplier_eval.apps.SupplierEvalConfig',

    # 异步任务队列（大报表等后台处理；需搭配Redis和 django-rq）
    'django_rq',
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
    # 性能监控中间件（开发+生产）
    'project.middleware.performance.PerformanceMonitoringMiddleware',
    # 查询计数中间件（仅开发环境）
    'project.middleware.query_counter.QueryCountDebugMiddleware',
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

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': '项目采购与成本管理系统 API',
    'DESCRIPTION': '基于Django的项目采购与成本管理系统接口文档',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ============================================================================
# 数据库配置（优化连接池和性能）
# ============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE': 600,  # 连接池：保持连接10分钟（提升性能）
        'CONN_HEALTH_CHECKS': True,  # Django 5.2新特性：启用连接健康检查
        'OPTIONS': {
            'timeout': 20,  # 防止数据库锁定
            'init_command': "PRAGMA foreign_keys=ON",  # 确保外键约束
        },
        # 事务原子性（按需启用，避免全局开启影响性能）
        'ATOMIC_REQUESTS': False,
    }
}

# 为SQLite启用外键约束
from django.db.backends.signals import connection_created
def enable_sqlite_foreign_keys(sender, connection, **kwargs):
    """启用SQLite外键约束"""
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')

connection_created.connect(enable_sqlite_foreign_keys)

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
# 会话（Session）配置（增强安全性）
# ============================================================================
# 会话有效期：12小时（单位：秒）
SESSION_COOKIE_AGE = 12 * 60 * 60  # 12小时 = 43200秒

# 关闭浏览器后会话是否失效（False表示会话保持到SESSION_COOKIE_AGE到期）
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# 每次请求都更新会话的过期时间（保持活跃状态）
# 注意：性能优化 - 避免每次请求都写数据库
SESSION_SAVE_EVERY_REQUEST = False

# 会话Cookie的名称
SESSION_COOKIE_NAME = 'procurement_sessionid'

# 会话引擎（默认使用数据库存储）
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Session安全设置
SESSION_COOKIE_HTTPONLY = True  # 防止JavaScript访问Cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF保护（Lax允许顶级导航）
SESSION_COOKIE_SECURE = False if DEBUG else True  # 生产环境强制HTTPS

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
# 缓存配置（多层缓存架构）
# ============================================================================
CACHES = {
    # 主缓存：本地内存缓存（开发环境）
    # 生产环境建议使用Redis: pip install django-redis
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'default-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
        'TIMEOUT': 300,  # 默认5分钟
        'KEY_PREFIX': 'taizhang',
        'VERSION': 1,
    },
    # 文件缓存（持久化备选）
    'file': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'cache',
        'TIMEOUT': 600,
        'OPTIONS': {
            'MAX_ENTRIES': 5000,
        }
    },
    # Dummy缓存（测试环境）
    'dummy': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# RQ 队列配置（示例配置，需在生产环境提供可用的 Redis 服务）
RQ_QUEUES = {
    'default': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', '6379')),
        'DB': int(os.environ.get('REDIS_DB', '0')),
        'PASSWORD': os.environ.get('REDIS_PASSWORD', ''),
        'DEFAULT_TIMEOUT': 360,
    },
    'high': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', '6379')),
        'DB': int(os.environ.get('REDIS_DB', '0')),
        'PASSWORD': os.environ.get('REDIS_PASSWORD', ''),
        'DEFAULT_TIMEOUT': 500,
    },
    'low': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', '6379')),
        'DB': int(os.environ.get('REDIS_DB', '0')),
        'PASSWORD': os.environ.get('REDIS_PASSWORD', ''),
        'DEFAULT_TIMEOUT': 1000,
    },
}

# Redis配置示例（生产环境使用）
# 需要安装: pip install django-redis redis
"""
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'taizhang',
        'TIMEOUT': 300,
        'VERSION': 1,
    }
}
"""

# 缓存中间件配置（全站缓存 - 按需启用）
# CACHE_MIDDLEWARE_ALIAS = 'default'
# CACHE_MIDDLEWARE_SECONDS = 600
# CACHE_MIDDLEWARE_KEY_PREFIX = 'site'

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

# 代理HTTPS头处理（如果使用Nginx等反向代理或HTTPS请求）
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 当使用自签名证书的HTTPS开发服务器时，需要配置这些设置
# 这样Django能正确处理HTTPS请求，避免CSRF验证失败
SECURE_SSL_HOST = '10.168.3.240:3500'  # 开发服务器地址

# CSRF安全增强配置
# 注意：前端大量使用 fetch + X-CSRFToken + document.cookie 读取 CSRF Token
# 如果将 CSRF Cookie 设置为 HttpOnly=True，JavaScript 无法读取，所有这类请求都会 403
# 因此这里必须保持为 False，避免与现有前端模式冲突。
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Strict'  # 严格的CSRF保护
CSRF_COOKIE_SECURE = False if DEBUG else True  # 生产环境强制HTTPS
CSRF_COOKIE_AGE = 31449600  # 1年（默认值）

# 信任代理设置（重要：允许Django信任代理头，正确处理HTTPS请求）
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# CSRF信任域名设置（允许指定域名通过CSRF验证）
# 信任本地开发环境的IP地址
CSRF_TRUSTED_ORIGINS = [
    'http://10.168.3.240:3500',
    'https://10.168.3.240:3500',
    'http://localhost:3500',
    'https://localhost:3500',
    'http://127.0.0.1:3500',
    'https://127.0.0.1:3500',
]

# 为支持HTTPS请求处理添加额外配置
# 允许在开发环境中处理HTTPS请求
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# HSTS设置（生产环境启用，开发环境注释掉以避免自签名证书问题）
# SECURE_HSTS_SECONDS = 31536000  # 1年
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# 确保静态文件路径使用相对路径，自动适配协议
# Django会根据请求协议自动生成正确的URL
