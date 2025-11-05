"""
URL configuration for procurement_system project.
"""
from django.urls import path, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from project import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 认证路由
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='admin/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
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
    
    # 监控与报表路由
    path('monitoring/cockpit/', views.monitoring_cockpit, name='monitoring_cockpit'),
    path('monitoring/archive/', views.archive_monitor, name='archive_monitor'),
    path('monitoring/update/', views.update_monitor, name='update_monitor'),
    path('monitoring/completeness/', views.completeness_check, name='completeness_check'),
    path('monitoring/statistics/', views.statistics_view, name='statistics_view'),
    path('monitoring/ranking/', views.ranking_view, name='ranking_view'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('reports/preview/', views.report_preview, name='report_preview'),
    path('reports/export/', views.report_export, name='report_export'),
    path('reports/professional/', views.generate_professional_report, name='generate_professional_report'),
    path('reports/comprehensive/', views.generate_comprehensive_report, name='generate_comprehensive_report'),
    
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
    
    # 数据导出API
    path('api/export/project-data/', views.export_project_data, name='export_project_data'),
    
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
]

# 自定义Admin站点标题
admin.site.site_header = '项目采购与成本管理系统'
admin.site.site_title = '采购管理'
admin.site.index_title = '欢迎使用项目采购与成本管理系统'
