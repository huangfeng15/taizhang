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

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
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
