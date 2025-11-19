
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
    // 优化：增大散点的基础尺寸和热区，提升可点击性
    let markerSize = 10;  // 增大基础尺寸到10
    let hoverSize = 18;   // 悬停时的尺寸
    let hitRadius = 15;   // 点击热区半径
    
    if (personCount > 15) {
        markerSize = 9;
        hoverSize = 16;
        hitRadius = 14;
    }
    if (personCount > 25) {
        markerSize = 8;
        hoverSize = 14;
        hitRadius = 12;
    }
    
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
                size: seriesData.map(s => s.type === 'scatter' ? hoverSize : 0),  // 悬停时显著增大
                sizeOffset: 8  // 增大悬停偏移量，扩大热区
            },
            strokeWidth: 3,  // 增加描边宽度使散点更明显
            strokeOpacity: 1,
            fillOpacity: 0.95,
            // 增加透明边框作为隐形点击热区
            discrete: seriesData.map((s, idx) => {
                if (s.type === 'scatter') {
                    return {
                        seriesIndex: idx,
                        dataPointIndex: undefined, // 应用于所有点
                        fillColor: s.color,
                        strokeColor: s.color,
                        size: markerSize,
                        // 使用CSS样式增加点击区域
                        shape: 'circle'
                    };
                }
                return null;
            }).filter(Boolean)
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
            intersect: false,  // 改为false，不需要精确交叉，靠近即可显示
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
            // 优化：增加悬停延迟，让tooltip更容易保持显示
            hideDelay: 500,  // 增加延迟隐藏时间到500ms
            // 增大tooltip的触发范围
            inverseOrder: false,
            // 优化：增加触发距离阈值
            intersectThreshold: hitRadius,  // 使用hitRadius作为触发阈值
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
    
    // 交互增强：点击高亮功能 + 点击显示详情功能
    if (enableInteraction) {
        let selectedSeries = null;
        let clickedTooltipTimer = null;  // 点击tooltip的定时器
        
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
        
        // 添加数据点点击事件：点击散点后显示详细信息并驻停2秒
        config.chart.events.dataPointSelection = function(event, chartContext, config) {
            const { seriesIndex, dataPointIndex } = config;
            const series = chartContext.w.config.series[seriesIndex];
            
            // 只处理散点图类型
            if (series.type === 'scatter' && series.data[dataPointIndex]) {
                const point = series.data[dataPointIndex];
                const value = point.y;
                
                // 构建详细信息内容
                let detailHtml = '<div style="padding: 12px; min-width: 200px;">';
                detailHtml += `<div style="font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #333;">${series.name}</div>`;
                detailHtml += `<div style="border-top: 1px solid #e0e0e0; padding-top: 8px;">`;
                detailHtml += `<div style="margin-bottom: 6px;"><strong>周期天数:</strong> ${Math.round(value)}天</div>`;
                if (point.code) detailHtml += `<div style="margin-bottom: 6px;"><strong>编号:</strong> ${point.code}</div>`;
                if (point.name) detailHtml += `<div style="margin-bottom: 6px;"><strong>名称:</strong> ${point.name}</div>`;
                if (point.person) detailHtml += `<div style="margin-bottom: 6px;"><strong>经办人:</strong> ${point.person}</div>`;
                if (point.x) {
                    const date = new Date(point.x);
                    detailHtml += `<div style="margin-bottom: 6px;"><strong>时间:</strong> ${date.getFullYear()}年${date.getMonth()+1}月${date.getDate()}日</div>`;
                }
                detailHtml += `</div>`;
                detailHtml += `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; font-size: 11px; color: #666; text-align: center;">信息将在2秒后自动关闭</div>`;
                detailHtml += '</div>';
                
                // 创建或更新自定义tooltip
                showPersistentTooltip(chartContext, detailHtml, event);
                
                // 清除之前的定时器
                if (clickedTooltipTimer) {
                    clearTimeout(clickedTooltipTimer);
                }
                
                // 设置2秒后自动隐藏
                clickedTooltipTimer = setTimeout(() => {
                    hidePersistentTooltip();
                }, 2000);
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

// ==================== 持久化Tooltip功能 ====================

/**
 * 显示持久化的tooltip（点击后驻停）
 * @param {Object} chartContext - 图表上下文
 * @param {string} content - tooltip内容HTML
 * @param {Object} event - 点击事件对象
 */
function showPersistentTooltip(chartContext, content, event) {
    // 移除已存在的持久化tooltip
    hidePersistentTooltip();
    
    // 创建新的tooltip元素
    const tooltip = document.createElement('div');
    tooltip.id = 'persistent-scatter-tooltip';
    tooltip.className = 'apexcharts-tooltip apexcharts-theme-light';
    tooltip.style.cssText = `
        position: fixed;
        background: white;
        border: 1px solid #e3e3e3;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        pointer-events: auto;
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
    `;
    tooltip.innerHTML = content;
    
    // 添加到页面
    document.body.appendChild(tooltip);
    
    // 计算位置（避免超出屏幕）
    const rect = tooltip.getBoundingClientRect();
    let left = event.clientX + 15;
    let top = event.clientY - rect.height / 2;
    
    // 边界检查
    if (left + rect.width > window.innerWidth) {
        left = event.clientX - rect.width - 15;
    }
    if (top < 10) {
        top = 10;
    }
    if (top + rect.height > window.innerHeight - 10) {
        top = window.innerHeight - rect.height - 10;
    }
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
    
    // 淡入效果
    setTimeout(() => {
        tooltip.style.opacity = '1';
    }, 10);
    
    // 添加点击关闭功能
    tooltip.addEventListener('click', hidePersistentTooltip);
}

/**
 * 隐藏持久化的tooltip
 */
function hidePersistentTooltip() {
    const tooltip = document.getElementById('persistent-scatter-tooltip');
    if (tooltip) {
        tooltip.style.opacity = '0';
        setTimeout(() => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        }, 200);
    }
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