/**
 * 统一美化弹窗组件
 * 替代原生的 alert(), confirm(), prompt()
 */

(function(window) {
    'use strict';

    // 弹窗管理器
    const CustomDialog = {
        // 当前活动的弹窗
        activeDialog: null,

        /**
         * 显示警告弹窗（替代 alert）
         * @param {string|object} options - 消息文本或配置对象
         * @returns {Promise<void>}
         */
        alert: function(options) {
            return new Promise((resolve) => {
                const config = typeof options === 'string' ? { message: options } : options;
                
                const defaultConfig = {
                    title: '提示',
                    message: '',
                    type: 'info', // info, success, warning, error
                    confirmText: '确定',
                    icon: 'fa-info-circle'
                };

                const finalConfig = { ...defaultConfig, ...config };

                // 根据类型设置默认图标
                if (!config.icon) {
                    const iconMap = {
                        info: 'fa-info-circle',
                        success: 'fa-check-circle',
                        warning: 'fa-exclamation-triangle',
                        error: 'fa-times-circle'
                    };
                    finalConfig.icon = iconMap[finalConfig.type] || 'fa-info-circle';
                }

                this._showDialog({
                    ...finalConfig,
                    buttons: [
                        {
                            text: finalConfig.confirmText,
                            className: 'custom-dialog-btn-confirm',
                            onClick: () => {
                                this._closeDialog();
                                resolve();
                            }
                        }
                    ]
                });
            });
        },

        /**
         * 显示确认弹窗（替代 confirm）
         * @param {string|object} options - 消息文本或配置对象
         * @returns {Promise<boolean>}
         */
        confirm: function(options) {
            return new Promise((resolve) => {
                const config = typeof options === 'string' ? { message: options } : options;
                
                const defaultConfig = {
                    title: '确认',
                    message: '',
                    type: 'warning',
                    confirmText: '确定',
                    cancelText: '取消',
                    icon: 'fa-exclamation-triangle',
                    dangerButton: false // 是否使用危险按钮样式
                };

                const finalConfig = { ...defaultConfig, ...config };

                this._showDialog({
                    ...finalConfig,
                    buttons: [
                        {
                            text: finalConfig.cancelText,
                            className: 'custom-dialog-btn-cancel',
                            onClick: () => {
                                this._closeDialog();
                                resolve(false);
                            }
                        },
                        {
                            text: finalConfig.confirmText,
                            className: finalConfig.dangerButton ? 'custom-dialog-btn-danger' : 'custom-dialog-btn-confirm',
                            onClick: () => {
                                this._closeDialog();
                                resolve(true);
                            }
                        }
                    ]
                });
            });
        },

        /**
         * 显示输入弹窗（替代 prompt）
         * @param {string|object} options - 消息文本或配置对象
         * @returns {Promise<string|null>}
         */
        prompt: function(options) {
            return new Promise((resolve) => {
                const config = typeof options === 'string' ? { message: options } : options;
                
                const defaultConfig = {
                    title: '输入',
                    message: '',
                    type: 'info',
                    confirmText: '确定',
                    cancelText: '取消',
                    icon: 'fa-edit',
                    placeholder: '请输入...',
                    defaultValue: '',
                    inputType: 'text'
                };

                const finalConfig = { ...defaultConfig, ...config };

                // 添加输入框到消息中
                const inputId = 'custom-dialog-input-' + Date.now();
                const messageWithInput = `
                    <div class="custom-dialog-message">${finalConfig.message}</div>
                    <input type="${finalConfig.inputType}" 
                           id="${inputId}" 
                           class="custom-dialog-input" 
                           placeholder="${finalConfig.placeholder}"
                           value="${finalConfig.defaultValue}">
                `;

                this._showDialog({
                    ...finalConfig,
                    message: messageWithInput,
                    buttons: [
                        {
                            text: finalConfig.cancelText,
                            className: 'custom-dialog-btn-cancel',
                            onClick: () => {
                                this._closeDialog();
                                resolve(null);
                            }
                        },
                        {
                            text: finalConfig.confirmText,
                            className: 'custom-dialog-btn-confirm',
                            onClick: () => {
                                const input = document.getElementById(inputId);
                                const value = input ? input.value : '';
                                this._closeDialog();
                                resolve(value);
                            }
                        }
                    ]
                });

                // 聚焦输入框
                setTimeout(() => {
                    const input = document.getElementById(inputId);
                    if (input) {
                        input.focus();
                        input.select();
                    }
                }, 100);
            });
        },

        /**
         * 强制关闭所有模态框（防御性清理）
         * 用于处理异常情况，确保页面可操作
         */
        _forceCloseDialog: function() {
            // 移除所有可能残留的遮罩层
            const overlays = document.querySelectorAll('.custom-dialog-overlay');
            overlays.forEach(overlay => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            });
            
            // 重置状态
            this.activeDialog = null;
            document.body.style.overflow = '';
        },
    
        /**
         * 显示自定义弹窗
         * @param {object} config - 配置对象
         */
        _showDialog: function(config) {
            // 强制关闭所有旧模态框，确保不会出现遮罩层叠加
            this._forceCloseDialog();
            
            // 短暂延迟确保 DOM 更新完成
            setTimeout(() => {
                this._createDialog(config);
            }, 10);
        },
    
        /**
         * 创建并显示模态框
         * @param {object} config - 配置对象
         */
        _createDialog: function(config) {

                // 创建遮罩层
                const overlay = document.createElement('div');
            overlay.className = 'custom-dialog-overlay';
            overlay.onclick = (e) => {
                if (e.target === overlay && config.closeOnClickOutside !== false) {
                    this._closeDialog();
                }
            };

            // 创建弹窗
            const dialog = document.createElement('div');
            dialog.className = 'custom-dialog';

            // 创建头部
            const header = document.createElement('div');
            header.className = 'custom-dialog-header';
            
            const iconDiv = document.createElement('div');
            iconDiv.className = `custom-dialog-icon ${config.type}`;
            iconDiv.innerHTML = `<i class="fas ${config.icon}"></i>`;
            
            const titleArea = document.createElement('div');
            titleArea.className = 'custom-dialog-title-area';
            
            const title = document.createElement('h3');
            title.className = 'custom-dialog-title';
            title.textContent = config.title;
            titleArea.appendChild(title);
            
            if (config.subtitle) {
                const subtitle = document.createElement('div');
                subtitle.className = 'custom-dialog-subtitle';
                subtitle.textContent = config.subtitle;
                titleArea.appendChild(subtitle);
            }
            
            header.appendChild(iconDiv);
            header.appendChild(titleArea);

            // 创建内容
            const body = document.createElement('div');
            body.className = 'custom-dialog-body';
            
            if (typeof config.message === 'string') {
                body.innerHTML = config.message;
            } else {
                body.appendChild(config.message);
            }

            // 如果有警告信息
            if (config.warnings && config.warnings.length > 0) {
                const warningBox = document.createElement('div');
                warningBox.className = 'custom-dialog-warning-box';
                
                const warningTitle = document.createElement('div');
                warningTitle.className = 'warning-title';
                warningTitle.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 警告：';
                warningBox.appendChild(warningTitle);
                
                const warningList = document.createElement('ul');
                config.warnings.forEach(warning => {
                    const li = document.createElement('li');
                    li.textContent = warning;
                    warningList.appendChild(li);
                });
                warningBox.appendChild(warningList);
                
                body.appendChild(warningBox);
            }

            // 如果有信息列表
            if (config.infoList && config.infoList.length > 0) {
                const infoListDiv = document.createElement('div');
                infoListDiv.className = 'custom-dialog-info-list';
                
                config.infoList.forEach(info => {
                    const item = document.createElement('div');
                    item.className = 'custom-dialog-info-item';
                    
                    const label = document.createElement('div');
                    label.className = 'custom-dialog-info-label';
                    label.textContent = info.label + '：';
                    
                    const value = document.createElement('div');
                    value.className = 'custom-dialog-info-value';
                    value.textContent = info.value;
                    
                    item.appendChild(label);
                    item.appendChild(value);
                    infoListDiv.appendChild(item);
                });
                
                body.appendChild(infoListDiv);
            }

            // 创建底部按钮
            const footer = document.createElement('div');
            footer.className = 'custom-dialog-footer';
            
            config.buttons.forEach(btnConfig => {
                const btn = document.createElement('button');
                btn.className = `custom-dialog-btn ${btnConfig.className}`;
                btn.textContent = btnConfig.text;
                btn.onclick = btnConfig.onClick;
                footer.appendChild(btn);
            });

            // 组装弹窗
            dialog.appendChild(header);
            dialog.appendChild(body);
            dialog.appendChild(footer);
            overlay.appendChild(dialog);

            // 添加到页面
            document.body.appendChild(overlay);
            this.activeDialog = overlay;

            // 阻止body滚动
            document.body.style.overflow = 'hidden';

            // ESC键关闭
            const escHandler = (e) => {
                if (e.key === 'Escape' && config.closeOnEscape !== false) {
                    this._closeDialog();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);
        },

        /**
         * 关闭当前弹窗（立即移除，不延迟）
         */
        _closeDialog: function() {
            if (this.activeDialog) {
                // 可以保留淡出效果，但立即移除 DOM
                this.activeDialog.style.opacity = '0';
                
                // 立即移除，不使用延迟
                if (this.activeDialog.parentNode) {
                    this.activeDialog.parentNode.removeChild(this.activeDialog);
                }
                
                this.activeDialog = null;
                document.body.style.overflow = '';
            }
        }
    };

    // 导出到全局
    window.CustomDialog = CustomDialog;

    // 提供简化的全局函数（可选）
    window.showAlert = function(options) {
        return CustomDialog.alert(options);
    };

    window.showConfirm = function(options) {
        return CustomDialog.confirm(options);
    };

    window.showPrompt = function(options) {
    // 页面加载时清理可能残留的遮罩层
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            CustomDialog._forceCloseDialog();
        });
    } else {
        // 如果脚本加载时 DOM 已经就绪，立即清理
        CustomDialog._forceCloseDialog();
    }

    // ESC 键强制关闭所有模态框（全局监听）
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && CustomDialog.activeDialog) {
            CustomDialog._forceCloseDialog();
        }
    });
        return CustomDialog.prompt(options);
    };

})(window);