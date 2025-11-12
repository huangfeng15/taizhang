/**
 * 弹窗替换辅助脚本
 * 自动将页面中的原生 alert/confirm 替换为美化弹窗
 */

(function() {
    'use strict';

    // 等待 CustomDialog 加载完成
    function waitForCustomDialog(callback) {
        if (typeof CustomDialog !== 'undefined') {
            callback();
        } else {
            setTimeout(() => waitForCustomDialog(callback), 50);
        }
    }

    waitForCustomDialog(function() {
        // 保存原生方法的引用
        const nativeAlert = window.alert;
        const nativeConfirm = window.confirm;
        const nativePrompt = window.prompt;

        // 替换 window.alert
        window.alert = function(message) {
            // 如果 CustomDialog 不可用，回退到原生方法
            if (typeof CustomDialog === 'undefined') {
                return nativeAlert.call(window, message);
            }

            return CustomDialog.alert({
                message: String(message),
                type: 'info'
            });
        };

        // 替换 window.confirm
        window.confirm = function(message) {
            // 如果 CustomDialog 不可用，回退到原生方法
            if (typeof CustomDialog === 'undefined') {
                return nativeConfirm.call(window, message);
            }

            // 由于 confirm 是同步的，但 CustomDialog.confirm 是异步的
            // 我们需要返回一个 Promise，但这会破坏现有代码
            // 所以我们提供一个警告，建议使用异步版本
            console.warn('使用同步 confirm() 已被弃用，请使用 CustomDialog.confirm() 的异步版本');
            
            // 对于同步调用，我们暂时回退到原生方法
            // 开发者应该逐步迁移到异步版本
            return nativeConfirm.call(window, message);
        };

        // 替换 window.prompt
        window.prompt = function(message, defaultValue) {
            // 如果 CustomDialog 不可用，回退到原生方法
            if (typeof CustomDialog === 'undefined') {
                return nativePrompt.call(window, message, defaultValue);
            }

            console.warn('使用同步 prompt() 已被弃用，请使用 CustomDialog.prompt() 的异步版本');
            
            // 对于同步调用，我们暂时回退到原生方法
            return nativePrompt.call(window, message, defaultValue);
        };

        // 提供便捷的异步方法别名
        window.showAlert = window.showAlert || function(options) {
            return CustomDialog.alert(options);
        };

        window.showConfirm = window.showConfirm || function(options) {
            return CustomDialog.confirm(options);
        };

        window.showPrompt = window.showPrompt || function(options) {
            return CustomDialog.prompt(options);
        };

        console.log('✓ 弹窗组件已加载，原生 alert() 已被美化版本替换');
        console.log('提示：对于 confirm() 和 prompt()，建议使用异步版本 CustomDialog.confirm() 和 CustomDialog.prompt()');
    });

    // 为表单的 onsubmit 提供辅助函数
    window.confirmSubmit = async function(form, options) {
        const defaultOptions = {
            title: '确认提交',
            message: '确定要提交此表单吗？',
            type: 'warning'
        };
        
        const finalOptions = typeof options === 'string' 
            ? { ...defaultOptions, message: options }
            : { ...defaultOptions, ...options };

        const confirmed = await CustomDialog.confirm(finalOptions);
        if (confirmed && form) {
            form.submit();
        }
        return confirmed;
    };

    // 为删除操作提供辅助函数
    window.confirmDelete = async function(options) {
        const defaultOptions = {
            title: '确认删除',
            message: '确定要删除吗？',
            warnings: ['此操作不可撤销'],
            dangerButton: true,
            type: 'warning'
        };
        
        const finalOptions = typeof options === 'string'
            ? { ...defaultOptions, message: options }
            : { ...defaultOptions, ...options };

        return await CustomDialog.confirm(finalOptions);
    };

})();