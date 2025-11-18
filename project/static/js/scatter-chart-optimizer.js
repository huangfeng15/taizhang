
/**
 * 散点图优化器 - 用于归档监控和更新监控页面的个人视图散点图
 * 
 * 主要功能：
 * 1. 高对比度颜色方案，支持多人数据区分
 * 2. 自适应图例布局（多行多列显示）
 * 3. 交互功能（悬停提示、点击高亮、图例筛选）
 * 4. 自适应字体和图标大小
 * 5. 图例分页/滚动功能（备选方案）
 */

// ==================== 高对比度颜色方案 ====================
// 30种高对比度颜色，适合多人数据场景
const SCATTER_COLOR_PALETTE = [
    '#0d6efd', // 蓝色
    '#dc3545', // 红色
    '#198754', // 绿色
    '#fd7e14', // 橙色
    '#6f42c1', // 紫色
    '#20c997', // 青绿色
    '#d63384', // 粉红色
    '#0dcaf0', // 天蓝色
    '#ffc107', // 黄色
    '#6610f2', // 靛蓝色
    '#e83e8c', // 洋红色
    '#17a2b8', // 青色
    '#28a745', // 草绿色
    '#ff6b6b', // 珊瑚红
    '#4ecdc4', // 薄荷色
    '#95e1d3', // 浅绿色
    '#f38181', // 淡红色
    '#aa96da', // 淡紫色
    '#fcbad3', // 粉色
    '#ffffd2', // 淡黄色
    '#a8d8ea', // 浅蓝色
    '#ffcfdf', // 樱花粉
    '#fefdca', // 米黄色
    '#e0f9b5', // 嫩绿色
    '#a5dee5', // 浅青色
    '#ffb6b9', // 蜜桃色
    '#fae3d9', // 杏色
    '#bbded6', // 薄荷绿
    '#61c0bf', // 松石绿
    '#f4a261'  // 杏橙色
];

/**
 * 根据人员数量获取优化的颜色方案
 * @param {number} count - 人员数量
 * @returns {Array<string>} 颜色数组
 */
function getOptimizedColors(count) {
    if (count <= SCATTER_COLOR_PALETTE.length) {
        return SCATTER_COLOR_PALETTE.slice(0, count);
    }
    
    // 如果人数超过预定义颜色数量，生成额外颜色
    const colors = [...SCATTER_COLOR_PALETTE];
    const additionalNeeded = count - SCATTER_COLOR_PALETTE.length;
    
    for (let i = 0; i < additionalNeeded; i++) {
        // 使用HSL生成不同色调的颜色
        const hue = (i * 137.508) % 360; // 黄金角度分布
        const saturation = 65 + (i % 3) * 10; // 65-85%
        const lightness = 50 + (i % 4) * 5; // 50-65%
        colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
    }
    
    return colors;
}

// ==================== 图例优化配置 ====================

/**
 * 计算图例的最佳布局配置
 * @param {number} itemCount - 图例项数量
 * @param {number} containerWidth - 容器宽度
 * @returns {Object} 布局配置
 */
function calculateLegendLayout(itemCount, containerWidth) {
    const config = {
        fontSize: 12,
        itemGap: 15,
        itemWidth: 12,
        itemHeight: 12,
        formatter: null,
        grid: null,
        maxRows: 3,
        useScroll: false
    };
    
    // 估算每个图例项的宽度（图标 + 间距 + 文本）
    const avgNameLength = 6; // 平均名字长度
    const estimatedItemWidth = config.itemWidth + config.itemGap + (avgNameLength * config.fontSize);
    
    // 计算每行可容纳的项数
    const itemsPerRow = Math.floor(containerWidth / estimatedItemWidth);
    const rows = Math.ceil(itemCount / itemsPerRow);
    
    // 根据人数和行数调整策略
    if (itemCount <= 10) {
        // 少量人员：使用标准单行或双行布局
        config.fontSize = 13;
        config.itemWidth = 12;
        config.itemHeight = 12;
    } else if (itemCount <= 20) {
        // 中等人员：使用紧凑的多行布局
        config.fontSize = 11;
        config.itemWidth = 10;
        config.itemHeight = 10;
        config.itemGap = 12;
        config.grid = {
            left: 10,
            right: 10,
            top: 5,
            bottom: 5,
            itemWidth: config.itemWidth,
            itemHeight: config.itemHeight,
            itemGap: config.itemGap
        };
    } else if (itemCount <= 30) {
        // 较多人员：使用更紧凑布局 + 名称缩写
        config.fontSize = 10;
        config.itemWidth = 8;
        config.itemHeight = 8;
        config.itemGap = 10;
        config.formatter = function(name) {
            return name.length > 4 ? name.substring(0, 4) + '...' : name;
        };
        config.grid = {
            left: 5,
            right: 5,
            top: 3,
            bottom: 3,
            itemWidth: config.itemWidth,
            itemHeight: config.itemHeight,
            itemGap: config.itemGap
        };
    } else {
        // 大量人员：启用滚动功能
        config.fontSize = 10;
        config.itemWidth = 8;
        config.itemHeight = 8;
        config.itemGap = 8;
        config.useScroll = true;
        config.maxRows = 3;
        config.formatter = function(name) {
            return name.length > 3 ? name.substring(0, 3) + '...' : name;
        };
    }
    
    return config;
}

