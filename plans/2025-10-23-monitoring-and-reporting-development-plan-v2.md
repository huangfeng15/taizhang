# 监控指标与报表功能扩展计划

## 文档信息

**文档版本：** v2.0 (修订版)  
**创建日期：** 2025-10-23  
**文档类型：** 功能扩展开发计划  
**目标读者：** 开发团队  
**计划周期：** 6-8周  

---

## ⚠️ 重要说明

**本计划是在现有"项目采购与成本管理系统"基础上增加监控指标和报表功能，而不是创建新的独立系统。**

### 现有系统概况

- ✅ 已有完整的Django项目结构 ([`config/`](config/))
- ✅ 已有项目、采购、合同、付款、结算等业务模型
- ✅ 已有基础的列表和详情页面
- ✅ 已有数据导入导出功能
- ✅ 已有SQLite数据库和完整数据

### 本次开发范围

在**现有系统基础上**增加:
- 📊 监控仪表盘（归档监控、更新监控、齐全性检查）
- 📈 业务数据统计（采购、合同、付款、结算统计）
- 🏆 业务排名展示
- 📄 报表生成与导出（周报、月报、季报、年报）

### 不包含的内容

- ❌ **不创建新的Django项目**
- ❌ **不重建数据库结构**
- ❌ **不修改现有业务模型**（只读取数据进行分析）
- ❌ **不替换现有页面**（新增独立的监控和报表页面）

---

## 1. 架构设计方案

### 1.1 技术栈（完全基于现有）

| 技术组件 | 现有版本 | 本次使用方式 |
|---------|---------|-------------|
| **后端框架** | Django 5.2.7 | ✅ 直接使用现有配置 |
| **数据库** | SQLite | ✅ 使用现有数据库，不新建表（可选缓存表） |
| **模板引擎** | Django Templates | ✅ 继续使用 |
| **前端** | HTML + CSS + JS | ✅ 保持轻量级 |
| **图表库** | 无 | 📦 新增 Chart.js (CDN) |
| **Excel** | openpyxl 3.1.5 | ✅ 已有，直接使用 |
| **数据分析** | pandas 2.3.3 | ✅ 已有，用于统计 |

### 1.2 实现方案选择

#### 方案A: 轻量级扩展（推荐MVP）

**在现有 [`project/`](project/) 应用中直接扩展**

```
project/                          # 现有应用，直接扩展
├── views.py                      # 📝 扩展：增加监控和报表视图
│   ├── dashboard()              # ✅ 现有
│   ├── project_list()           # ✅ 现有  
│   ├── contract_list()          # ✅ 现有
│   ├── monitoring_dashboard()   # 🆕 新增
│   ├── archive_monitor()        # 🆕 新增
│   ├── update_monitor()         # 🆕 新增
│   ├── statistics_view()        # 🆕 新增
│   ├── completeness_check()     # 🆕 新增
│   ├── ranking_view()           # 🆕 新增
│   └── generate_report()        # 🆕 新增
│
├── services/                     # 🆕 新建目录
│   ├── __init__.py
│   ├── archive_monitor.py       # 归档监控业务逻辑
│   ├── update_monitor.py        # 更新监控业务逻辑
│   ├── statistics.py            # 统计计算逻辑
│   ├── completeness.py          # 齐全性检查逻辑
│   ├── ranking.py               # 业务排名逻辑
│   └── report_generator.py      # 报表生成逻辑
│
├── utils/                        # 🆕 新建目录
│   ├── __init__.py
│   ├── date_helpers.py          # 日期计算工具
│   ├── chart_data.py            # 图表数据转换
│   └── excel_export.py          # Excel导出封装
│
├── templates/                    # ✅ 现有目录，扩展内容
│   ├── base.html                # 📝 修改：增加监控菜单
│   ├── dashboard.html           # ✅ 现有首页
│   ├── monitoring/              # 🆕 新建子目录
│   │   ├── dashboard.html       # 监控总览
│   │   ├── archive.html         # 归档监控
│   │   ├── update.html          # 更新监控
│   │   ├── statistics.html      # 统计分析
│   │   ├── completeness.html    # 齐全性检查
│   │   └── ranking.html         # 业务排名
│   └── reports/                 # 🆕 新建子目录
│       ├── form.html            # 报表生成表单
│       └── preview.html         # 报表预览
│
├── static/                       # 📝 扩展静态资源
│   ├── css/
│   │   └── monitoring.css       # 🆕 监控页面样式
│   └── js/
│       ├── charts.js            # 🆕 图表初始化
│       └── monitoring.js        # 🆕 监控交互
│
└── filter_config.py             # ✅ 现有，可能需要扩展

config/
└── urls.py                       # 📝 修改：增加路由
    ├── /monitoring/              # 🆕 监控路由组
    └── /reports/                 # 🆕 报表路由组
```

