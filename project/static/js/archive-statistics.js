/**
 * 归档统计功能
 * 负责视图切换、目标选择、趋势图渲染
 */
class ArchiveStatistics {
    constructor(options) {
        this.viewMode = options.viewMode || 'project';
        this.targetCode = options.targetCode || '';
        this.showAll = options.showAll || false;
        this.trendData = options.trendData || { procurement: [], contract: [] };
        this.chart = null;

        this.init();
    }

    init() {
        this.bindViewModeSwitch();
        this.bindTargetSelector();
        this.bindShowAllCheckbox();
        this.initProjectSelector();
        this.renderTrendChart();
    }

    /**
     * 绑定视图模式切换
     */
    bindViewModeSwitch() {
        const buttons = document.querySelectorAll('.view-mode-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                this.switchViewMode(mode);
            });
        });
    }

    /**
     * 切换视图模式
     */
    switchViewMode(mode) {
        if (mode === this.viewMode) return;

        const url = new URL(window.location.href);
        url.searchParams.set('view_mode', mode);
        url.searchParams.delete('target_code'); // 清空目标选择
        window.location.href = url.toString();
    }

    /**
     * 绑定目标选择器
     */
    bindTargetSelector() {
        const selector = document.getElementById('targetSelect');
        if (!selector) return;

        selector.addEventListener('change', (e) => {
            const targetCode = e.target.value;
            this.updateTargetCode(targetCode);
        });
    }

    /**
     * 更新目标编码
     */
    updateTargetCode(targetCode) {
        const url = new URL(window.location.href);
        if (targetCode) {
            url.searchParams.set('target_code', targetCode);
        } else {
            url.searchParams.delete('target_code');
        }
        window.location.href = url.toString();
    }

    /**
     * 绑定"显示所有记录"复选框
     */
    bindShowAllCheckbox() {
        const checkbox = document.getElementById('showAllCheck');
        if (!checkbox) return;

        checkbox.addEventListener('change', (e) => {
            const url = new URL(window.location.href);
            if (e.target.checked) {
                url.searchParams.set('show_all', 'true');
            } else {
                url.searchParams.delete('show_all');
            }
            window.location.href = url.toString();
        });
    }

    /**
     * 初始化项目选择器（智能选择器）
     */
    initProjectSelector() {
        if (this.viewMode !== 'project') return;

        const selector = document.getElementById('targetSelect');
        if (!selector) return;

        // 使用智能选择器（如果已加载）
        if (typeof SmartSelector !== 'undefined') {
            this.initSmartProjectSelector(selector);
        } else {
            // 降级方案：使用简单的项目API
            this.loadProjectOptions(selector);
        }
    }

    /**
     * 初始化智能项目选择器
     */
    initSmartProjectSelector(selector) {
        // 获取全局筛选的年份
        const urlParams = new URLSearchParams(window.location.search);
        const globalYear = urlParams.get('global_year') || 'all';

        // 构建API URL
        let apiUrl = '/api/projects/';
        if (globalYear !== 'all') {
            apiUrl += `?year=${globalYear}`;
        }

        // 初始化智能选择器
        new SmartSelector(selector, {
            apiUrl: apiUrl,
            valueField: 'project_code',
            labelField: 'project_name',
            searchFields: ['project_code', 'project_name'],
            placeholder: '请选择项目',
            initialValue: this.targetCode
        });
    }

    /**
     * 加载项目选项（降级方案）
     */
    async loadProjectOptions(selector) {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const globalYear = urlParams.get('global_year') || 'all';

            let apiUrl = '/api/projects/';
            if (globalYear !== 'all') {
                apiUrl += `?year=${globalYear}`;
            }

            const response = await fetch(apiUrl);
            const projects = await response.json();

            // 清空现有选项
            selector.innerHTML = '<option value="">请选择项目</option>';

            // 添加项目选项
            projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.project_code;
                option.textContent = `${project.project_code} - ${project.project_name}`;
                if (project.project_code === this.targetCode) {
                    option.selected = true;
                }
                selector.appendChild(option);
            });
        } catch (error) {
            console.error('加载项目列表失败:', error);
        }
    }

    /**
     * 渲染趋势图
     */
    renderTrendChart() {
        const canvas = document.getElementById('trendChart');
        if (!canvas || !this.trendData) return;

        // 提取数据
        const procurementData = this.trendData.procurement || [];
        const contractData = this.trendData.contract || [];

        if (procurementData.length === 0 && contractData.length === 0) {
            canvas.parentElement.innerHTML = '<p class="text-center text-muted py-5">暂无趋势数据</p>';
            return;
        }

        // 提取标签（时间周期）
        const labels = procurementData.map(item => item.period);

        // 提取数值
        const procurementValues = procurementData.map(item => item.avg_cycle);
        const contractValues = contractData.map(item => item.avg_cycle);

        // 销毁旧图表
        if (this.chart) {
            this.chart.destroy();
        }

        // 创建图表
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '采购归档周期',
                        data: procurementValues,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        spanGaps: true // 跳过null值
                    },
                    {
                        label: '合同归档周期',
                        data: contractValues,
                        borderColor: '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y + ' 天';
                                } else {
                                    label += '无数据';
                                }
                                return label;
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            procurementDeadline: {
                                type: 'line',
                                yMin: 40,
                                yMax: 40,
                                borderColor: 'rgba(13, 110, 253, 0.5)',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    display: true,
                                    content: '采购规定周期 (40天)',
                                    position: 'end',
                                    backgroundColor: 'rgba(13, 110, 253, 0.8)',
                                    color: 'white',
                                    font: {
                                        size: 10
                                    }
                                }
                            },
                            contractDeadline: {
                                type: 'line',
                                yMin: 30,
                                yMax: 30,
                                borderColor: 'rgba(25, 135, 84, 0.5)',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    display: true,
                                    content: '合同规定周期 (30天)',
                                    position: 'start',
                                    backgroundColor: 'rgba(25, 135, 84, 0.8)',
                                    color: 'white',
                                    font: {
                                        size: 10
                                    }
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '时间周期'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '平均归档周期（天）'
                        },
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    /**
     * 销毁实例
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// 导出到全局
window.ArchiveStatistics = ArchiveStatistics;