// ==================== ApexCharts 散点图优化配置生成器 ====================

/**
 * 生成优化的散点图配置（用于归档监控和更新监控个人视图）
 * @param {Object} params - 配置参数
 * @returns {Object} ApexCharts配置对象
 */
function generateOptimizedScatterConfig(params) {
    const {
        seriesData,          // 系列数据数组
        title,               // 图表标题
        yAxisTitle,          // Y轴标题
        baselineValue,       // 基准线值
        baselineName,        // 基准线名称
        containerWidth = 1200, // 容器宽度
        enableInteraction = true // 是否启用交互功能
    } = params;
    
    const personCount = seriesData.filter(s => s.type === 'scatter').length;
    const colors = getOptimizedColors(personCount);
    const legendConfig = calculateLegendLayout(personCount, containerWidth);
    
    // 计算散点大小（人数越多，点越小，但保持最小可交互尺寸）
    let markerSize = 8;  // 增大基础尺寸
    if (personCount > 15) markerSize = 7;
    if (personCount > 25) markerSize = 6;
    
    // 基础配置
    const config = {
        chart: {
            type: 'line',
            height: 450, // 增加图表高度以容纳更多图例行
            toolbar: { 
                show: true,
                tools: {
                    download: true,
                    selection: enableInteraction,
                    zoom: enableInteraction,
                    zoomin: enableInteraction,
                    zoomout: enableInteraction,
                    pan: enableInteraction,
                    reset: enableInteraction
                }
            },
            zoom: { 
                enabled: enableInteraction,
                type: 'xy'
            },
            animations: {
                enabled: true,
                speed: 800
            },
            events: {}
        },
        series: seriesData,
        xaxis: {
            type: 'datetime',
            title: { 
                text: '时间',
                style: { fontSize: '14px', fontWeight: 600 }
            },
            labels: {
                format: 'yyyy年MM月',
                style: { fontSize: '12px' }
            }
        },
        yaxis: {
            title: { 
                text: yAxisTitle,
                style: { fontSize: '14px', fontWeight: 600 }
            },
            labels: {
                formatter: function(value) {
                    return value ? Math.round(value) + '天' : '';
                },
                style: { fontSize: '12px' }
            }
        },
        title: {
            text: title,
            align: 'left',
            style: { 
                fontSize: '16px', 
                fontWeight: 600,
                color: '#333'
            }
        },
        stroke: {
            width: seriesData.map(s => s.type === 'line' ? 3 : 0),
            dashArray: seriesData.map(s => s.type === 'line' ? 5 : 0)
        },
        markers: {
            size: seriesData.map(s => s.type === 'scatter' ? markerSize : 0),
            hover: {
                size: seriesData.map(s => s.type === 'scatter' ? markerSize + 6 : 0),  // 悬停时显著增大
                sizeOffset: 6  // 增大悬停偏移量
            },
            strokeWidth: 2,  // 添加描边使散点更明显
            strokeOpacity: 0.9,
            fillOpacity: 0.9
        },
        dataLabels: {
            enabled: false
        },
        legend: {
            show: true,
            position: 'bottom',
            horizontalAlign: 'center',
            floating: false,
            fontSize: `${legendConfig.fontSize}px`,
            fontWeight: 500,
            markers: {
                width: legendConfig.itemWidth,
                height: legendConfig.itemHeight,
                radius: 2
            },
            itemMargin: {
                horizontal: legendConfig.itemGap,
                vertical: 8
            },
            onItemClick: {
                toggleDataSeries: enableInteraction
            },
            onItemHover: {
                highlightDataSeries: enableInteraction
            }
        },
        tooltip: {
            enabled: true,
            shared: false,
            intersect: true,  // 必须精确交叉才显示tooltip
            followCursor: false,  // 不跟随鼠标，固定在数据点附近
            custom: undefined,  // 使用默认tooltip
            fillSeriesColor: false,
            theme: 'light',
            style: {
                fontSize: '13px'
            },
            onDatasetHover: {
                highlightDataSeries: true  // 悬停时高亮整个系列
            },
            marker: {
                show: true  // 在tooltip中显示标记
            },
            x: {
                format: 'yyyy年MM月dd日'
            },
            y: {
                formatter: function(value, { seriesIndex, dataPointIndex, w }) {
                    const series = w.config.series[seriesIndex];
                    if (series.type === 'scatter' && series.data[dataPointIndex]) {
                        const point = series.data[dataPointIndex];
                        let tooltip = `<strong>${Math.round(value)}天</strong>`;
                        if (point.code) tooltip += `<br/>编号: ${point.code}`;
                        if (point.name) tooltip += `<br/>名称: ${point.name}`;
                        if (point.person) tooltip += `<br/>经办人: ${point.person}`;
                        return tooltip;
                    }
                    return value !== null && value !== undefined ? Math.round(value) + '天' : '无数据';
                }
            },
            style: {
                fontSize: '13px'
            }
        },
        colors: colors,
        grid: {
            borderColor: '#e7e7e7',
            strokeDashArray: 4,
            padding: {
                top: 0,
                right: 30,
                bottom: 0,
                left: 10
            }
        }
    };
    
    // 如果需要滚动功能
    if (legendConfig.useScroll) {
        config.legend.height = legendConfig.maxRows * 30; // 限制图例高度
        config.legend.containerMargin = {
            top: 20,
            bottom: 20
        };
        // ApexCharts不原生支持图例滚动，需要在渲染后手动处理
        config.chart.events.mounted = function(chartContext, config) {
            addLegendScrollSupport(chartContext);
        };
    }
    
    // 名称格式化
    if (legendConfig.formatter) {
        config.legend.formatter = legendConfig.formatter;
    }
    
    // 交互增强：点击高亮功能
    if (enableInteraction) {
        let selectedSeries = null;
        
        config.chart.events.legendClick = function(chartContext, seriesIndex, config) {
            if (selectedSeries === seriesIndex) {
                // 取消选中，显示所有系列
                selectedSeries = null;
                chartContext.updateOptions({
                    chart: {
                        opacity: 1
                    }
                });
            } else {
                // 选中某个系列，淡化其他系列
                selectedSeries = seriesIndex;
                const seriesCount = config.config.series.length;
                const opacities = Array(seriesCount).fill(0.3);
                opacities[seriesIndex] = 1;
                
                chartContext.updateOptions({
                    fill: {
                        opacity: opacities
                    },
                    stroke: {
                        opacity: opacities
                    }
                });
            }
        };
    }
    
    return config;
}

