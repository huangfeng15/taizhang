"""
更新监控统计门面类
统一管理更新监控的各种服务调用，提供简洁的接口
参照归档监控的设计模式
"""
from .update_statistics import UpdateStatisticsService


class UpdateStatisticsFacade:
    """
    更新监控统计门面类
    提供统一的接口来访问更新监控的各种统计功能
    """
    
    def __init__(self, start_date=None):
        """
        初始化服务实例
        
        Args:
            start_date: 起始日期，只统计该日期之后的业务数据
        """
        self.stats_service = UpdateStatisticsService(start_date=start_date)
    
    def get_overview(self, view_mode='project', year_filter=None, project_filter=None, start_date=None):
        """
        获取概览数据（项目视图或个人视图）
        
        Args:
            view_mode: 'project' 或 'person'
            year_filter: 年度筛选
            project_filter: 项目筛选
            start_date: 起始日期筛选
        
        Returns:
            dict: 概览数据
        """
        if view_mode == 'project':
            return self.stats_service.get_projects_update_overview(
                year_filter=year_filter,
                project_filter=project_filter,
                start_date=start_date
            )
        else:
            return self.stats_service.get_persons_update_overview(
                year_filter=year_filter,
                project_filter=project_filter,
                start_date=start_date
            )
    
    def get_detail(self, view_mode='project', target_code=None, 
                   year_filter=None, project_filter=None, show_all=False):
        """
        获取详情数据（项目详情或经办人详情）
        
        Args:
            view_mode: 'project' 或 'person'
            target_code: 目标编码（项目编码或经办人姓名）
            year_filter: 年度筛选
            project_filter: 项目筛选（仅个人视图使用）
            show_all: 是否显示所有记录
        
        Returns:
            dict: 详情数据（包含趋势图和问题列表）
        """
        if not target_code:
            # 如果没有指定目标，返回汇总数据
            if view_mode == 'person':
                return self.stats_service.get_all_persons_trend_and_problems(
                    year_filter=year_filter,
                    project_filter=project_filter,
                    show_all=show_all
                )
            return None
        
        if view_mode == 'project':
            return self.stats_service.get_project_trend_and_problems(
                project_code=target_code,
                year_filter=year_filter,
                show_all=show_all
            )
        else:
            return self.stats_service.get_person_trend_and_problems(
                person_name=target_code,
                year_filter=year_filter,
                project_filter=project_filter,
                show_all=show_all
            )
    
    def get_trend_and_problems(self, view_mode='project', year_filter=None, 
                              project_filter=None, show_all=False):
        """
        获取趋势图和问题列表（用于主页面展示）
        
        Args:
            view_mode: 'project' 或 'person'
            year_filter: 年度筛选
            project_filter: 项目筛选
            show_all: 是否显示所有记录
        
        Returns:
            dict: 趋势和问题数据
        """
        if view_mode == 'project' and project_filter:
            # 项目视图下选择了具体项目，显示该项目的趋势和问题
            return self.stats_service.get_project_trend_and_problems(
                project_code=project_filter,
                year_filter=year_filter,
                show_all=show_all
            )
        elif view_mode == 'person':
            # 个人视图下始终显示所有经办人的汇总数据
            return self.stats_service.get_all_persons_trend_and_problems(
                year_filter=year_filter,
                project_filter=project_filter,
                show_all=show_all
            )
        return None