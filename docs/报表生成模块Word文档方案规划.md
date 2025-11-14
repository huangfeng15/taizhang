
# 报表生成模块Word文档方案规划

## 一、方案概述

**完全可行！** 基于现有系统架构，我将为你设计一个专业的Word文档报表生成系统。系统已具备：
- ✅ `python-docx` 库支持（已在 requirements.txt 中）
- ✅ 完善的监控统计服务（归档、更新、齐全性、业务周期）
- ✅ 报表生成视图框架（`views_reports.py`）

## 二、报表内容结构设计

### 2.1 报表类型
- **周报**：每周自动生成（默认上周数据）
- **月报**：每月自动生成（默认上月数据）
- **临时报表**：手动触发任意时间段报表

### 2.2 Word文档内容结构

#### **封面页**
- 报告标题（如"2025年第1周工作报告"）
- 报告周期
- 生成时间
- 单位标识

#### **第一章：总体情况概览**

**1.1 核心数据汇总**
```
项目总数：XX个
- 新增项目：XX个
- 在建项目：XX个

采购活动：
- 总数：XX个
- 总金额：XX万元
- 平均周期：XX天

合同管理：
- 签订合同：XX个
- 合同总额：XX万元
- 执行中合同：XX个

支付结算：
- 支付金额：XX万元
- 结算金额：XX万元
- 支付率：XX%
```

**1.2 对比分析**
- 环比数据对比（与上周/上月对比）
- 关键指标变化趋势

**1.3 可视化图表**（嵌入Word）
- 项目分布饼图
- 金额趋势折线图
- 各项目进度对比柱状图

#### **第二章：各项目详细情况**

按项目分组，每个项目包含：

**2.X 项目名称**

**2.X.1 项目基本信息**
| 项目编号 | 项目名称 | 负责人 | 预算金额 | 状态 |
|---------|---------|--------|---------|------|
| XXX     | XXX     | XXX    | XXX     | XXX  |

**2.X.2 采购活动清单**
| 采购编号 | 采购名称 | 采购类型 | 预算金额 | 中标金额 | 状态 | 经办人 |
|---------|---------|---------|---------|---------|------|--------|
| XXX     | XXX     | XXX     | XXX     | XXX     | XXX  | XXX    |

**2.X.3 合同执行情况**
| 合同编号 | 合同名称 | 签订日期 | 合同金额 | 已支付 | 执行率 | 经办人 |
|---------|---------|---------|---------|--------|--------|--------|
| XXX     | XXX     | XXX     | XXX     | XXX    | XX%    | XXX    |

**2.X.4 支付进度**
- 累计支付：XX万元
- 待支付：XX万元
- 支付率：XX%

**2.X.5 项目里程碑事件**
- YYYY-MM-DD: 完成XX事项
- YYYY-MM-DD: 签订XX合同
- YYYY-MM-DD: 完成XX归档

#### **第三章：监控问题汇总**

**3.1 归档问题**

**3.1.1 超期未归档统计**
| 问题类型 | 数量 | 占比 | 平均超期天数 |
|---------|------|------|-------------|
| 采购归档 | XX   | XX%  | XX天        |
| 合同归档 | XX   | XX%  | XX天        |

**3.1.2 超期未归档清单**
| 编号 | 名称 | 类型 | 业务日期 | 应归档日期 | 超期天数 | 责任人 | 项目 |
|-----|------|------|---------|-----------|---------|--------|------|
| XXX | XXX  | 采购 | XXX     | XXX       | XX天    | XXX    | XXX  |

**3.1.3 责任人分布**
| 责任人 | 超期数量 | 平均超期天数 | 风险等级 |
|-------|---------|-------------|---------|
| 张三  | XX      | XX天        | 高      |

**3.2 更新问题**

**3.2.1 数据更新滞后统计**
| 模块 | 总数 | 延迟更新数 | 延迟率 | 平均延迟天数 |
|-----|------|-----------|--------|-------------|
| 采购 | XX   | XX        | XX%    | XX天        |
| 合同 | XX   | XX        | XX%    | XX天        |
| 支付 | XX   | XX        | XX%    | XX天        |
| 结算 | XX   | XX        | XX%    | XX天        |

**3.2.2 更新延迟清单**（前20条）
| 编号 | 名称 | 模块 | 业务日期 | 应更新日期 | 实际更新日期 | 延迟天数 | 责任人 |
|-----|------|------|---------|-----------|-------------|---------|--------|
| XXX | XXX  | XXX  | XXX     | XXX       | XXX         | XX天    | XXX    |

**3.3 业务周期问题**

**3.3.1 超业务周期统计**
| 业务类型 | 标准周期 | 超期数量 | 平均实际周期 | 最长周期 |
|---------|---------|---------|-------------|---------|
| 采购周期 | XX天    | XX      | XX天        | XX天    |
| 合同履约 | XX天    | XX      | XX天        | XX天    |

**3.3.2 超周期业务清单**
| 编号 | 名称 | 类型 | 开始日期 | 结束日期 | 实际周期 | 超标天数 | 风险等级 |
|-----|------|------|---------|---------|---------|---------|---------|
| XXX | XXX  | XXX  | XXX     | XXX     | XX天    | XX天    | 高      |

**3.4 齐全性检查问题**

