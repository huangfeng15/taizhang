window.AdvancedFilter = {
            // 显示高级筛选弹窗
            showAdvancedFilter: function(fields, currentFilters = {}) {
                const html = `
                    <div id="advancedFilterModal" class="modal-overlay" onclick="AdvancedFilter.closeModal(event)">
                        <div class="modal-content" onclick="event.stopPropagation()">
                            <div class="modal-header">
                                <h3 style="font-size: 20px; font-weight: 600;">高级筛选</h3>
                                <button onclick="AdvancedFilter.closeModal()" style="background: none; border: none; font-size: 24px; color: var(--text-secondary); cursor: pointer;">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <div class="modal-body">
                                <form id="advancedFilterForm">
                                    ${fields.map(field => this.renderFilterField(field, currentFilters[field.name])).join('')}
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" onclick="AdvancedFilter.resetFilters()" class="btn btn-secondary">
                                    <i class="fas fa-undo"></i> 重置
                                </button>
                                <button type="button" onclick="AdvancedFilter.closeModal()" class="btn btn-secondary">取消</button>
                                <button type="button" onclick="AdvancedFilter.applyFilters()" class="btn btn-primary">
                                    <i class="fas fa-filter"></i> 应用筛选
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', html);
            },

            // 渲染筛选字段
            renderFilterField: function(field, currentValue) {
                // 获取URL参数用于回显
                const urlParams = new URLSearchParams(window.location.search);
                
                let inputHtml = '';
                if (field.type === 'select') {
                    inputHtml = `
                        <select name="${field.name}" class="form-input" style="max-width: 300px; white-space: normal; height: auto; min-height: 38px;">
                            <option value="">全部</option>
                            ${field.options.map(opt => `
                                <option value="${opt.value}" ${currentValue === opt.value ? 'selected' : ''}>
                                    ${opt.label}
                                </option>
                            `).join('')}
                        </select>
                    `;
                } else if (field.type === 'date') {
                    inputHtml = `<input type="date" name="${field.name}" class="form-input" value="${currentValue || ''}">`;
                } else if (field.type === 'daterange') {
                    // 从URL获取日期范围的开始和结束值
                    const startValue = urlParams.get(`${field.name}_start`) || '';
                    const endValue = urlParams.get(`${field.name}_end`) || '';
                    inputHtml = `
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <input type="date" name="${field.name}_start" class="form-input" placeholder="开始日期" value="${startValue}">
                            <span>至</span>
                            <input type="date" name="${field.name}_end" class="form-input" placeholder="结束日期" value="${endValue}">
                        </div>
                    `;
                } else if (field.type === 'number') {
                    // 从URL获取数字范围的最小和最大值
                    const minValue = urlParams.get(`${field.name}_min`) || '';
                    const maxValue = urlParams.get(`${field.name}_max`) || '';
                    inputHtml = `
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <input type="number" name="${field.name}_min" class="form-input" placeholder="最小值" step="0.01" value="${minValue}">
                            <span>至</span>
                            <input type="number" name="${field.name}_max" class="form-input" placeholder="最大值" step="0.01" value="${maxValue}">
                        </div>
                    `;
                } else {
                    inputHtml = `<input type="text" name="${field.name}" class="form-input" value="${currentValue || ''}" placeholder="${field.placeholder || ''}">`;
                }

                return `
                    <div class="form-group" style="max-width: 100%;">
                        <label class="form-label">${field.label}</label>
                        <div style="max-width: 100%;">
                            ${inputHtml}
                        </div>
                    </div>
                `;
            },

            // 应用筛选
            applyFilters: function() {
                const form = document.getElementById('advancedFilterForm');
                if (!form) {
                    console.error('找不到筛选表单');
                    return;
                }
                
                const formData = new FormData(form);
                const url = new URL(window.location.href);
                
                // 保留现有的q和project等基础筛选参数
                const baseParams = ['q', 'project', 'status', 'contract', 'contract_type'];
                const preservedParams = {};
                baseParams.forEach(param => {
                    const value = url.searchParams.get(param);
                    if (value) preservedParams[param] = value;
                });
                
                // 清除所有参数
                url.search = '';
                
                // 重置到第一页
                url.searchParams.set('page', '1');
                
                // 恢复基础筛选参数
                Object.keys(preservedParams).forEach(key => {
                    url.searchParams.set(key, preservedParams[key]);
                });
                
                // 添加新的高级筛选参数
                for (const [key, value] of formData.entries()) {
                    // 正确处理空值：检查是否为空字符串或仅包含空格
                    if (value !== null && value !== undefined && String(value).trim() !== '') {
                        url.searchParams.set(key, value);
                    }
                }
                
                // 关闭弹窗并跳转
                this.closeModal();
                window.location.href = url.toString();
            },

            // 重置筛选
            resetFilters: function() {
                const url = new URL(window.location.href);
                url.search = '';
                window.location.href = url.toString();
            },

            // 关闭弹窗
            closeModal: function(event) {
                if (event && event.target.id !== 'advancedFilterModal') return;
                const modal = document.getElementById('advancedFilterModal');
                if (modal) modal.remove();
            }
        };