/**
 * 通用趋势图组件
 * 
 * 功能特性：
 * 1. 支持月度和年度两种时间维度的趋势展示
 * 2. 使用实际数据点，而非平均值
 * 3. 空数据时显示友好提示
 * 4. 支持多系列数据对比
 * 5. 可配置的图表样式和交互
 * 
 * 使用方法：
 * const chart = new TrendChart('chartElementId', {
 *   title: '趋势图标题',
 *   data: chartData,
 *   dimension: 'month', // 'month' 或 'year'
 *   series: [{name: '系列1', key: 'value1'}, {name: '系列2', key: 'value2'}]
 * });
 */

class TrendChart {
    constructor(elementId, options = {}) {
        this.elementId = elementId;
        this.element = document.getElementById(elementId);
        
        if (!this.element) {
            console.error(`元素 #${elementId} 未找到`);
            return;
        }
        
        // 默认配置
        this.config = {
            title: options.title || '趋势图',
            subtitle: options.subtitle || '',
            dimension: options.dimension || 'month', // 'month' 或 'year'
            data: options.data || [],
            series: options.series || [{name: '数值', key: 'value', color: '#4e73df'}],
            baselinesSeries: options.baselinesSeries || [], // 基准线系列配置
            height: options.height || 350,
            showLegend: options.showLegend !== false,
            showDataLabels: options.showDataLabels !== false,
            enableZoom: options.enableZoom !== false,
            emptyMessage: options.emptyMessage || '暂无数据',
            yAxisFormatter: options.yAxisFormatter || null,
            tooltipFormatter: options.tooltipFormatter || null,
            ...options
        };
        
        this.chart = null;
        this.init();
    }
    
    /**
     * 初始化图表
     */
    init() {
        // 检查数据
        if (!this.hasValidData()) {
            this.renderEmptyState();
            return;
        }
        
        // 处理数据
        const chartData = this.prepareChartData();
        
        // 渲染图表
        this.renderChart(chartData);
    }
    
    /**
     * 检查是否有有效数据
     */
    hasValidData() {
        if (!this.config.data || this.config.data.length === 0) {
            return false;
        }
        
        // 检查是否所有系列的数据都为空
        const hasData = this.config.series.some(series => {
            return this.config.data.some(item => {
                const value = item[series.key];
                return value !== null && value !== undefined && value !== 0;
            });
        });
        
        return hasData;
    }
    
    /**
     * 渲染空状态
     */
    renderEmptyState() {
        this.element.innerHTML = `
            <div class="alert alert-info text-center" style="height: ${this.config.height}px; display: flex; align-items: center; justify-content: center; margin: 0;">
                <div>
                    <i class="fas fa-chart-line fa-3x mb-3" style="opacity: 0.3;"></i>
                    <p class="mb-0">${this.config.emptyMessage}</p>
                </div>
            </div>
        `;
    }
    
    /**
     * 准备图表数据
     */
    prepareChartData() {
        const data = this.config.data;
        const dimension = this.config.dimension;
        
        // 生成X轴标签
        let categories;
        if (dimension === 'month') {
            // 月度数据：生成1-12月
            categories = Array.from({length: 12}, (_, i) => `${i + 1}月`);
        } else {
            // 年度数据：从数据中提取年份
            categories = [...new Set(data.map(item => item.year))].sort();
        }
        
        // 准备系列数据
        const seriesData = this.config.series.map(series => {
            const values = categories.map(category => {
                let dataItem;
                
                if (dimension === 'month') {
                    const month = parseInt(category);
                    dataItem = data.find(item => item.month === month);
                } else {
                    dataItem = data.find(item => item.year === category);
                }
                
                return dataItem ? (dataItem[series.key] || 0) : 0;
            });
            
            return {
                name: series.name,
                data: values,
                color: series.color
            };
        });
        
        return {
            categories,
            series: seriesData
        };
    }
    