**优势:**
- ✅ 最小改动，快速上线
- ✅ 无需注册新应用
- ✅ 与现有代码风格一致
- ✅ 便于维护和理解

#### 方案B: 独立应用（可选）

**如果监控功能持续扩展，可创建独立 `monitoring` 应用**

```
monitoring/                       # 🆕 独立应用（可选）
├── __init__.py
├── apps.py
├── views.py                     # 监控视图
├── urls.py                      # 监控路由
└── services/                    # 业务逻辑（同方案A）

config/
├── settings.py                   # 📝 注册新应用
└── urls.py                       # 📝 包含新应用路由

project/templates/
└── monitoring/                   # 🆕 模板（同方案A）
```

**建议:** 
- **第一阶段**: 使用方案A (轻量级扩展)
- **第二阶段**: 如需要可重构为方案B

---

## 2. 开发阶段规划

### 阶段一: 基础架构与归档监控 (Week 1-2)

#### 目标
- 搭建服务层架构
- 实现归档监控功能
- 创建监控仪表盘

#### 任务清单

**1. 创建目录结构**
- [ ] 创建 [`project/services/`](project/services/) 目录
- [ ] 创建 [`project/utils/`](project/utils/) 目录  
- [ ] 创建 [`project/templates/monitoring/`](project/templates/monitoring/) 目录
- [ ] 创建 [`project/static/css/monitoring.css`](project/static/css/monitoring.css)
- [ ] 创建 [`project/static/js/charts.js`](project/static/js/charts.js)

**2. 实现归档监控服务**

文件: [`project/services/archive_monitor.py`](project/services/archive_monitor.py)

```python
# 归档监控服务
def get_archive_overview():
    """获取归档总览数据"""
    # 统计采购、合同、结算的归档情况
    pass

def get_overdue_list(module=None):
    """获取逾期项目列表"""
    # 计算逾期天数，分级预警
    pass
```

**3. 创建监控视图**

文件: [`project/views.py`](project/views.py) (扩展)

```python
@login_required
def monitoring_dashboard(request):
    """监控仪表盘"""
    from project.services.archive_monitor import get_archive_overview
    context = {
        'archive_data': get_archive_overview(),
    }
    return render(request, 'monitoring/dashboard.html', context)

@login_required  
def archive_monitor(request):
    """归档监控详情"""
    from project.services.archive_monitor import get_overdue_list
    context = {
        'overdue_list': get_overdue_list(),
    }
    return render(request, 'monitoring/archive.html', context)
```

**4. 创建监控模板**

文件: [`project/templates/monitoring/dashboard.html`](project/templates/monitoring/dashboard.html)

- [ ] 实现监控仪表盘布局
- [ ] 集成Chart.js显示归档率环形图
- [ ] 显示预警项目列表

**5. 配置路由**

文件: [`config/urls.py`](config/urls.py) (扩展)

```python
urlpatterns = [
    # ... 现有路由 ...
    path('monitoring/', monitoring_dashboard, name='monitoring_dashboard'),
    path('monitoring/archive/', archive_monitor, name='archive_monitor'),
]
```

**6. 更新导航菜单**

文件: [`project/templates/base.html`](project/templates/base.html) (修改)

- [ ] 在导航栏增加"监控中心"菜单项
- [ ] 增加子菜单：归档监控、更新监控、统计分析等

---

### 阶段二: 数据更新监控与齐全性检查 (Week 3-4)

#### 目标
- 实现数据更新时效性监控
- 实现数据齐全性检查
- 完善监控功能

#### 任务清单

**1. 实现更新监控服务**

文件: [`project/services/update_monitor.py`](project/services/update_monitor.py)

