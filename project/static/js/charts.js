/**
 * 图表初始化和工具函数
 * 基于 Chart.js
 */

// 颜色配置
const CHART_COLORS = {
    primary: '#667eea',
    success: '#38ef7d',
    warning: '#f5576c',
    danger: '#fa709a',
    info: '#4facfe',
    secondary: '#6c757d',
};

const CHART_PALETTE = [
    '#667eea', '#764ba2', '#f093fb', '#f5576c',
    '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
    '#fa709a', '#fee140', '#30cfd0', '#330867'
];

/**
 * 创建饼图
 * @param {string} canvasId - Canvas元素ID
 * @param {Array} labels - 标签数组
 * @param {Array} data - 数据数组
 * @param {string} title - 图表标题
 */
function createPieChart(canvasId, labels, data, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }

    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: CHART_PALETTE,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: title !== '',
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            let value = context.parsed || 0;
                            let total = context.dataset.data.reduce((a, b) => a + b, 0);
                            let percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 创建环形图（用于归档率展示）
 * @param {string} canvasId - Canvas元素ID
 * @param {number} value - 完成百分比（0-100）
 * @param {string} label - 标签
 */
function createDoughnutChart(canvasId, value, label = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }

    const remaining = 100 - value;
    const color = value >= 90 ? CHART_COLORS.success : 
                  value >= 70 ? CHART_COLORS.warning : 
                  CHART_COLORS.danger;

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['已完成', '未完成'],
            datasets: [{
                data: [value, remaining],
                backgroundColor: [color, '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                title: {
                    display: label !== '',
                    text: label,
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 创建柱状图
 * @param {string} canvasId - Canvas元素ID
 * @param {Array} labels - 标签数组
 * @param {Array} datasets - 数据集数组
 * @param {string} title - 图表标题
 */
function createBarChart(canvasId, labels, datasets, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: title !== '',
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * 创建折线图
 * @param {string} canvasId - Canvas元素ID
 * @param {Array} labels - 标签数组
 * @param {Array} datasets - 数据集数组
 * @param {string} title - 图表标题
 */
function createLineChart(canvasId, labels, datasets, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: title !== '',
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * 格式化数字（添加千位分隔符）
 * @param {number} num - 数字
 * @returns {string} 格式化后的字符串
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * 格式化金额（元）
 * @param {number} amount - 金额
 * @returns {string} 格式化后的字符串
 */
function formatAmount(amount) {
    return formatNumber(amount.toFixed(2)) + ' 元';
}

/**
 * 更新进度环
 * @param {string} elementId - 元素ID
 * @param {number} percentage - 百分比（0-100）
 */
function updateProgressRing(elementId, percentage) {
    const circle = document.querySelector(`#${elementId} .progress-ring-value`);
    const text = document.querySelector(`#${elementId} .progress-ring-text`);
    
    if (!circle || !text) return;
    
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percentage / 100) * circumference;
    
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    circle.style.strokeDashoffset = offset;
    text.textContent = `${percentage}%`;
    
    // 根据百分比设置颜色
    if (percentage >= 90) {
        circle.style.stroke = CHART_COLORS.success;
    } else if (percentage >= 70) {
        circle.style.stroke = CHART_COLORS.warning;
    } else {
        circle.style.stroke = CHART_COLORS.danger;
    }
}