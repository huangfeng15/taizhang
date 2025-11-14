"""
Word报表生成器
整合数据采集、图表生成和文档构建，生成完整的监控报表
"""
from datetime import date, timedelta
from typing import Optional, List
import os

from .report_data_collector import ReportDataCollector
from .chart_generator import ChartGenerator
from .word_document_builder import WordDocumentBuilder


class WordReportGenerator:
    """Word报表生成器"""
    
    def __init__(self, start_date: date, end_date: date, 
                 project_codes: Optional[List[str]] = None):
        """
        初始化报表生成器
        
        Args:
            start_date: 统计开始日期
            end_date: 统计结束日期
            project_codes: 项目编码列表
        """
        self.start_date = start_date
        self.end_date = end_date
        self.project_codes = project_codes
        
        # 初始化各个组件
        self.data_collector = ReportDataCollector(start_date, end_date, project_codes)
        self.chart_generator = ChartGenerator()
        self.doc_builder = WordDocumentBuilder()
    
    def generate_weekly_report(self, file_path: str):
        """
        生成周报
        
        Args:
            file_path: 输出文件路径
        """
        # 计算周期标识
        period = f"{self.start_date.strftime('%Y年%m月%d日')} - {self.end_date.strftime('%Y年%m月%d日')}"
        
        # 创建封面
        self.doc_builder.create_cover_page(
            title='工作监控周报',
            period=period,
            generate_date=date.today().strftime('%Y年%m月%d日')
        )
        
        # 生成报表内容
        self._build_report_content()
        
        # 保存文档
        self.doc_builder.save(file_path)
        
        # 清理临时图表文件
        self.chart_generator.cleanup_all()
    
    def generate_monthly_report(self, file_path: str):
        """
        生成月报
        
        Args:
            file_path: 输出文件路径
        """
        # 计算周期标识
        period = f"{self.start_date.year}年{self.start_date.month}月"
        
        # 创建封面
        self.doc_builder.create_cover_page(
            title='工作监控月报',
            period=period,
            generate_date=date.today().strftime('%Y年%m月%d日')
        )
        
        # 生成报表内容
        self._build_report_content()
        
        # 保存文档
        self.doc_builder.save(file_path)
        
        # 清理临时图表文件
        self.chart_generator.cleanup_all()
    
    def _build_report_content(self):
        """构建报表内容"""
        # 第一章：总体情况概览
        self._build_overview_chapter()
        
        # 第二章：各项目详细情况
        self._build_projects_chapter()
        
        # 第三章：监控问题汇总
        self._build_issues_chapter()
        
        # 第四章：建议与行动项
        self._build_suggestions_chapter()
    
    def _build_overview_chapter(self):
        """构建总体情况概览章节"""
        self.doc_builder.add_chapter('第一章 总体情况概览', level=1)
        
        # 1.1 核心数据汇总
        self.doc_builder.add_chapter('1.1 核心数据汇总', level=2)
        
        overview_data = self.data_collector.collect_overview_data()
        
        # 显示核心统计数据
        summary_data = {
            '项目总数': f"{overview_data['project_count']}个",
            '新增项目': f"{overview_data['new_project_count']}个",
            '采购活动总数': f"{overview_data['procurement_stats']['total_count']}个",
            '采购总金额': f"{overview_data['procurement_stats']['total_amount']}万元",
            '平均采购周期': f"{overview_data['procurement_stats']['avg_cycle']}天",
            '签订合同数': f"{overview_data['contract_stats']['total_count']}个",
            '合同总额': f"{overview_data['contract_stats']['total_amount']}万元",
            '支付金额': f"{overview_data['payment_stats']['total_amount']}万元",
            '支付率': f"{overview_data['payment_stats']['payment_rate']}%",
            '结算金额': f"{overview_data['settlement_stats']['total_amount']}万元"
        }
        
        self.doc_builder.add_summary_box('核心数据', summary_data)
        
        # 1.2 对比分析
        self.doc_builder.add_chapter('1.2 对比分析', level=2)
        
        comparison = overview_data['comparison']
        comparison_text = f"""
与上期对比：
• 采购数量变化：{comparison['procurement_count_change']:+.1f}%
• 采购金额变化：{comparison['procurement_amount_change']:+.1f}%
• 合同数量变化：{comparison['contract_count_change']:+.1f}%
• 合同金额变化：{comparison['contract_amount_change']:+.1f}%
        """
        self.doc_builder.add_paragraph(comparison_text.strip())
        
        # 1.3 可视化图表
        self.doc_builder.add_chapter('1.3 数据可视化', level=2)
        
        # 生成对比图表
        try:
            chart_data = {
                'labels': ['采购数量', '合同数量'],
                'current': [
                    overview_data['procurement_stats']['total_count'],
                    overview_data['contract_stats']['total_count']
                ],
                'previous': [
                    max(0, overview_data['procurement_stats']['total_count'] - 
                        int(overview_data['procurement_stats']['total_count'] * 
                            comparison['procurement_count_change'] / 100)),
                    max(0, overview_data['contract_stats']['total_count'] - 
                        int(overview_data['contract_stats']['total_count'] * 
                            comparison['contract_count_change'] / 100))
                ]
            }
            
            chart_path = self.chart_generator.generate_comparison_chart(
                chart_data, '业务数量对比'
            )
            self.doc_builder.add_image(chart_path, width=5.5)
        except Exception as e:
            self.doc_builder.add_paragraph(f'图表生成失败: {str(e)}')
        
        self.doc_builder.add_page_break()
    
    def _build_projects_chapter(self):
        """构建各项目详细情况章节"""
        self.doc_builder.add_chapter('第二章 各项目详细情况', level=1)
        
        projects_data = self.data_collector.collect_project_details()
        
        for idx, project in enumerate(projects_data[:10], 1):  # 限制10个项目
            # 项目标题
            self.doc_builder.add_chapter(
                f"2.{idx} {project['project_name']}", 
                level=2
            )
            
            # 2.X.1 项目基本信息
            self.doc_builder.add_chapter(f"2.{idx}.1 项目基本信息", level=3)
            basic_info = {
                '项目编号': project['project_code'],
                '项目名称': project['project_name'],
                '采购数量': f"{len(project['procurements'])}个",
                '合同数量': f"{len(project['contracts'])}个"
            }
            self.doc_builder.add_key_value_table(basic_info)
            
            # 2.X.2 采购活动清单
            if project['procurements']:
                self.doc_builder.add_chapter(f"2.{idx}.2 采购活动清单", level=3)
                procurement_headers = ['采购编号', '采购名称', '类型', '预算金额(万元)', 
                                      '中标金额(万元)', '状态', '经办人']
                procurement_data = [
                    [
                        p['code'], p['name'][:20], p['type'], 
                        p['budget_amount'], p['winning_amount'], 
                        p['status'], p['officer']
                    ]
                    for p in project['procurements'][:10]
                ]
                self.doc_builder.add_table(procurement_data, procurement_headers)
            
            # 2.X.3 合同执行情况
            if project['contracts']:
                self.doc_builder.add_chapter(f"2.{idx}.3 合同执行情况", level=3)
                contract_headers = ['合同编号', '合同名称', '签订日期', '合同金额(万元)', 
                                  '已支付(万元)', '执行率(%)', '经办人']
                contract_data = [
                    [
                        c['code'], c['name'][:20], c['signing_date'], 
                        c['amount'], c['paid_amount'], 
                        c['execution_rate'], c['officer']
                    ]
                    for c in project['contracts'][:10]
                ]
                self.doc_builder.add_table(contract_data, contract_headers)
            
            # 2.X.4 里程碑事件
            if project['milestones']:
                self.doc_builder.add_chapter(f"2.{idx}.4 项目里程碑事件", level=3)
                milestone_items = [
                    f"{m['date']}: {m['event']}"
                    for m in project['milestones'][:10]
                ]
                self.doc_builder.add_bullet_list(milestone_items)
            
            if idx < len(projects_data[:10]):
                self.doc_builder.add_page_break()
    
    def _build_issues_chapter(self):
        """构建监控问题汇总章节"""
        self.doc_builder.add_chapter('第三章 监控问题汇总', level=1)
        
        issues_data = self.data_collector.collect_monitoring_issues()
        
        # 3.1 归档问题
        self._build_archive_issues_section(issues_data['archive_issues'])
        
        # 3.2 更新问题
        self._build_update_issues_section(issues_data['update_issues'])
        
        # 3.3 齐全性问题
        self._build_completeness_issues_section(issues_data['completeness_issues'])
        
        # 3.4 问题汇总分析
        self._build_issues_summary_section(issues_data['summary'])
        
        self.doc_builder.add_page_break()
    
    def _build_archive_issues_section(self, archive_issues):
        """构建归档问题小节"""
        self.doc_builder.add_chapter('3.1 归档问题', level=2)
        
        stats = archive_issues['statistics']
        
        # 3.1.1 超期未归档统计
        self.doc_builder.add_chapter('3.1.1 超期未归档统计', level=3)
        
        stat_data = {
            '采购超期数': f"{stats['procurement_overdue']}个",
            '合同超期数': f"{stats['contract_overdue']}个",
            '平均超期天数': f"{stats['avg_overdue_days']}天"
        }
        self.doc_builder.add_key_value_table(stat_data)
        
        # 3.1.2 超期未归档清单
        if archive_issues['overdue_list']:
            self.doc_builder.add_chapter('3.1.2 超期未归档清单', level=3)
            
            headers = ['编号', '名称', '类型', '业务日期', '应归档日期', '超期天数', '责任人', '项目']
            data = [
                [
                    item['code'][:15], item['name'][:20], item['type'],
                    str(item['business_date'])[:10], str(item['archive_deadline'])[:10],
                    item['overdue_days'], item['person'][:10], item['project'][:10]
                ]
                for item in archive_issues['overdue_list'][:30]
            ]
            self.doc_builder.add_table(data, headers)
        
        # 3.1.3 责任人分布
        if archive_issues['person_distribution']:
            self.doc_builder.add_chapter('3.1.3 责任人问题分布', level=3)
            
            headers = ['责任人', '超期数量', '平均超期天数']
            data = [
                [p['person'], p['count'], p['avg_overdue_days']]
                for p in archive_issues['person_distribution'][:10]
            ]
            self.doc_builder.add_table(data, headers)
    
    def _build_update_issues_section(self, update_issues):
        """构建更新问题小节"""
        self.doc_builder.add_chapter('3.2 更新问题', level=2)
        
        stats = update_issues['statistics']
        
        # 统计数据
        stat_data = {
            '采购延迟数': f"{stats['procurement_delayed']}个",
            '合同延迟数': f"{stats['contract_delayed']}个",
            '支付延迟数': f"{stats['payment_delayed']}个",
            '结算延迟数': f"{stats['settlement_delayed']}个",
            '平均延迟天数': f"{stats['avg_delay_days']}天"
        }
        self.doc_builder.add_key_value_table(stat_data)
        
        # 延迟清单
        if update_issues['delayed_list']:
            self.doc_builder.add_chapter('3.2.1 更新延迟清单', level=3)
            
            headers = ['编号', '名称', '模块', '业务日期', '应更新日期', '实际更新日期', '延迟天数']
            data = [
                [
                    item['code'][:15], item['name'][:20], item['module'],
                    str(item['business_date'])[:10], str(item['update_deadline'])[:10],
                    str(item['actual_update_date'])[:10], item['delay_days']
                ]
                for item in update_issues['delayed_list'][:30]
            ]
            self.doc_builder.add_table(data, headers)
    
    def _build_completeness_issues_section(self, completeness_issues):
        """构建齐全性问题小节"""
        self.doc_builder.add_chapter('3.3 齐全性问题', level=2)
        
        stats = completeness_issues['statistics']
        
        stat_data = {
            '采购记录总数': f"{stats['procurement_total']}个",
            '采购完整记录': f"{stats['procurement_complete']}个",
            '采购齐全率': f"{stats['procurement_rate']}%",
            '合同记录总数': f"{stats['contract_total']}个",
            '合同完整记录': f"{stats['contract_complete']}个",
            '合同齐全率': f"{stats['contract_rate']}%",
            '综合齐全率': f"{stats['overall_rate']}%"
        }
        self.doc_builder.add_key_value_table(stat_data)
    
    def _build_issues_summary_section(self, summary):
        """构建问题汇总分析小节"""
        self.doc_builder.add_chapter('3.4 问题汇总分析', level=2)
        
        # 问题总数
        self.doc_builder.add_paragraph(
            f"问题总数：{summary['total_issues']}个", 
            bold=True, 
            font_size=11
        )
        
        # 按类型统计
        self.doc_builder.add_empty_line()
        self.doc_builder.add_paragraph('按类型统计：', bold=True)
        type_items = [
            f"归档问题：{summary['by_type']['archive']}个",
            f"更新问题：{summary['by_type']['update']}个",
            f"齐全性问题：{summary['by_type']['completeness']}个"
        ]
        self.doc_builder.add_bullet_list(type_items)
        
        # 按严重程度统计
        self.doc_builder.add_empty_line()
        self.doc_builder.add_paragraph('按严重程度统计：', bold=True)
        severity_items = [
            f"高风险：{summary['severity']['high']}个",
            f"中风险：{summary['severity']['medium']}个",
            f"低风险：{summary['severity']['low']}个"
        ]
        self.doc_builder.add_bullet_list(severity_items)
    
    def _build_suggestions_chapter(self):
        """构建建议与行动项章节"""
        self.doc_builder.add_chapter('第四章 建议与行动项', level=1)
        
        # 4.1 改进建议
        self.doc_builder.add_chapter('4.1 改进建议', level=2)
        
        suggestions = {
            '归档管理': [
                '建议加强对超期归档业务的督办力度',
                '建议完善归档流程规范，明确时间节点',
                '建议对经常超期的责任人进行培训'
            ],
            '数据更新': [
                '建议建立每日数据更新检查机制',
                '建议对延迟更新情况进行通报',
                '建议优化系统操作流程，减少录入时间'
            ],
            '数据质量': [
                '建议补充必填字段信息',
                '建议建立数据质量考核机制',
                '建议加强数据齐全性检查'
            ],
            '流程优化': [
                '建议简化业务流程，提高办事效率',
                '建议加强部门间协同配合',
                '建议定期开展业务培训'
            ]
        }
        
        for category, items in suggestions.items():
            self.doc_builder.add_paragraph(f"\n{category}：", bold=True)
            self.doc_builder.add_bullet_list(items)
        
        # 4.2 下一周期关注重点
        self.doc_builder.add_chapter('4.2 下一周期关注重点', level=2)
        
        focus_points = [
            '重点关注超期时间较长的归档业务',
            '加强对数据更新及时性的监控',
            '持续提升数据齐全性',
            '优化业务流程，缩短业务周期',
            '加强对问题频发人员和项目的督导'
        ]
        self.doc_builder.add_bullet_list(focus_points)
        
        # 4.3 持续改进计划
        self.doc_builder.add_chapter('4.3 持续改进计划', level=2)
        
        plans = {
            '短期目标（本周/本月）': [
                '完成所有超期归档业务的督办',
                '提升数据更新及时率至95%以上',
                '补充缺失的必填字段信息'
            ],
            '中期目标（本季度）': [
                '建立完善的监控预警机制',
                '优化业务流程，平均周期缩短10%',
                '数据齐全率达到98%以上'
            ],
            '长期目标（全年）': [
                '实现业务全流程数字化管理',
                '建立智能化监控预警系统',
                '打造数据质量标杆'
            ]
        }
        
        for goal_type, items in plans.items():
            self.doc_builder.add_paragraph(f"\n{goal_type}：", bold=True)
            self.doc_builder.add_number_list(items)