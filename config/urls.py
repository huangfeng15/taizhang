"""
URL configuration for procurement_system project.
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]

# 自定义Admin站点标题
admin.site.site_header = '项目采购与成本管理系统'
admin.site.site_title = '采购管理'
admin.site.index_title = '欢迎使用项目采购与成本管理系统'