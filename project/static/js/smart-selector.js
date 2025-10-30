/**
 * 智能选择器组件
 * 提供带搜索、分页和级联筛选功能的下拉选择器
 */

class SmartSelector {
    constructor(config) {
        this.config = {
            container: null,           // 容器元素
            apiUrl: '',               // API地址
            placeholder: '请选择',    // 占位符
            searchPlaceholder: '搜索...', // 搜索占位符
            displayField: 'display_text', // 显示字段
            valueField: 'id',        // 值字段
            cascadeFilters: {},      // 级联筛选参数
            onChange: null,          // 值变更回调
            pageSize: 20,            // 每页数量
            ...config
        };
        
        this.currentPage = 1;
        this.totalPages = 1;
        this.searchTimeout = null;
        this.searchQuery = '';
        this.selectedValue = null;
        this.selectedText = '';
        this.isOpen = false;
        this.items = [];
        
        this.init();
    }
    
    init() {
        this.createElements();
        this.bindEvents();
    }
    
    createElements() {
        const container = this.config.container;
        container.classList.add('smart-selector');
        
        // 创建选择器UI
        container.innerHTML = `
            <div class="smart-selector-trigger">
                <span class="smart-selector-value">${this.config.placeholder}</span>
                <i class="smart-selector-arrow">▼</i>
            </div>
            <div class="smart-selector-dropdown" style="display: none;">
                <div class="smart-selector-search">
                    <input type="text" 
                           class="smart-selector-search-input" 
                           placeholder="${this.config.searchPlaceholder}">
                </div>
                <div class="smart-selector-list"></div>
                <div class="smart-selector-pagination">
                    <button class="smart-selector-prev" disabled>上一页</button>
                    <span class="smart-selector-page-info">第 1 页</span>
                    <button class="smart-selector-next" disabled>下一页</button>
                </div>
                <div class="smart-selector-loading" style="display: none;">
                    加载中...
                </div>
            </div>
        `;
        
        // 缓存DOM元素
        this.trigger = container.querySelector('.smart-selector-trigger');
        this.valueDisplay = container.querySelector('.smart-selector-value');
        this.dropdown = container.querySelector('.smart-selector-dropdown');
        this.searchInput = container.querySelector('.smart-selector-search-input');
        this.listContainer = container.querySelector('.smart-selector-list');
        this.prevBtn = container.querySelector('.smart-selector-prev');
        this.nextBtn = container.querySelector('.smart-selector-next');
        this.pageInfo = container.querySelector('.smart-selector-page-info');
        this.loading = container.querySelector('.smart-selector-loading');
    }
    
    bindEvents() {
        // 点击触发器打开/关闭下拉框
        this.trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });
        
        // 搜索输入
        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchQuery = e.target.value;
                this.currentPage = 1;
                this.loadData();
            }, 300);
        });
        
        // 分页按钮
        this.prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadData();
            }
        });
        
        this.nextBtn.addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.loadData();
            }
        });
        
        // 点击外部关闭下拉框
        document.addEventListener('click', (e) => {
            if (!this.config.container.contains(e.target)) {
                this.close();
            }
        });
        
        // 列表项点击事件委托
        this.listContainer.addEventListener('click', (e) => {
            const item = e.target.closest('.smart-selector-item');
            if (item) {
                const value = item.dataset.value;
                const text = item.dataset.text;
                this.select(value, text);
            }
        });
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.isOpen = true;
        this.dropdown.style.display = 'block';
        this.searchInput.value = '';
        this.searchQuery = '';
        this.currentPage = 1;
        this.loadData();
        this.searchInput.focus();
    }
    
    close() {
        this.isOpen = false;
        this.dropdown.style.display = 'none';
    }
    
    async loadData() {
        this.showLoading();
        
        try {
            // 构建请求参数
            const params = new URLSearchParams({
                page: this.currentPage,
                page_size: this.config.pageSize,
                search: this.searchQuery,
                ...this.config.cascadeFilters
            });
            
            const response = await fetch(`${this.config.apiUrl}?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.items = result.data;
                this.totalPages = result.pagination.total_pages;
                this.renderList();
                this.updatePagination();
            } else {
                console.error('加载数据失败:', result.message);
                this.showError(result.message);
            }
        } catch (error) {
            console.error('请求失败:', error);
            this.showError('加载数据失败，请重试');
        } finally {
            this.hideLoading();
        }
    }
    
    renderList() {
        if (this.items.length === 0) {
            this.listContainer.innerHTML = '<div class="smart-selector-empty">暂无数据</div>';
            return;
        }
        
        const html = this.items.map(item => {
            const value = item[this.config.valueField];
            const text = item[this.config.displayField];
            const isSelected = value === this.selectedValue ? 'selected' : '';
            
            return `
                <div class="smart-selector-item ${isSelected}" 
                     data-value="${this.escapeHtml(value)}" 
                     data-text="${this.escapeHtml(text)}">
                    ${this.escapeHtml(text)}
                </div>
            `;
        }).join('');
        
        this.listContainer.innerHTML = html;
    }
    
    updatePagination() {
        this.prevBtn.disabled = this.currentPage <= 1;
        this.nextBtn.disabled = this.currentPage >= this.totalPages;
        this.pageInfo.textContent = `第 ${this.currentPage} / ${this.totalPages} 页`;
    }
    
    select(value, text) {
        this.selectedValue = value;
        this.selectedText = text;
        this.valueDisplay.textContent = text;
        this.valueDisplay.classList.remove('placeholder');
        this.close();
        
        // 触发变更回调
        if (typeof this.config.onChange === 'function') {
            this.config.onChange(value, text);
        }
    }
    
    setValue(value, text) {
        this.selectedValue = value;
        this.selectedText = text;
        if (text) {
            this.valueDisplay.textContent = text;
            this.valueDisplay.classList.remove('placeholder');
        } else {
            this.valueDisplay.textContent = this.config.placeholder;
            this.valueDisplay.classList.add('placeholder');
        }
    }
    
    getValue() {
        return this.selectedValue;
    }
    
    getText() {
        return this.selectedText;
    }
    
    clear() {
        this.setValue(null, '');
    }
    
    updateCascadeFilters(filters) {
        this.config.cascadeFilters = { ...filters };
        if (this.isOpen) {
            this.currentPage = 1;
            this.loadData();
        }
    }
    
    showLoading() {
        this.loading.style.display = 'block';
        this.listContainer.style.opacity = '0.5';
    }
    
    hideLoading() {
        this.loading.style.display = 'none';
        this.listContainer.style.opacity = '1';
    }
    
    showError(message) {
        this.listContainer.innerHTML = `<div class="smart-selector-error">${this.escapeHtml(message)}</div>`;
    }
    
    escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    destroy() {
        // 清理事件监听器和DOM
        this.config.container.innerHTML = '';
        this.config.container.classList.remove('smart-selector');
    }
}

// 导出到全局
window.SmartSelector = SmartSelector;