    /**
     * 渲染图表
     */
    renderChart(chartData) {
        // 准备系列数据，包含数据系列和基准线系列
        const allSeries = [...chartData.series];
        
        // 添加基准线系列
        if (this.config.baselinesSeries && this.config.baselinesSeries.length > 0) {
            this.config.baselinesSeries.forEach(baseline => {
                allSeries.push({
                    name: baseline.name,
                    data: Array(chartData.categories.length).fill(baseline.value),
                    color: baseline.color || '#999',
                    type: 'line'
                });
            });
        }
        
        const options = {
            chart: {
                type: 'line',
                height: this.config.height,
                toolbar: {
                    show: this.config.enableZoom,
                    tools: {
                        download: true,
                        selection: true,
                        zoom: true,
                        zoomin: true,
                        zoomout: true,
                        pan: true,
                        reset: true
                    }
                },
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800
                }
            },
            series: allSeries,
            xaxis: {
                categories: chartData.categories,
                title: {
                    text: this.config.dimension === 'month' ? '月份' : '年份',
                    style: {
                        fontSize: '12px',
                        fontWeight: 500
                    }
                }
            },
            yaxis: {
                title: {
                    text: this.config.yAxisTitle || '数值',
                    style: {
                        fontSize: '12px',
                        fontWeight: 500
                    }
                },
                labels: {
                    formatter: this.config.yAxisFormatter || function(value) {
                        return Math.round(value);
                    }
                }
            },
            title: {
                text: this.config.title,
                align: 'left',
                style: {
                    fontSize: '16px',
                    fontWeight: 600
                }
            },
            subtitle: this.config.subtitle ? {
                text: this.config.subtitle,
                align: 'left',
                style: {
                    fontSize: '12px',
                    color: '#6c757d'
                }
            } : undefined,
            stroke: {
                curve: 'smooth',
                width: Array(allSeries.length).fill(0).map((_, idx) => {
                    // 基准线使用较细的线条
                    if (idx >= chartData.series.length) {
                        return 2;
                    }
                    return 3;
                }),
                dashArray: Array(allSeries.length).fill(0).map((_, idx) => {
                    // 基准线使用虚线
                    if (idx >= chartData.series.length) {
                        return 5;
                    }
                    return 0;
                })
            },
            markers: {
                size: Array(allSeries.length).fill(0).map((_, idx) => {
                    // 基准线不显示标记点
                    if (idx >= chartData.series.length) {
                        return 0;
                    }
                    return 5;
                }),
                hover: {
                    size: 7
                }
            },
            dataLabels: {
                enabled: this.config.showDataLabels,
                style: {
                    fontSize: '11px'
                },
                formatter: function(value) {
                    return Math.round(value);
                }
            },
            legend: {
                show: this.config.showLegend,
                position: 'top',
                horizontalAlign: 'right',
                fontSize: '12px',
                markers: {
                    width: 12,
                    height: 12,
                    radius: 2
                }
            },
            tooltip: {
                enabled: true,
                shared: true,
                intersect: false,
                y: this.config.tooltipFormatter ? {
                    formatter: this.config.tooltipFormatter
                } : {
                    formatter: function(value) {
                        return Math.round(value);
                    }
                }
            },
            grid: {
                borderColor: '#e7e7e7',
                strokeDashArray: 4,
                xaxis: {
                    lines: {
                        show: true
                    }
                }
            },
            colors: allSeries.map(s => s.color || '#4e73df')
        };
        
        // 销毁旧图表
        if (this.chart) {
            this.chart.destroy();
        }
        
        // 创建新图表
        this.chart = new ApexCharts(this.element, options);
        this.chart.render();
    }
    
    /**
     * 更新图表数据
     */
    updateData(newData) {
        this.config.data = newData;
        
        if (!this.hasValidData()) {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
            this.renderEmptyState();
            return;
        }
        
        const chartData = this.prepareChartData();
        
        if (this.chart) {
            this.chart.updateOptions({
                xaxis: {
                    categories: chartData.categories
                }
            });
            this.chart.updateSeries(chartData.series);
        } else {
            this.renderChart(chartData);
        }
    }
    
    /**
     * 更新配置
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        this.init();
    }
    
    /**
     * 销毁图表
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
}

// 导出到全局
window.TrendChart = TrendChart;