# modal-management Specification

## Purpose
TBD - created by archiving change fix-delete-modal-overlay. Update Purpose after archive.
## Requirements
### Requirement: 模态框单例管理
系统 MUST 在任意时刻只存在一个活动的模态框实例。

**ID**: REQ-MODAL-001
**优先级**: 高

#### Scenario: 打开新模态框时自动关闭旧模态框
**Given** 系统中已经存在一个打开的模态框  
**When** 调用 `CustomDialog` 的任何方法（alert/confirm/prompt）打开新模态框  
**Then** 旧模态框及其遮罩层应立即被完全移除  
**And** 新模态框应正常显示  
**And** 页面应只存在一个遮罩层

#### Scenario: 快速连续打开多个模态框
**Given** 用户快速连续触发多个模态框操作  
**When** 第二个模态框在第一个模态框关闭动画完成前被触发  
**Then** 第一个模态框应立即被强制关闭  
**And** 第二个模态框应正常显示  
**And** 不应出现遮罩层叠加

### Requirement: 立即关闭机制
模态框关闭时 MUST 立即移除 DOM 元素，SHALL NOT 使用延迟移除策略。

**ID**: REQ-MODAL-002
**优先级**: 高

#### Scenario: 调用关闭方法后立即移除
**Given** 一个打开的模态框  
**When** 调用 `_closeDialog()` 方法  
**Then** 模态框的 DOM 元素应立即从文档中移除  
**And** 遮罩层应立即从文档中移除  
**And** body 的 overflow 样式应恢复为默认值  
**And** 不应有任何延迟（setTimeout）

#### Scenario: 关闭动画不影响 DOM 移除
**Given** 模态框配置了淡出动画  
**When** 关闭模态框  
**Then** 可以设置 opacity 为 0 实现淡出效果  
**But** DOM 元素应立即移除，不等待动画完成

### Requirement: 强制清理机制
系统 MUST 提供强制清理所有模态框和遮罩层的方法，用于异常情况恢复。

**ID**: REQ-MODAL-003
**优先级**: 高

#### Scenario: 强制清理所有残留遮罩层
**Given** 页面中可能存在多个残留的遮罩层（异常情况）  
**When** 调用 `_forceCloseDialog()` 方法  
**Then** 所有 `.custom-dialog-overlay` 元素应被移除  
**And** `activeDialog` 状态应被重置为 null  
**And** body 的 overflow 样式应恢复  
**And** 所有相关的事件监听器应被移除

#### Scenario: 页面加载时自动清理
**Given** 页面刚加载完成  
**When** DOMContentLoaded 事件触发  
**Then** 应自动调用 `_forceCloseDialog()` 清理可能残留的遮罩层

### Requirement: ESC 键强制关闭
用户按下 ESC 键时 SHALL 强制关闭所有模态框。

**ID**: REQ-MODAL-004
**优先级**: 中

#### Scenario: 按 ESC 键关闭模态框
**Given** 一个或多个打开的模态框  
**When** 用户按下 ESC 键  
**Then** 所有模态框应被强制关闭  
**And** 所有遮罩层应被移除  
**And** 页面应恢复可操作状态

### Requirement: 删除操作的模态框流程
批量删除操作 MUST 遵循规范的模态框打开和关闭流程。

**ID**: REQ-MODAL-005
**优先级**: 高

#### Scenario: 删除成功后显示成功提示
**Given** 用户确认批量删除操作  
**When** 删除请求成功返回  
**Then** 确认模态框应完全关闭  
**And** 等待至少 50ms 确保 DOM 更新  
**And** 显示成功提示模态框  
**And** 用户关闭成功提示后页面应刷新

#### Scenario: 删除失败后显示错误提示
**Given** 用户确认批量删除操作  
**When** 删除请求失败（如权限不足、网络错误）  
**Then** 确认模态框应完全关闭  
**And** 等待至少 50ms 确保 DOM 更新  
**And** 显示错误提示模态框  
**And** 用户关闭错误提示后页面应保持当前状态  
**And** 删除按钮应恢复为可用状态

#### Scenario: 删除操作中断
**Given** 用户点击批量删除按钮  
**When** 用户在确认模态框中点击取消  
**Then** 确认模态框应关闭  
**And** 不应发送删除请求  
**And** 不应显示其他模态框  
**And** 页面应保持当前状态

### Requirement: 遮罩层点击行为
点击模态框外部的遮罩层 SHALL 关闭模态框（除非明确禁用）。

**ID**: REQ-MODAL-006
**优先级**: 中

#### Scenario: 点击遮罩层关闭模态框
**Given** 一个打开的模态框，且 `closeOnClickOutside` 未设置为 false  
**When** 用户点击遮罩层（模态框外部区域）  
**Then** 模态框应关闭  
**And** 遮罩层应被移除

#### Scenario: 点击模态框内容不关闭
**Given** 一个打开的模态框  
**When** 用户点击模态框内容区域  
**Then** 模态框应保持打开状态  
**And** 点击事件应被阻止冒泡

### Requirement: 状态恢复
模态框关闭后 MUST 正确恢复页面状态。

**ID**: REQ-MODAL-007
**优先级**: 中

#### Scenario: 恢复 body 滚动
**Given** 模态框打开时禁用了 body 滚动  
**When** 模态框关闭  
**Then** body 的 `overflow` 样式应恢复为空字符串  
**And** 页面应可以正常滚动

#### Scenario: 清理事件监听器
**Given** 模态框打开时添加了 ESC 键监听器  
**When** 模态框关闭  
**Then** 相关的事件监听器应被移除  
**And** 不应有内存泄漏

### Requirement: Promise 链式调用
模态框方法 MUST 返回 Promise，支持 async/await 语法。

**ID**: REQ-MODAL-008
**优先级**: 高

#### Scenario: 使用 async/await 顺序显示模态框
**Given** 需要顺序显示多个模态框  
**When** 使用 `await CustomDialog.confirm()` 和 `await CustomDialog.alert()`  
**Then** 第二个模态框应在第一个模态框关闭后才显示  
**And** 不应出现遮罩层叠加

#### Scenario: Promise 正确解析
**Given** 调用 `CustomDialog.confirm()`  
**When** 用户点击确认按钮  
**Then** Promise 应 resolve 为 true  
**When** 用户点击取消按钮  
**Then** Promise 应 resolve 为 false

