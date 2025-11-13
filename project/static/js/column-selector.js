window.ColumnSelector = {
            defaultColumns: [],
            availableColumns: [],
            storageKey: '',

            // 初始化字段选择器
            init: function(availableColumns, defaultColumns, storageKey) {
                this.availableColumns = availableColumns;
                this.defaultColumns = defaultColumns;
                this.storageKey = storageKey;
                this.loadColumnSettings();
            },

            // 显示字段选择弹窗
            showColumnSelector: function() {
                const selectedColumns = this.getSelectedColumns();
                const html = `
                    <div id="columnSelectorModal" class="modal-overlay" onclick="ColumnSelector.closeModal(event)">
                        <div class="modal-content" onclick="event.stopPropagation()">
                            <div class="modal-header">
                                <h3 style="font-size: 20px; font-weight: 600;">选择显示字段</h3>
                                <button onclick="ColumnSelector.closeModal()" style="background: none; border: none; font-size: 24px; color: var(--text-secondary); cursor: pointer;">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <div class="modal-body">
                                <div class="column-selector">
                                    ${this.availableColumns.map(col => `
                                        <label class="column-item">
                                            <input type="checkbox"
                                                   value="${col.key}"
                                                   ${selectedColumns.includes(col.key) ? 'checked' : ''}
                                                   ${col.required ? 'disabled' : ''}>
                                            <span>${col.label}${col.required ? ' (必选)' : ''}</span>
                                        </label>
                                    `).join('')}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" onclick="ColumnSelector.resetColumns()" class="btn btn-secondary">
                                    <i class="fas fa-undo"></i> 恢复默认
                                </button>
                                <button type="button" onclick="ColumnSelector.closeModal()" class="btn btn-secondary">取消</button>
                                <button type="button" onclick="ColumnSelector.applyColumns()" class="btn btn-primary">
                                    <i class="fas fa-check"></i> 确定
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', html);
            },

            // 获取选中的字段
            getSelectedColumns: function() {
                const saved = localStorage.getItem(this.storageKey);
                if (saved) {
                    return JSON.parse(saved);
                }
                return this.defaultColumns;
            },

            // 应用字段选择
            applyColumns: function() {
                const modal = document.getElementById('columnSelectorModal');
                const checkboxes = modal.querySelectorAll('input[type="checkbox"]:not([disabled])');
                const selected = Array.from(checkboxes)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value);
                
                // 添加必选字段
                const requiredColumns = this.availableColumns
                    .filter(col => col.required)
                    .map(col => col.key);
                const allSelected = [...new Set([...requiredColumns, ...selected])];
                
                localStorage.setItem(this.storageKey, JSON.stringify(allSelected));
                this.closeModal();
                window.location.reload();
            },

            // 重置为默认字段
            resetColumns: function() {
                localStorage.removeItem(this.storageKey);
                this.closeModal();
                window.location.reload();
            },

            // 加载字段设置并更新表格
            loadColumnSettings: function() {
                const selectedColumns = this.getSelectedColumns();
                const table = document.querySelector('.data-table');
                if (!table) return;

                // 隐藏未选中的列（通过data-column属性匹配）
                this.availableColumns.forEach(col => {
                    if (!selectedColumns.includes(col.key)) {
                        // 隐藏表头
                        const th = table.querySelector(`thead th[data-column="${col.key}"]`);
                        if (th) th.style.display = 'none';
                        
                        // 隐藏所有行的对应单元格
                        table.querySelectorAll(`tbody td[data-column="${col.key}"]`).forEach(td => {
                            td.style.display = 'none';
                        });
                    }
                });
            },

            // 获取列索引
            getColumnIndex: function(key) {
                return this.availableColumns.findIndex(col => col.key === key);
            },

            // 关闭弹窗
            closeModal: function(event) {
                if (event && event.target.id !== 'columnSelectorModal') return;
                const modal = document.getElementById('columnSelectorModal');
                if (modal) modal.remove();
            }
        };