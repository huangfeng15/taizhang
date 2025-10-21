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
    
    # 批量操作API
    path('api/contracts/batch-delete/', views.batch_delete_contracts, name='batch_delete_contracts'),
    path('api/payments/batch-delete/', views.batch_delete_payments, name='batch_delete_payments'),
    path('api/procurements/batch-delete/', views.batch_delete_procurements, name='batch_delete_procurements'),
    path('api/projects/batch-delete/', views.batch_delete_projects, name='batch_delete_projects'),
    
    # 数据导入API
    path('api/import/', views.import_data, name='import_data'),
]

# 自定义Admin站点标题
admin.site.site_header = '项目采购与成本管理系统'
admin.site.site_title = '采购管理'
admin.site.index_title = '欢迎使用项目采购与成本管理系统'