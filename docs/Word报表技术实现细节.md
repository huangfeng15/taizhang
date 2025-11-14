
# Word报表技术实现细节补充

## 四、实施步骤

### 第一阶段：基础框架搭建（2-3天）

#### 1. 安装依赖
```bash
# 已在 requirements.txt 中包含
pip install python-docx matplotlib pillow
```

#### 2. 创建目录结构
```bash
mkdir -p project/services/reports
mkdir -p project/templates/reports
mkdir -p static/reports/chart_images
```

#### 3. 创建核心模块文件
- `project/services/reports/__init__.py`
- `project/services/reports/report_data_collector.py`
- `project/services/reports/chart_generator.py`
- `project/services/reports/word_document_builder.py`
- `project/services/reports/word_report_generator.py`

### 第二阶段：数据采集服务（3-4天）

复用现有监控服务，整合数据：

```python
# report_data_collector.py 核心逻辑

from project.services.monitors.archive_statistics import ArchiveStatisticsService
from project.services.monitors.update_statistics import UpdateStatisticsService
from project.services.monitors.completeness_statistics import CompletenessStatisticsService

class ReportDataCollector:
    def collect_monitoring_issues(self):
        """整合所有监控问题数据"""
        
        # 1. 归档问题
        archive_service = ArchiveStatisticsService()
        archive_data = archive_service.get_projects_archive_overview(
            year_filter=self.year,
            project_filter=self.project_codes[0] if self.project_codes else None
        )
        
        # 2. 更新问题
        update_service = UpdateStatisticsService(start_date=self.start_date)
        update_data = update_service.get_projects_update_overview(
            year_filter=self.year,
            project_filter=self.project_codes[0] if self.project_codes else None
        )
        
        # 3. 齐全性问题
        completeness_service = CompletenessStatisticsService()
        completeness_data = completeness_service.get_projects_completeness_overview(
            year_filter=self.year,
            project_filter=self.project_codes[0] if self.project_codes else None
        )
        
        # 整合并返回
        return {
            'archive_issues': self._format_archive_issues(archive_data),
            'update_issues': self._format_update_issues(update_data),
            'completeness_issues': self._format_completeness_issues(completeness_data),
            'summary': self._build_issues_summary(archive_data, update_data, completeness_data)
        }
```

### 第三阶段：Word文档生成（3-4天）

#### 关键技术点

**1. 中文字体支持**
```python
from docx.oxml.ns import qn

# 设置中文字体
style = doc.styles['Normal']
style.font.name = 'Microsoft YaHei'
style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
```

**2. 表格样式**
```python
# 创建专业表格
table = doc.add_table(rows=1, cols=len(headers))
table.style = 'Light Grid Accent 1'  # 使用内置样式
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# 设置列宽
for i, width in enumerate(column_widths):
    table.columns[i].width = Inches(width)
```

**3. 图表嵌入**
```python
# matplotlib生成图表
plt.figure(figsize=(10, 6))
plt.plot(x, y)
temp_path = '/tmp/chart.png'
plt.savefig(temp_path, dpi=150, bbox_inches='tight')
plt.close()

# 插入Word
doc.add_picture(temp_path, width=Inches(6))
os.remove(temp_path)  # 清理临时文件
```

**4. 分页控制**
```python
# 章节后分页
doc.add_page_break()
```

### 第四阶段：视图集成（2天）

#### 扩展 views_reports.py

```python
from project.services.reports.word_report_generator import WordReportGenerator

@require_http_methods(['GET', 'POST'])
def generate_word_report(request):
    """生成Word监控报表"""
    
    if request.method == 'GET':
        # 显示表单
        context = {
            'page_title': 'Word监控报表生成',
            'report_types': ['weekly', 'monthly'],
            'projects': Project.objects.all()
        }
        return render(request, 'reports/word_report_form.html', context)
    
    # POST: 生成报表
    try:
        report_type = request.POST.get('report_type', 'weekly')
        project_codes = request.POST.getlist('projects')
        
        # 计算日期范围
        if report_type == 'weekly':
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
        else:  # monthly
            end_date = date.today()
            start_date = date(end_date.year, end_date.month, 1)
        
        # 生成报表
        generator = WordReportGenerator(
            start_date=start_date,
            end_date=end_date,
            project_codes=project_codes if project_codes else None
        )
        
        # 临时文件
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            if report_type == 'weekly':
                generator.generate_weekly_report(tmp_path)
            else:
                generator.generate_monthly_report(tmp_path)
            
            # 读取并返回
            with open(tmp_path, 'rb') as f:
                content = f.read()
            
            filename = f'监控报表_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx'
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except Exception as e:
        messages.error(request, f'生成报表失败: {str(e)}')
        return redirect('generate_word_report')
```

#### 添加URL路由

```python
# config/urls.py
urlpatterns = [
    # ...
    path('reports/word/', views.generate_word_report, name='generate_word_report'),
]
```

### 第五阶段：前端界面（1-2天）

#### 创建表单页面 `templates/reports/word_report_form.html`

```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h2>{{ page_title }}</h2>
    
    <form method="post" action="{% url 'generate_word_report' %}">
        {% csrf_token %}
        
        <div class="form-group">
            <label>报表类型</label>
            <select name="report_type" class="form-control">
                <option value="weekly">周报</option>
                <option value="monthly">月报</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>选择项目（可多选，不选则全部）</label>
            <select name="projects" class="form-control" multiple size="10">
                {% for project in projects %}
                <option value="{{ project.project_code }}">
                    {{ project.project_name }}
                </option>
                {% endfor %}
            </select>
        </div>
        
        <button type="submit" class="btn btn-primary">
            <i class="fas fa-file-word"></i> 生成Word报表
        </button>
    </form>
</div>
{% endblock %}
```