**3.4.1 数据完整性统计**
| 模块 | 总记录数 | 完整记录数 | 完整率 | 缺失字段数 |
|-----|---------|-----------|--------|-----------|
| 采购 | XX      | XX        | XX%    | XX        |
| 合同 | XX      | XX        | XX%    | XX        |

**3.4.2 字段缺失分布**（Top 10）
| 字段名称 | 缺失数量 | 缺失率 | 所属模块 |
|---------|---------|--------|---------|
| XXX     | XX      | XX%    | 采购    |

**3.4.3 完整性低的记录清单**（前20条）
| 编号 | 名称 | 模块 | 完整率 | 缺失字段数 | 主要缺失字段 | 责任人 |
|-----|------|------|--------|-----------|------------|--------|
| XXX | XXX  | XXX  | XX%    | XX        | XX、XX、XX | XXX    |

**3.5 问题汇总分析**

**3.5.1 问题严重程度分级**
| 严重程度 | 问题数量 | 占比 | 主要类型 |
|---------|---------|------|---------|
| 高风险  | XX      | XX%  | XX      |
| 中风险  | XX      | XX%  | XX      |
| 低风险  | XX      | XX%  | XX      |

**3.5.2 责任部门/人员问题分布**
| 责任人 | 归档问题 | 更新问题 | 周期问题 | 齐全性问题 | 合计 | 风险评分 |
|-------|---------|---------|---------|-----------|------|---------|
| 张三  | XX      | XX      | XX      | XX        | XX   | XX分    |

#### **第四章：建议与行动项**

**4.1 问题项目优先级排序**（Top 10）
| 排名 | 项目名称 | 综合问题数 | 高风险问题 | 责任人 | 建议措施 |
|-----|---------|-----------|-----------|--------|---------|
| 1   | XXX     | XX        | XX        | XXX    | XXX     |

**4.2 改进建议**
1. **归档管理**
   - 建议加强XX项目的归档督办
   - 建议完善归档流程规范
   
2. **数据更新**
   - 建议XX人员及时更新数据
   - 建议建立每日更新机制
   
3. **业务周期**
   - 建议优化XX环节，缩短业务周期
   - 建议对超期业务进行重点监控
   
4. **数据质量**
   - 建议补充XX字段信息
   - 建议建立数据质量检查机制

**4.3 下一周期关注重点**
- 重点关注项目：XXX、XXX
- 重点关注人员：XXX、XXX
- 重点关注事项：XXX

**4.4 持续改进计划**
- 短期目标（本周/本月）
- 中期目标（本季度）
- 长期目标（全年）

#### **附录**
- 附录A：专业术语说明
- 附录B：统计口径说明
- 附录C：数据来源说明

## 三、技术架构设计

### 3.1 目录结构
```
project/
├── services/
│   └── reports/
│       ├── __init__.py
│       ├── word_report_generator.py      # Word报表主生成器
│       ├── report_data_collector.py      # 数据采集服务
│       ├── chart_generator.py            # 图表生成器
│       ├── word_document_builder.py      # Word文档构建器
│       └── report_templates.py           # 报表模板配置
├── templates/
│   └── reports/
│       ├── word_report_form.html         # Word报表生成界面
│       └── word_report_history.html      # 历史报表列表
└── static/
    └── reports/
        └── chart_images/                 # 临时图表图片目录
```

### 3.2 核心模块设计

#### **3.2.1 数据采集服务 (`report_data_collector.py`)**
```python
class ReportDataCollector:
    """统一采集所有报表所需数据"""
    
    def __init__(self, start_date, end_date, project_codes=None):
        self.start_date = start_date
        self.end_date = end_date
        self.project_codes = project_codes
    
    def collect_overview_data(self):
        """采集总体概览数据
        
        Returns:
            dict: {
                'project_count': 项目总数,
                'new_project_count': 新增项目数,
                'procurement_stats': {...},
                'contract_stats': {...},
                'payment_stats': {...},
                'comparison': {...}  # 对比数据
            }
        """
        pass
        
    def collect_project_details(self):
        """采集项目详细数据
        
        Returns:
            list: [{
                'project_code': 项目编码,
                'project_name': 项目名称,
                'procurements': [...],  # 采购列表
                'contracts': [...],     # 合同列表
                'payments': [...],      # 支付列表
                'milestones': [...]     # 里程碑事件
            }]
        """
        pass
        
    def collect_monitoring_issues(self):
        """采集监控问题数据
        
        使用现有监控服务：
        - archive_statistics.py: 归档问题
        - update_statistics.py: 更新问题
        - completeness_statistics.py: 齐全性问题
        - cycle_monitor: 业务周期问题
        
        Returns:
            dict: {
                'archive_issues': {...},
                'update_issues': {...},
                'cycle_issues': {...},
                'completeness_issues': {...},
                'summary': {...}  # 问题汇总分析
            }
        """
        from project.services.monitors.archive_statistics import ArchiveStatisticsService
        from project.services.monitors.update_statistics import UpdateStatisticsService
        from project.services.monitors.completeness_statistics import CompletenessStatisticsService
        
        # 使用现有服务获取问题数据
        archive_service = ArchiveStatisticsService()
        update_service = UpdateStatisticsService()
        completeness_service = CompletenessStatisticsService()
        
        # ... 调用各服务的问题检测方法
        pass
```

#### **3.2.2 图表生成器 (`chart_generator.py`)**
```python
import matplotlib.pyplot as plt
from matplotlib import rcParams
import io
from PIL import Image

class ChartGenerator:
    