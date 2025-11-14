"""
图表生成器
使用matplotlib生成报表图表
"""
import os
import tempfile
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import rcParams
import numpy as np

# 设置中文字体支持
matplotlib.use('Agg')  # 使用非交互式后端
rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class ChartGenerator:
    """图表生成器类"""
    
    def __init__(self):
        """初始化图表生成器"""
        self.temp_files = []  # 记录临时文件以便清理
    
    def generate_bar_chart(self, data: Dict[str, Any], title: str, 
                          x_label: str = '', y_label: str = '', 
                          figsize: tuple = (10, 6)) -> str:
        """
        生成柱状图
        
        Args:
            data: {'labels': [...], 'values': [...]}
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            figsize: 图表大小
            
        Returns:
            str: 临时文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        # 创建柱状图
        bars = ax.bar(range(len(labels)), values, color='#3498db', alpha=0.8)
        
        # 设置标签
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # 在柱子上显示数值
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom', fontsize=10)
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # 保存到临时文件
        temp_path = self._save_temp_chart(fig)
        plt.close(fig)
        
        return temp_path
    
    def generate_pie_chart(self, data: Dict[str, Any], title: str,
                          figsize: tuple = (10, 8)) -> str:
        """
        生成饼图
        
        Args:
            data: {'labels': [...], 'values': [...]}
            title: 图表标题
            figsize: 图表大小
            
        Returns:
            str: 临时文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        # 颜色方案
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', 
                 '#1abc9c', '#34495e', '#95a5a6']
        
        # 创建饼图
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(labels)],
            explode=[0.05] * len(labels)  # 稍微分离各部分
        )
        
        # 美化文字
        for text in texts:
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 保存到临时文件
        temp_path = self._save_temp_chart(fig)
        plt.close(fig)
        
        return temp_path
    
    def generate_line_chart(self, data: Dict[str, Any], title: str,
                           x_label: str = '', y_label: str = '',
                           figsize: tuple = (12, 6)) -> str:
        """
        生成折线图
        
        Args:
            data: {'labels': [...], 'series': [{'name': '', 'values': [...]}, ...]}
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            figsize: 图表大小
            
        Returns:
            str: 临时文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        labels = data.get('labels', [])
        series = data.get('series', [])
        
        # 颜色方案
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']
        
        # 绘制多条折线
        for idx, s in enumerate(series):
            ax.plot(range(len(labels)), s['values'], 
                   marker='o', linewidth=2, markersize=6,
                   label=s['name'], color=colors[idx % len(colors)])
        
        # 设置标签
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # 添加图例
        ax.legend(loc='best', fontsize=10)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # 保存到临时文件
        temp_path = self._save_temp_chart(fig)
        plt.close(fig)
        
        return temp_path
    
    def generate_stacked_bar_chart(self, data: Dict[str, Any], title: str,
                                   x_label: str = '', y_label: str = '',
                                   figsize: tuple = (12, 6)) -> str:
        """
        生成堆叠柱状图
        
        Args:
            data: {'labels': [...], 'series': [{'name': '', 'values': [...]}, ...]}
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            figsize: 图表大小
            
        Returns:
            str: 临时文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        labels = data.get('labels', [])
        series = data.get('series', [])
        
        # 颜色方案
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']
        
        # 计算堆叠位置
        x = np.arange(len(labels))
        width = 0.6
        bottom = np.zeros(len(labels))
        
        # 绘制堆叠柱状图
        for idx, s in enumerate(series):
            ax.bar(x, s['values'], width, label=s['name'],
                  bottom=bottom, color=colors[idx % len(colors)], alpha=0.8)
            bottom += np.array(s['values'])
        
        # 设置标签
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # 添加图例
        ax.legend(loc='best', fontsize=10)
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # 保存到临时文件
        temp_path = self._save_temp_chart(fig)
        plt.close(fig)
        
        return temp_path
    
    def generate_horizontal_bar_chart(self, data: Dict[str, Any], title: str,
                                     x_label: str = '', y_label: str = '',
                                     figsize: tuple = (10, 8)) -> str:
        """
        生成水平柱状图（适合显示排名数据）
        
        Args:
            data: {'labels': [...], 'values': [...]}
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            figsize: 图表大小
            
        Returns:
            str: 临时文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        # 创建水平柱状图
        y_pos = np.arange(len(labels))
        bars = ax.barh(y_pos, values, color='#3498db', alpha=0.8)
        
        # 设置标签
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        
        # 在柱子上显示数值
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f'{width:.1f}',
                   ha='left', va='center', fontsize=10, 
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # 添加网格
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # 保存到临时文件
        temp_path = self._save_temp_chart(fig)
        plt.close(fig)
        
        return temp_path
    
    def generate_comparison_chart(self, data: Dict[str, Any], title: str,
                                  figsize: tuple = (10, 6)) -> str:
        """
        生成对比图（显示当期与上期对比）
        
        Args:
            data: {
                'labels': [...],
                'current': [...],
                'previous': [...]
            }
            title: 图表标题
            figsize: 图表大小
            
        Returns:
            str: 临时文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        labels = data.get('labels', [])
        current = data.get('current', [])
        previous = data.get('previous', [])
        
        x = np.arange(len(labels))
        width = 0.35
        
        # 创建并排柱状图
        bars1 = ax.bar(x - width/2, current, width, label='当期', 
                      color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, previous, width, label='上期', 
                      color='#95a5a6', alpha=0.8)
        
        # 设置标签
        ax.set_ylabel('数量/金额', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend(fontsize=10)
        
        # 在柱子上显示数值
        def add_value_labels(bars):
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}',
                       ha='center', va='bottom', fontsize=9)
        
        add_value_labels(bars1)
        add_value_labels(bars2)
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # 保存到临时文件
        temp_path = self._save_temp_chart(fig)
        plt.close(fig)
        
        return temp_path
    
    def _save_temp_chart(self, fig) -> str:
        """保存图表到临时文件"""
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        
        # 保存图表
        fig.savefig(temp_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        
        # 记录临时文件
        self.temp_files.append(temp_path)
        
        return temp_path
    
    def cleanup_chart(self, chart_path: str):
        """清理单个图表文件"""
        if os.path.exists(chart_path):
            try:
                os.remove(chart_path)
                if chart_path in self.temp_files:
                    self.temp_files.remove(chart_path)
            except Exception:
                pass
    
    def cleanup_all(self):
        """清理所有临时图表文件"""
        for path in self.temp_files[:]:
            self.cleanup_chart(path)
        self.temp_files = []
    
    def __del__(self):
        """析构函数，自动清理临时文件"""
        self.cleanup_all()