## 五、核心代码示例

### 1. 归档问题格式化

```python
def _format_archive_issues(self, archive_data):
    """格式化归档问题数据"""
    
    # 从 archive_data['problems'] 获取问题清单
    problems = archive_data.get('problems', {})
    
    return {
        'statistics': {
            'procurement_overdue': len(problems.get('procurement', [])),
            'contract_overdue': len(problems.get('contract', [])),
            'avg_overdue_days': self._calc_avg_overdue_days(problems)
        },
        'overdue_list': [
            {
                'code': item['code'],
                'name': item['name'],
                'type': '采购' if item['module'] == 'procurement' else '合同',
                'business_date': item['business_date'],
                'archive_deadline': item['archive_deadline'],
                'overdue_days': item['overdue_days'],
                'person': item['responsible_person'],
                'project': item.get('project_code', '-')
            }
            for module_items in problems.values()
            for item in module_items
        ][:50],  # 限制50条
        'person_distribution': self._calc_person_distribution(problems)
    }
```

### 2. 问题汇总分析

```python
def _build_issues_summary(self, archive_data, update_data, completeness_data):
    """构建问题汇总分析"""
    
    # 统计各类问题总数
    total_archive = len(archive_data.get('problems', {}).get('procurement', [])) + \
                   len(archive_data.get('problems', {}).get('contract', []))
    total_update = sum(len(v) for v in update_data.get('problems', {}).values())
    total_completeness = len(completeness_data.get('incomplete_records', []))
    
    # 问题严重程度分级
    high_risk = self._count_high_risk_issues(archive_data, update_data)
    medium_risk = self._count_medium_risk_issues(archive_data, update_data)
    low_risk = total_archive + total_update - high_risk - medium_risk
    
    # 责任人问题分布
    person_stats = self._aggregate_person_issues(
        archive_data, update_data, completeness_data
    )
    
    return {
        'total_issues': total_archive + total_update + total_completeness,
        'severity': {
            'high': high_risk,
            'medium': medium_risk,
            'low': low_risk
        },
        'by_type': {
            'archive': total_archive,
            'update': total_update,
            'completeness': total_completeness
        },
        'person_distribution': person_stats
    }
```

### 3. 建议生成逻辑

```python
def _build_suggestions_chapter(self, monitoring_issues):
    """构建建议与行动项章节"""
    
    self.doc_builder.add_chapter('第四章 建议与行动项', level=1)
    
    # 4.1 问题项目优先级
    self.doc_builder.add_chapter('4.1 问题项目优先级排序', level=2)
    
    priority_projects = self._rank_problem_projects(monitoring_issues)
    if priority_projects:
        data = [
            [
                i,
                p['project_name'],
                p['total_issues'],
                p['high_risk_issues'],
                p['main_person'],
                p['suggestions']
            ]
            for i, p in enumerate(priority_projects[:10], 1)
        ]
        self.doc_builder.add_table(
            data=data,
            headers=['排名', '项目名称', '问题总数', '高风险', '责任人', '建议措施']
        )
    
    # 4.2 改进建议
    self.doc_builder.add_chapter('4.2 改进建议', level=2)
    
    suggestions = self._generate_suggestions(monitoring_issues)
    for category, items in suggestions.items():
        self.doc_builder.add_paragraph(f"\n{category}：", bold=True)
        self.doc_builder.add_bullet_list(items)
    
    # 4.3 下一周期关注重点
    self.doc_builder.add_chapter('4.3 下一周期关注重点', level=2)
    
    focus_points = self._generate_focus_points(monitoring_issues)
    self.doc_builder.add_bullet_list(focus_points)
```

## 六、性能优化建议

### 1. 数据采集优化
- 使用 `select_related()` 和 `prefetch_related()` 减少数据库查询
- 对大数据量使用分页和限制（如每类问题最多50条）
- 缓存中间计算结果

### 2. 图表生成优化
- 复用 matplotlib figure 对象
- 及时关闭图表释放内存：`plt.close()`
- 控制图表DPI（150已足够）

### 3. 文档生成优化
- 使用流式处理，避免一次性加载所有数据
- 临时文件使用后立即清理
- 限制表格行数，超过的提供"更多详情请查看系统"提示

## 七、测试计划

### 单元测试
```python
# tests/test_word_report.py

def test_data_collector():
    """测试数据采集"""
    collector = ReportDataCollector(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 7)
    )
    data = collector.collect_overview_data()
    assert 'project_count' in data
    assert 'procurement_stats' in data

def test_chart_generator():
    """测试图表生成"""
    generator = ChartGenerator()
    data = {'labels': ['A', 'B'], 'values': [10, 20]}
    path = generator.generate_bar_chart(data, '测试', 'X', 'Y')
    assert os.path.exists(path)
    generator.cleanup_chart(path)

def test_word_document_builder():
    """测试文档构建"""
    builder = WordDocumentBuilder()
    builder.create_cover_page('测试报告', '2025年第1周', '2025-01-07')
    builder.add_chapter('第一章', level=1)
    
    # 保存并验证
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        builder.save(f.name)
        assert os.path.exists(f.name)
        os.remove(f.name)
```

### 集成测试
- 测试完整周报生成流程
- 测试完整月报生成流程
- 测试多项目筛选
- 测试异常情况处理

## 八、部署说明

### 1. 依赖检查
```bash
pip list | grep -E "(python-docx|matplotlib)"
```

### 2. 字体配置
确保服务器上有中文字体：
- Windows: 默认有微软雅黑
- Linux: 需安装中文字体包
```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei
