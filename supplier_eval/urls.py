"""
供应商管理模块 - URL路由配置
"""
from django.urls import path
from supplier_eval import views

app_name = 'supplier_eval'

urlpatterns = [
    # 供应商履约评价
    path('evaluations/', views.supplier_evaluation_list, name='supplier_evaluation_list'),
    path('evaluations/detail/<str:supplier_name>/', views.supplier_evaluation_detail, name='supplier_evaluation_detail'),
    path('evaluations/create/', views.supplier_evaluation_create, name='supplier_evaluation_create'),
    path('evaluations/<str:evaluation_code>/edit/', views.supplier_evaluation_edit, name='supplier_evaluation_edit'),
    
    # 供应商承接项目查询
    path('contracts/', views.supplier_contract_list, name='supplier_contract_list'),
    
    # 供应商约谈记录
    path('interviews/', views.supplier_interview_list, name='supplier_interview_list'),
    path('interviews/<int:interview_id>/', views.supplier_interview_detail, name='supplier_interview_detail'),
    path('interviews/create/', views.supplier_interview_create, name='supplier_interview_create'),
    path('interviews/<int:interview_id>/edit/', views.supplier_interview_edit, name='supplier_interview_edit'),
]