/**
 * 通用编辑模态框处理脚本
 * 提供前端编辑功能，替代Django Admin界面
 */

class EditModal {
    constructor() {
        this.modal = null;
        this.modalElement = null;
        this.init();
    }

    init() {
        // 创建模态框容器
        this.createModalContainer();
        
        // 绑定编辑按钮点击事件
        this.bindEditButtons();
    }

    createModalContainer() {
        // 检查是否已存在模态框
        if (document.getElementById('editModal')) {
            return;
        }

        // 创建模态框HTML
        const modalHTML = `
            <div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="editModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="editModalLabel">编辑信息</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                        </div>
                        <div class="modal-body" id="editModalBody">
                            <div class="text-center py-5">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">加载中...</span>
                                </div>
                                <p class="mt-3 text-muted">正在加载表单...</p>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" id="saveBtn" onclick="submitEditForm()">保存</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // 初始化Bootstrap模态框
        this.modalElement = document.getElementById('editModal');
        this.modal = new bootstrap.Modal(this.modalElement);

        // 模态框关闭时清理内容
        this.modalElement.addEventListener('hidden.bs.modal', () => {
            document.getElementById('editModalBody').innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p class="mt-3 text-muted">正在加载表单...</p>
                </div>
            `;
        });
    }

    bindEditButtons() {
        // 使用事件委托处理动态添加的编辑/新增按钮
        document.addEventListener('click', (e) => {
            // 处理编辑按钮
            const editBtn = e.target.closest('[data-edit-url]');
            if (editBtn) {
                e.preventDefault();
                const editUrl = editBtn.dataset.editUrl;
                const title = editBtn.dataset.title || '编辑信息';
                this.loadForm(editUrl, title);
                return;
            }
            
            // 处理新增按钮
            const createBtn = e.target.closest('[data-create-url]');
            if (createBtn) {
                e.preventDefault();
                const createUrl = createBtn.dataset.createUrl;
                const title = createBtn.dataset.title || '新增记录';
                this.loadForm(createUrl, title);
            }
        });
    }

    async loadForm(url, title = '编辑信息') {
        try {
            // 更新模态框标题
            document.getElementById('editModalLabel').textContent = title;
            
            // 显示模态框
            this.modal.show();

            // 加载表单
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }

            const html = await response.text();
            document.getElementById('editModalBody').innerHTML = html;

            // 绑定保存按钮点击事件（使用全局函数）
            window.submitEditForm = () => this.submitForm();

        } catch (error) {
            console.error('加载表单失败:', error);
            this.showError('加载表单失败，请稍后重试');
        }
    }

    async submitForm() {
        const form = document.getElementById('editForm');
        if (!form) {
            this.showError('表单未加载，请重试');
            return;
        }

        const formData = new FormData(form);
        const submitUrl = form.action;

        try {
            // 禁用提交按钮
            const submitBtn = document.getElementById('saveBtn');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中...';

            const response = await fetch(submitUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                // 成功提示
                this.showSuccess(data.message || '保存成功');
                
                // 关闭模态框
                this.modal.hide();

                // 刷新页面以显示更新后的数据
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                // 显示详细的错误信息
                let errorMessage = data.message || '保存失败';
                
                // 如果有字段级别的错误，在表单中高亮显示
                if (data.field_errors) {
                    this.highlightFieldErrors(data.field_errors);
                }
                
                // 显示错误提示（支持多行）
                this.showError(errorMessage);
                
                // 重新启用提交按钮
                submitBtn.disabled = false;
                submitBtn.innerHTML = '保存';
            }

        } catch (error) {
            console.error('提交表单失败:', error);
            this.showError('提交失败，请稍后重试');
            
            // 重新启用提交按钮
            const submitBtn = document.getElementById('saveBtn');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '保存';
            }
        }
    }

    highlightFieldErrors(fieldErrors) {
        // 清除之前的错误高亮
        document.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
        document.querySelectorAll('.invalid-feedback').forEach(el => {
            el.remove();
        });

        // 为每个有错误的字段添加高亮和错误提示
        for (const [fieldName, errors] of Object.entries(fieldErrors)) {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                // 添加错误样式
                field.classList.add('is-invalid');
                
                // 创建错误提示元素
                const errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback d-block';
                errorDiv.innerHTML = errors.join('<br>');
                
                // 插入错误提示
                field.parentNode.appendChild(errorDiv);
            }
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        // 将换行符转换为HTML
        const htmlMessage = message.replace(/\n/g, '<br>');
        this.showToast(htmlMessage, 'danger');
    }

    showToast(message, type = 'info') {
        // 创建Toast容器（如果不存在）
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // 创建Toast
        const toastId = 'toast-' + Date.now();
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true" style="max-width: 500px;">
                <div class="d-flex">
                    <div class="toast-body" style="white-space: pre-wrap;">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="关闭"></button>
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHTML);

        // 显示Toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: type === 'danger' ? 5000 : 3000  // 错误提示显示更长时间
        });
        toast.show();

        // Toast隐藏后移除元素
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new EditModal();
});