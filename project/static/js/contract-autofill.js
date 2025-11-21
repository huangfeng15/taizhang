/**
 * 合同表单自动填充功能
 * 当选择关联采购项目后，自动填充合同相关字段
 */

(function() {
    'use strict';

    /**
     * 初始化合同自动填充功能
     */
    function initContractAutofill() {
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupAutofill);
        } else {
            setupAutofill();
        }
    }

    /**
     * 设置自动填充
     */
    function setupAutofill() {
        const form = document.getElementById('editForm');
        if (!form) {
            console.warn('未找到合同表单');
            return;
        }

        // 检查是否是合同模块
        const moduleType = form.dataset.module;
        if (moduleType !== 'contract') {
            return;
        }

        // 等待EditModal初始化完成
        waitForEditModal((editModal) => {
            // 获取采购项目选择器实例
            const procurementSelector = editModal.smartSelectors.procurement;
            if (!procurementSelector) {
                console.warn('未找到采购项目选择器实例');
                return;
            }

            // 保存原始的onChange回调
            const originalOnChange = procurementSelector.config.onChange;
            
            // 重写onChange回调以添加自动填充逻辑
            procurementSelector.config.onChange = function(value, text) {
                // 调用原始回调
                if (typeof originalOnChange === 'function') {
                    originalOnChange(value, text);
                }
                
                // 执行自动填充
                if (value) {
                    autofillFromProcurement(value);
                }
            };
        });
    }

    /**
     * 等待EditModal初始化完成
     */
    function waitForEditModal(callback) {
        const checkInterval = setInterval(() => {
            if (window.editModal && window.editModal.smartSelectors) {
                clearInterval(checkInterval);
                callback(window.editModal);
            }
        }, 100);

        // 10秒超时
        setTimeout(() => {
            clearInterval(checkInterval);
        }, 10000);
    }

    /**
     * 根据采购项目自动填充合同字段
     */
    async function autofillFromProcurement(procurementCode) {
        try {
            // 显示加载提示
            showLoadingIndicator();

            // 调用API获取采购项目详情
            const response = await fetch(`/api/procurements/${encodeURIComponent(procurementCode)}/detail/`);
            const result = await response.json();

            if (!result.success) {
                console.error('获取采购详情失败:', result.message);
                showNotification('获取采购详情失败: ' + result.message, 'error');
                return;
            }

            const procurementData = result.data;

            // 自动填充字段
            fillFormField('contract_name', procurementData.project_name, '合同名称');
            fillFormField('contract_type', procurementData.procurement_category, '合同类型');
            fillFormField('contract_source', '采购合同', '合同来源');
            fillFormField('party_a', procurementData.procurement_unit, '甲方');
            fillFormField('party_b', procurementData.winning_bidder, '乙方');
            fillFormField('contract_amount', procurementData.winning_amount, '含税签约合同价(元)');

            // 显示成功提示
            showNotification('已自动填充合同信息，请审核并根据需要修改', 'success');

        } catch (error) {
            console.error('自动填充失败:', error);
            showNotification('自动填充失败: ' + error.message, 'error');
        } finally {
            hideLoadingIndicator();
        }
    }

    /**
     * 填充表单字段
     */
    function fillFormField(fieldName, value, fieldLabel) {
        if (!value && value !== 0) {
            return;
        }

        const field = document.querySelector(`[name="${fieldName}"]`);
        if (!field) {
            console.warn(`未找到字段: ${fieldName}`);
            return;
        }

        // 根据字段类型设置值
        if (field.tagName === 'SELECT') {
            // 下拉框
            const option = Array.from(field.options).find(opt => opt.value === value || opt.text === value);
            if (option) {
                field.value = option.value;
                // 触发change事件
                field.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                console.warn(`下拉框 ${fieldName} 中未找到匹配项: ${value}`);
            }
        } else if (field.type === 'number') {
            // 数字输入框
            field.value = value;
            field.dispatchEvent(new Event('input', { bubbles: true }));
        } else {
            // 普通文本输入框
            field.value = value;
            field.dispatchEvent(new Event('input', { bubbles: true }));
        }

        // 添加视觉提示
        highlightField(field, fieldLabel);
    }

    /**
     * 高亮显示已填充的字段
     */
    function highlightField(field, fieldLabel) {
        const fieldContainer = field.closest('.mb-3');
        if (fieldContainer) {
            // 添加高亮类
            fieldContainer.classList.add('autofilled');
            
            // 3秒后移除高亮
            setTimeout(() => {
                fieldContainer.classList.remove('autofilled');
            }, 3000);
        }
    }

    /**
     * 显示加载指示器
     */
    function showLoadingIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'autofill-loading';
        indicator.className = 'autofill-loading';
        indicator.innerHTML = `
            <div class="autofill-loading-content">
                <div class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <span style="margin-left: 10px;">正在自动填充...</span>
            </div>
        `;
        document.body.appendChild(indicator);
    }

    /**
     * 隐藏加载指示器
     */
    function hideLoadingIndicator() {
        const indicator = document.getElementById('autofill-loading');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * 显示通知消息
     */
    function showNotification(message, type = 'info') {
        // 使用Bootstrap Alert或自定义通知
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show autofill-notification`;
        notification.setAttribute('role', 'alert');
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // 插入到表单顶部
        const form = document.getElementById('editForm');
        if (form) {
            form.insertBefore(notification, form.firstChild);
        } else {
            document.body.insertBefore(notification, document.body.firstChild);
        }

        // 5秒后自动关闭
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 150);
        }, 5000);
    }

    // 初始化
    initContractAutofill();

})();