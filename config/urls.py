"""
URL configuration for procurement_system project.
"""
from django.contrib import admin
from django.urls import path
from project import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
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
    
    # 批量操作API
    path('api/contracts/batch-delete/', views.batch_delete_contracts, name='batch_delete_contracts'),
    path('api/payments/batch-delete/', views.batch_delete_payments, name='batch_delete_payments'),
    path('api/procurements/batch-delete/', views.batch_delete_procurements, name='batch_delete_procurements'),
    path('api/projects/batch-delete/', views.batch_delete_projects, name='batch_delete_projects'),
    
    # 数据导入API
    path('api/import/template/', views.download_import_template, name='download_import_template'),
    path('api/import/', views.import_data, name='import_data'),
    
    # 数据导出API
    path('api/export/project-data/', views.export_project_data, name='export_project_data'),
]

# 自定义Admin站点标题
admin.site.site_header = '项目采购与成本管理系统'
admin.site.site_title = '采购管理'
admin.site.index_title = '欢迎使用项目采购与成本管理系统'
