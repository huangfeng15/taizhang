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
    path('projects/<str:project_code>/', views.project_detail, name='project_detail'),
    path('procurements/', views.procurement_list, name='procurement_list'),
    path('procurements/<str:procurement_code>/', views.procurement_detail, name='procurement_detail'),
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/<str:contract_code>/', views.contract_detail, name='contract_detail'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<str:payment_code>/', views.payment_detail, name='payment_detail'),
]

# 自定义Admin站点标题
admin.site.site_header = '项目采购与成本管理系统'
admin.site.site_title = '采购管理'
admin.site.index_title = '欢迎使用项目采购与成本管理系统'