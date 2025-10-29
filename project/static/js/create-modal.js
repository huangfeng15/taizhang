
/**
 * 通用新增模态框管理器
 * 用于处理所有"新增"操作的模态框显示和提交
 */

(function() {
    'use strict';

    // 等待 DOM 加载完成
    document.addEventListener('DOMContentLoaded', function() {
        // 为所有带有 data-create-url 属性的按钮添加事件监听
        document.addEventListener('click', function(e) {
            const button = e.target.closest('[data-create-url]');
            if (button) {
                e.preventDefault();
                const createUrl = button.getAttribute('data-create-url');
                const title = button.getAttribute('data-title') || '新增记录';
                openCreateModal(createUrl, title);
            }
        });
    });

    /**
     *