```python
def get_project_update_status():
    """获取各项目各模块最近更新状态"""
    # 检查 created_at 和 updated_at 字段
    # 计算距今天数，超过40天标红
    pass
```

**2. 实现齐全性检查服务**

文件: [`project/services/completeness.py`](project/services/completeness.py)

```python
def check_contract_completeness():
    """检查合同数据齐全性"""
    # 检查补充协议是否关联主合同
    # 检查采购合同是否关联采购项目
    pass
```

**3. 创建对应视图和模板**

- [ ] 实现 [`update_monitor()`](project/views.py) 视图
- [ ] 实现 [`completeness_check()`](project/views.py) 视图
- [ ] 创建 [`monitoring/update.html`](project/templates/monitoring/update.html)
- [ ] 创建 [`monitoring/completeness.html`](project/templates/monitoring/completeness.html)

---

### 阶段三: 业务数据统计 (Week 5-6)

#### 目标
- 实现采购、合同、付款、结算统计
- 支持年度数据对比
- 图表可视化展示

#### 任务清单

**1. 实现统计服务**

文件: [`project/services/statistics.py`](project/services/statistics.py)

```python
def get_procurement_statistics(year=None):
    """采购统计"""
    # 累计预算、中标金额
    # 采购方式占比
    # 采购周期分析
    pass

def get_contract_statistics(year=None):
    """合同统计"""
    pass

def get_payment_statistics(year=None):
    """付款统计"""
    # 累计付款、预计剩余支付
    pass

def get_settlement_statistics():
    """结算统计"""
    pass
```

**2. 创建统计视图和模板**

- [ ] 实现 [`statistics_view()`](project/views.py) 视图
- [ ] 创建 [`monitoring/statistics.html`](project/templates/monitoring/statistics.html)
- [ ] 使用Chart.js绘制饼图、柱状图、折线图

---

### 阶段四: 业务排名 (Week 7)

#### 目标
- 实现项目和个人业务排名
- 支持多维度排名展示

#### 任务清单

**1. 实现排名服务**

文件: [`project/services/ranking.py`](project/services/ranking.py)

```python
def get_procurement_ranking(rank_type='project'):
    """采购业务排名"""
    # 准时完成率排名
    # 采购周期效率排名
    # 完成数量排名
    pass

def get_archive_ranking(rank_type='project'):
    """归档业务排名"""
    pass
```

**2. 创建排名视图和模板**

- [ ] 实现 [`ranking_view()`](project/views.py) 视图
- [ ] 创建 [`monitoring/ranking.html`](project/templates/monitoring/ranking.html)
- [ ] 实现排行榜UI，使用🥇🥈🥉图标

---

### 阶段五: 报表生成与导出 (Week 8)

#### 目标
- 实现周报、月报、季报、年报生成
- 支持Excel和PDF导出

#### 任务清单

**1. 实现报表生成服务**

文件: [`project/services/report_generator.py`](project/services/report_generator.py)

```python
def generate_monthly_report(year, month):
    """生成月报数据"""
    # 汇总采购、合同、付款、结算数据
    # 计算各类统计指标
    pass

def export_to_excel(report_data):
    """导出Excel"""
    # 使用现有的 openpyxl
    pass
```

**2. 创建报表视图和模板**

- [ ] 实现 [`generate_report()`](project/views.py) 视图
- [ ] 创建 [`reports/form.html`](project/templates/reports/form.html)
- [ ] 创建 [`reports/preview.html`](project/templates/reports/preview.html)

---

## 3. 数据来源说明

### 3.1 现有模型依赖

所有监控和统计功能都基于现有模型:

| 功能模块 | 依赖的现有模型 | 主要字段 |
|---------|--------------|---------|
| 归档监控 | [`Procurement`](procurement/models.py), [`Contract`](contract/models.py) | `archive_date`, `platform_publicity_date`, `signing_date` |
| 更新监控 | 所有模型 | `created_at`, `updated_at` |
| 采购统计 | [`Procurement`](procurement/models.py) | `budget_amount`, `winning_amount`, `procurement_method` |
| 合同统计 | [`Contract`](contract/models.py) | `contract_amount`, `contract_type`, `contract_source` |
| 付款统计 | [`Payment`](payment/models.py) | `payment_amount`, `payment_date` |
| 结算统计 | [`Settlement`](settlement/models.py) | `final_amount`, `completion_date` |
| 业务排名 | 所有模型 | 各模型的时间和金额字段 |

