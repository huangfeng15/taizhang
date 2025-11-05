"""
PDF导入URL配置
"""
from django.urls import path
from . import views

app_name = 'pdf_import'

urlpatterns = [
    # 步骤1: 上传PDF文件
    path('upload/', views.upload_pdf, name='upload'),
    
    # 步骤2: 提取数据（后台处理）
    path('extract/<str:session_id>/', views.extract_data, name='extract'),
    
    # 步骤3: 预览和编辑数据
    path('preview/<str:session_id>/', views.preview_data, name='preview'),
    
    # 步骤4: 保存成功页面
    path('success/<str:session_id>/', views.save_success, name='success'),
    
    # 可选：草稿管理
    path('drafts/', views.list_drafts, name='drafts'),
    path('drafts/<str:session_id>/resume/', views.resume_draft, name='resume_draft'),
    path('drafts/<str:session_id>/delete/', views.delete_draft, name='delete_draft'),
]