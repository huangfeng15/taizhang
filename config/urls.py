"""
URL configuration for procurement_system project.
"""
from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from project import views
from project.views_workload import workload_statistics_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # 认证路由
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='login'
    ), name='logout'),
    
    # 前端页面路由
    path('', views.dashboard, name='dashboard'),
    path('projects/', views.project_list, name='project_list'),
    path('project/<str:project_code>/', views.project_detail, name='project_detail'),
    path('procurements/', views.procurement_list, name='procurement_list'),
    path('procurement/<str:procurement_code>/', views.procurement_detail, name='procurement_detail'),
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/enhanced/', views.contract_list_enhanced, name='contract_list_enhanced'),
    path('contract/<str:contract_code>/', views.contract_detail, name='contract_detail'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payment/<str:payment_code>/', views.payment_detail, name='payment_detail'),
    path('database/management/', views.database_management, name='database_management'),
    path('database/restore-no-auth/', views.restore_database_no_auth, name='restore_database_no_auth'),
    
    # 监控与报表路由
    path('monitoring/cockpit/', views.monitoring_cockpit, name='monitoring_cockpit'),
    path('monitoring/archive/', views.archive_monitor, name='archive_monitor'),
    path('monitoring/cycle/', views.cycle_monitor, name='cycle_monitor'),
    path('monitoring/update/', views.update_monitor, name='update_monitor'),
    path('monitoring/completeness/', views.completeness_check, name='completeness_check'),
    path('monitoring/statistics/', views.statistics_view, name='statistics_view'),
    path('monitoring/ranking/', views.ranking_view, name='ranking_view'),
    path('monitoring/workload/', workload_statistics_view, name='workload_statistics'),
    path('monitoring/completeness/field-config/', views.completeness_field_config, name='completeness_field_config'),
    path('api/completeness/field-config/update/', views.update_completeness_field_config, name='update_completeness_field_config'),

    # 齐全性检查快速编辑API
    path('api/procurement/<str:procurement_code>/detail-for-edit/', views.api_procurement_detail_for_edit, name='api_procurement_detail_for_edit'),
    path('api/procurement/<str:procurement_code>/quick-update/', views.api_procurement_quick_update, name='api_procurement_quick_update'),
    path('api/contract/<str:contract_code>/detail-for-edit/', views.api_contract_detail_for_edit, name='api_contract_detail_for_edit'),
    path('api/contract/<str:contract_code>/quick-update/', views.api_contract_quick_update, name='api_contract_quick_update'),

    # 级联选择器数据API
    path('api/projects/', views.api_projects_list, name='api_projects_list'),
    path('api/procurements/', views.api_procurements_list, name='api_procurements_list'),
    path('api/contracts/', views.api_contracts_list, name='api_contracts_list'),

    # 统计数据详情查看API
    path('api/statistics/<str:module>/details/', views.statistics_detail_api, name='statistics_detail_api'),
    path('monitoring/statistics/<str:module>/details/', views.statistics_detail_page, name='statistics_detail_page'),
    path('monitoring/statistics/<str:module>/export/', views.statistics_detail_export, name='statistics_detail_export'),
    
    # 批量操作API
    path('api/contracts/batch-delete/', views.batch_delete_contracts, name='batch_delete_contracts'),
    path('api/payments/batch-delete/', views.batch_delete_payments, name='batch_delete_payments'),
    path('api/procurements/batch-delete/', views.batch_delete_procurements, name='batch_delete_procurements'),
    path('api/projects/batch-delete/', views.batch_delete_projects, name='batch_delete_projects'),
    
    # 数据导入API
    path('api/import/template/', views.download_import_template, name='download_import_template'),

    # PDF智能导入路由
    path('pdf-import/', include('pdf_import.urls')),
    path('api/import/', views.import_data, name='import_data'),
    
    # 供应商管理路由
    path('supplier/', include('supplier_eval.urls')),

    # 数据导出/导入API
    path('api/export/project-data/', views.export_project_data, name='export_project_data'),
    path('api/import/project-data/', views.import_project_data, name='import_project_data'),
    
    # 前端编辑API
    path('projects/<str:project_code>/edit/', views.project_edit, name='project_edit'),
    path('contracts/<str:contract_code>/edit/', views.contract_edit, name='contract_edit'),
    path('procurements/<str:procurement_code>/edit/', views.procurement_edit, name='procurement_edit'),
    path('payments/<str:payment_code>/edit/', views.payment_edit, name='payment_edit'),
    
    # 前端新增API
    path('projects/create/', views.project_create, name='project_create'),
    path('procurements/create/', views.procurement_create, name='procurement_create'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('payments/create/', views.payment_create, name='payment_create'),

    # OpenAPI schema & Swagger 文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='api_docs',
    ),

    # 用户使用手册
    path('user-manual/', views.user_manual, name='user_manual'),
]

# 自定义Admin站点标题（从settings集中配置，避免硬编码重复）
admin.site.site_header = getattr(settings, 'ADMIN_SITE_HEADER', 'Admin')
admin.site.site_title = getattr(settings, 'ADMIN_SITE_TITLE', 'Admin')
admin.site.index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 'Site administration')