/**
 * 为图例添加滚动支持（当人数过多时）
 * @param {Object} chartContext - ApexCharts实例
 */
function addLegendScrollSupport(chartContext) {
    setTimeout(() => {
        const legendEl = chartContext.el.querySelector('.apexcharts-legend');
        if (!legendEl) return;
        
        // 添加滚动样式
        legendEl.style.maxHeight = '120px';
        legendEl.style.overflowY = 'auto';
        legendEl.style.overflowX = 'hidden';
        legendEl.style.padding = '10px';
        
        // 添加自定义滚动条样式
        const style = document.createElement('style');
        style.textContent = `
            .apexcharts-legend::-webkit-scrollbar {
                width: 8px;
            }
            .apexcharts-legend::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 4px;
            }
            .apexcharts-legend::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 4px;
            }
            .apexcharts-legend::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
        `;
        document.head.appendChild(style);
    }, 100);
}

// ==================== 响应式调整 ====================

/**
 * 监听窗口大小变化，动态调整图表配置
 * @param {ApexCharts} chart - 图表实例
 * @param {Object} params - 原始参数
 */
function makeChartResponsive(chart, params) {
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const containerWidth = chart.el.offsetWidth;
            const newConfig = generateOptimizedScatterConfig({
                ...params,
                containerWidth
            });
            
            // 更新图例配置
            chart.updateOptions({
                legend: newConfig.legend,
                markers: newConfig.markers
            }, false, true);
        }, 300);
    });
}

// ==================== 导出供外部使用 ====================
window.ScatterChartOptimizer = {
    getOptimizedColors,
    calculateLegendLayout,
    generateOptimizedScatterConfig,
    makeChartResponsive
};