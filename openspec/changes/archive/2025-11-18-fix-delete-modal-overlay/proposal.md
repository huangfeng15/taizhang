# 修复删除确认模态框遮罩层问题

## Why

当前实现中，用户点击批量删除按钮后：
1. 首先弹出确认删除的模态框（CustomDialog.confirm）
2. 用户确认后，如果删除失败（如权限不足或关联数据未删除），会再弹出错误提示模态框（CustomDialog.alert）
3. 此时原有的确认模态框遮罩层未正确关闭，导致出现透明遮罩层叠加
4. 用户无法点击页面上的任何元素，必须刷新页面才能恢复

**根本原因**: `CustomDialog._closeDialog()` 方法在关闭模态框时使用了延迟移除DOM的策略（200ms延迟），但在快速连续弹出多个模态框时，前一个模态框的遮罩层还未完全移除，新的模态框就已经显示，导致遮罩层叠加。

## What Changes

### 核心修改

**1. 修改 `project/static/js/custom-dialog.js`**
- 新增 `_forceCloseDialog()` 方法：强制清理所有残留遮罩层
- 修改 `_showDialog()` 方法：在显示新模态框前强制清理旧模态框
- 修改 `_closeDialog()` 方法：立即移除DOM而非使用200ms延迟
- 新增页面加载时自动清理机制
- 新增ESC键全局监听，可强制关闭所有模态框

**2. 修改 `project/templates/base.html`**
- 修改 `BatchOperations.batchDelete()` 方法
- 在确认后添加50ms延迟，确保确认框完全关闭
- 使用 async/await 确保模态框按顺序显示
- 优化错误处理流程

### 规范变更

新增 `specs/modal-management` 规范，定义以下需求：
- REQ-MODAL-001: 模态框单例管理
- REQ-MODAL-002: 立即关闭机制
- REQ-MODAL-003: 强制清理机制
- REQ-MODAL-004: ESC键强制关闭
- REQ-MODAL-005: 删除操作的模态框流程
- REQ-MODAL-006: 遮罩层点击行为
- REQ-MODAL-007: 状态恢复
- REQ-MODAL-008: Promise链式调用

## 影响范围
- 采购列表页面（procurement_list.html）
- 合同列表页面（contract_list.html）
- 付款列表页面（payment_list.html）
- 项目列表页面（project_list.html）
- CustomDialog 组件（custom-dialog.js）
- base.html 中的批量删除逻辑

## 优先级
高 - 影响用户体验，导致页面无法操作

## 相关文件
- `project/static/js/custom-dialog.js` - 模态框组件
- `project/templates/base.html` - 批量删除逻辑
- `project/templates/procurement_list.html` - 采购列表
- `project/templates/contract_list.html` - 合同列表
- `project/templates/payment_list.html` - 付款列表
- `project/templates/project_list.html` - 项目列表