### 3.2 无需新建数据库表

**重要:** 所有统计和监控功能都是实时计算,**不需要新建数据库表**。

可选优化: 如果性能需要,可以后期增加缓存表。

---

## 4. 前端设计指导

### 4.1 页面布局风格

保持与现有页面风格一致:
- 使用现有的 [`base.html`](project/templates/base.html) 布局
- 复用现有的CSS样式
- 保持简洁的表格和卡片布局

### 4.2 图表库集成

使用Chart.js (CDN引入):

```html
<!-- 在 base.html 中引入 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

### 4.3 响应式设计

- 确保在常见分辨率下正常显示
- 表格支持横向滚动
- 图表自适应容器宽度

---

## 5. 测试计划

### 5.1 单元测试

为每个服务层函数编写单元测试:

```python
# project/tests/test_statistics.py
def test_get_procurement_statistics():
    """测试采购统计功能"""
    pass
```

### 5.2 功能测试

- [ ] 监控仪表盘数据正确性
- [ ] 统计数据计算准确性
- [ ] 排名算法正确性
- [ ] 报表生成和导出功能

### 5.3 性能测试

- [ ] 大数据量下的查询性能
- [ ] 页面加载速度
- [ ] 报表生成耗时

---

## 6. 部署清单

### 6.1 代码变更

- [ ] 合并所有新增代码
- [ ] 更新 [`config/urls.py`](config/urls.py)
- [ ] 更新 [`project/templates/base.html`](project/templates/base.html) 导航

### 6.2 依赖检查

检查 [`requirements.txt`](requirements.txt):
- ✅ openpyxl (已有)
- ✅ pandas (已有)  
- 📦 reportlab (可选,如需PDF)

### 6.3 静态文件

- [ ] 收集静态文件: `python manage.py collectstatic`
- [ ] 验证Chart.js CDN可访问

### 6.4 数据库

**无需迁移!** 本次开发不涉及数据库结构变更。

---

## 7. 验收标准

### 7.1 功能完整性

- [ ] 归档监控功能可用,预警准确
- [ ] 数据更新监控功能可用
- [ ] 数据齐全性检查功能可用
- [ ] 统计分析页面数据准确
- [ ] 业务排名功能可用
- [ ] 报表生成和导出功能可用

### 7.2 性能要求

- [ ] 监控页面加载时间 < 3秒
- [ ] 统计页面加载时间 < 5秒
- [ ] 报表生成时间 < 10秒

### 7.3 用户体验

- [ ] 界面风格与现有页面一致
- [ ] 操作流程清晰直观
- [ ] 图表展示清晰美观
- [ ] 移动端基本可用

---

## 8. 风险与应对

### 8.1 潜在风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 大数据量查询慢 | 中 | 增加索引,分页查询 |
| 统计逻辑复杂 | 中 | 充分测试,逐步优化 |
| 用户需求变化 | 低 | 预留扩展接口 |

### 8.2 回滚方案

如果出现问题:
1. 移除新增的URL路由
2. 从导航栏移除监控菜单
3. 不影响现有业务功能

---

## 9. 后续优化方向

### 9.1 短期优化 (1-2个月)

- 增加缓存机制提升性能
- 优化图表交互体验
- 增加数据导出格式

### 9.2 中期扩展 (3-6个月)

- 预警通知推送
- 自定义报表模板
- 数据钻取分析

### 9.3 长期规划 (6个月以上)

- 独立监控应用重构
- 实时数据更新
- 移动端适配

---

## 10. 总结

本开发计划明确定位为**在现有系统上增加监控和报表功能**,采用渐进式开发策略:

✅ **最小改动**: 在现有代码基础上扩展  
✅ **快速交付**: 分阶段实现,每阶段可独立使用  
✅ **风险可控**: 不影响现有业务功能  
✅ **易于维护**: 代码结构清晰,便于后续扩展

---

**文档状态:** ✅ 已完成  
**审核状态:** 待审核  
**下一步:** 开始第一阶段开发