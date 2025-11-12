# 统一美化弹窗组件使用说明

## 概述

本项目已实现统一的美化弹窗组件，替代原生的 `alert()`、`confirm()` 和 `prompt()` 弹窗，提供更美观、更友好的用户体验。

## 特性

- ✨ 现代化紫色渐变设计
- 🎨 支持多种类型（info、success、warning、error）
- 📱 响应式设计，支持移动端
- ⌨️ 支持 ESC 键关闭
- 🔄 支持异步操作
- 🎯 自动替换原生 alert()
- 🛡️ 安全的输入验证

## 文件结构

```
project/static/
├── css/
│   └── custom-dialog.css          # 弹窗样式
└── js/
    ├── custom-dialog.js            # 弹窗核心功能
    └── dialog-polyfill.js          # 原生方法替换
```

## 基本用法

### 1. 警告弹窗（Alert）

```javascript
// 简单用法
CustomDialog.alert('操作成功！');

// 完整配置
CustomDialog.alert({
    title: '操作成功',
    message: '数据已保存',
    type: 'success',  // info, success, warning, error
    icon: 'fa-check-circle',
    confirmText: '确定'
});

// 使用 Promise
CustomDialog.alert('操作完成').then(() => {
    console.log('用户点击了确定');
});
```

### 2. 确认弹窗（Confirm）

```javascript
// 简单用法
const confirmed = await CustomDialog.confirm('确定要删除吗？');
if (confirmed) {
    // 用户点击了确定
}

// 完整配置
const result = await CustomDialog.confirm({
    title: '确认删除',
    message: '确定要删除这条记录吗？',
    warnings: [
        '此操作不可撤销',
        '相关数据也将被删除'
    ],
    type: 'warning',
    dangerButton: true,  // 使用危险按钮样式
    confirmText: '删除',
    cancelText: '取消'
});
```

### 3. 输入弹窗（Prompt）

```javascript
// 简单用法
const name = await CustomDialog.prompt('请输入您的姓名：');
if (name) {
    console.log('用户输入了：', name);
}

// 完整配置
const value = await CustomDialog.prompt({
    title: '重命名',
    message: '请输入新的文件名：',
    placeholder: '文件名',
    defaultValue: '旧文件名',
    inputType: 'text',  // text, password, email, number
    confirmText: '确定',
    cancelText: '取消'
});
```

## 高级用法

### 带信息列表的确认弹窗

```javascript
await CustomDialog.confirm({
    title: '确认恢复备份',
    subtitle: '此操作将覆盖当前数据库',
    message: '确定要恢复以下备份吗？',
    infoList: [
        { label: '备份文件', value: 'backup_20231112.sqlite3' },
        { label: '文件大小', value: '31.42 MB' },
        { label: '创建时间', value: '2023-11-12 10:59:30' }
    ],
    warnings: [
        '当前数据库将被完全覆盖',
        '此操作不可撤销',
        '所有未保存的数据将丢失'
    ],
    dangerButton: true,
    type: 'error',
    icon: 'fa-database'
});
```

### 表单提交确认

```javascript
// HTML
<form onsubmit="return false;" id="myForm">
    <!-- 表单内容 -->
</form>

// JavaScript
document.getElementById('myForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const confirmed = await confirmSubmit(e.target, {
        title: '确认提交',
        message: '确定要提交此表单吗？',
        warnings: ['提交后数据将被保存到数据库']
    });
    
    if (confirmed) {
        e.target.submit();
    }
});
```

### 删除操作确认

```javascript
async function deleteItem(id) {
    const confirmed = await confirmDelete({
        title: '确认删除',
        message: `确定要删除项目 #${id} 吗？`,
        warnings: [
            '此操作不可撤销',
            '相关的采购、合同、付款数据也将被删除'
        ]
    });
    
    if (confirmed) {
        // 执行删除操作
    }
}
```

## 配置选项

### Alert 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | string | '提示' | 弹窗标题 |
| message | string | '' | 弹窗内容 |
| type | string | 'info' | 类型：info/success/warning/error |
| icon | string | 自动 | Font Awesome 图标类名 |
| confirmText | string | '确定' | 确认按钮文本 |

### Confirm 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | string | '确认' | 弹窗标题 |
| subtitle | string | - | 副标题 |
| message | string | '' | 弹窗内容 |
| warnings | array | [] | 警告信息列表 |
| infoList | array | [] | 信息列表 [{label, value}] |
| type | string | 'warning' | 类型 |
| icon | string | 自动 | 图标 |
| dangerButton | boolean | false | 是否使用危险按钮样式 |
| confirmText | string | '确定' | 确认按钮文本 |
| cancelText | string | '取消' | 取消按钮文本 |

### Prompt 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | string | '输入' | 弹窗标题 |
| message | string | '' | 弹窗内容 |
| placeholder | string | '请输入...' | 输入框占位符 |
| defaultValue | string | '' | 默认值 |
| inputType | string | 'text' | 输入类型 |
| confirmText | string | '确定' | 确认按钮文本 |
| cancelText | string | '取消' | 取消按钮文本 |

## 样式定制

弹窗使用 CSS 变量，可以轻松定制：

```css
:root {
    --primary-color: #1890ff;
    --success-color: #52c41a;
    --warning-color: #faad14;
    --error-color: #ff4d4f;
}
```

## 兼容性说明

### 原生方法替换

- `alert()` - 已自动替换为美化版本
- `confirm()` - 建议使用 `CustomDialog.confirm()` 异步版本
- `prompt()` - 建议使用 `CustomDialog.prompt()` 异步版本

### 迁移指南

**旧代码：**
```javascript
if (confirm('确定要删除吗？')) {
    deleteItem();
}
```

**新代码：**
```javascript
const confirmed = await CustomDialog.confirm('确定要删除吗？');
if (confirmed) {
    deleteItem();
}
```

## 最佳实践

1. **使用异步版本**：优先使用 `CustomDialog.confirm()` 而不是原生 `confirm()`
2. **提供清晰的警告**：对于危险操作，使用 `warnings` 参数列出风险
3. **使用合适的类型**：根据操作性质选择 info/success/warning/error
4. **危险操作标识**：删除等危险操作使用 `dangerButton: true`
5. **提供详细信息**：使用 `infoList` 显示操作相关的详细信息

## 示例场景

### 数据库备份确认

```javascript
const confirmed = await CustomDialog.confirm({
    title: '创建数据库备份',
    message: '确定要创建数据库备份吗？',
    type: 'info',
    icon: 'fa-database'
});
```

### 数据导入警告

```javascript
const confirmed = await CustomDialog.confirm({
    title: '确认导入数据',
    message: `确定要导入数据到项目 "${projectCode}" 吗？`,
    warnings: [
        '该项目的所有现有数据将被清空',
        '此操作不可撤销',
        '请确保已备份数据库'
    ],
    dangerButton: true,
    type: 'warning'
});
```

### 操作成功提示

```javascript
CustomDialog.alert({
    title: '操作成功',
    message: '数据已成功保存',
    type: 'success'
}).then(() => {
    window.location.reload();
});
```

## 技术支持

如有问题或建议，请联系开发团队。

## 更新日志

### v1.0.0 (2024-11-12)
- ✨ 初始版本发布
- 🎨 紫色渐变主题设计
- 📱 响应式支持
- 🔄 异步操作支持
- 🛡️ 自动替换原生弹窗