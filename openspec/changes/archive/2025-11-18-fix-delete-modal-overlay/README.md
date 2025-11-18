# 修复删除确认模态框遮罩层问题

## 变更ID
`fix-delete-modal-overlay`

## 状态
🔴 待实施 (Pending)

## 概述
修复采购、合同、付款、项目列表页面在批量删除操作失败时，模态框遮罩层叠加导致页面无法操作的问题。

## 问题描述
当用户执行批量删除操作时：
1. 首先显示确认删除的模态框
2. 用户确认后，如果删除失败（如权限不足、网络错误）
3. 系统会弹出错误提示模态框
4. **问题**：此时原有确认模态框的遮罩层未正确关闭，导致两个遮罩层叠加
5. 用户无法点击页面上的任何元素，必须刷新页面才能恢复

## 根本原因
- `CustomDialog._closeDialog()` 使用 200ms 延迟移除 DOM
- 快速连续弹出模态框时，旧遮罩层未完全移除就创建了新遮罩层
- 缺少强制清理机制来处理异常情况

## 解决方案
1. **立即关闭机制**：移除延迟，立即清理 DOM
2. **强制清理方法**：添加 `_forceCloseDialog()` 清理所有残留遮罩层
3. **Promise 链式调用**：确保模态框按顺序打开和关闭
4. **防御性编程**：页面加载时自动清理，ESC 键强制关闭

## 影响范围
- ✅ `project/static/js/custom-dialog.js` - 核心模态框组件
- ✅ `project/templates/base.html` - 批量删除逻辑
- ✅ `project/templates/procurement_list.html` - 采购列表
- ✅ `project/templates/contract_list.html` - 合同列表
- ✅ `project/templates/payment_list.html` - 付款列表
- ✅ `project/templates/project_list.html` - 项目列表

## 文档结构
```
fix-delete-modal-overlay/
├── README.md                           # 本文件
├── proposal.md                         # 提案概述
├── tasks.md                            # 任务清单
├── design.md                           # 详细设计文档
└── specs/
    └── modal-management/
        └── spec.md                     # 模态框管理规范
```

## 快速开始

### 1. 查看提案
```bash
cat openspec/changes/fix-delete-modal-overlay/proposal.md
```

### 2. 查看任务清单
```bash
cat openspec/changes/fix-delete-modal-overlay/tasks.md
```

### 3. 查看设计文档
```bash
cat openspec/changes/fix-delete-modal-overlay/design.md
```

### 4. 查看规范文档
```bash
cat openspec/changes/fix-delete-modal-overlay/specs/modal-management/spec.md
```

## 实施步骤

### 第一步：修改 CustomDialog 组件
修改 `project/static/js/custom-dialog.js`：

```javascript
// 添加强制清理方法
_forceCloseDialog: function() {
    const overlays = document.querySelectorAll('.custom-dialog-overlay');
    overlays.forEach(overlay => {
        if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    });
    this.activeDialog = null;
    document.body.style.overflow = '';
}

// 修改关闭方法（立即移除）
_closeDialog: function() {
    if (this.activeDialog) {
        if (this.activeDialog.parentNode) {
            this.activeDialog.parentNode.removeChild(this.activeDialog);
        }
        this.activeDialog = null;
        document.body.style.overflow = '';
    }
}

// 修改显示方法（先强制清理）
_showDialog: function(config) {
    this._forceCloseDialog();
    setTimeout(() => {
        // 创建新模态框...
    }, 10);
}
```

### 第二步：修改批量删除逻辑
修改 `project/templates/base.html` 中的 `BatchOperations.batchDelete()`：

```javascript
batchDelete: async function(apiUrl, confirmMessage) {
    // ... 前置检查
    
    const confirmed = await CustomDialog.confirm({...});
    if (!confirmed) return;
    
    // 关键：等待确认框完全关闭
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // ... 执行删除
    
    // 失败时显示错误
    await CustomDialog.alert({
        title: '删除失败',
        message: error.message,
        type: 'error'
    });
}
```

### 第三步：测试验证
1. 测试正常删除流程
2. 测试删除失败场景（权限不足）
3. 测试快速连续操作
4. 测试 ESC 键关闭
5. 测试不同浏览器

## 验收标准
- [ ] 删除失败时错误提示正常显示
- [ ] 关闭错误提示后页面可以正常操作
- [ ] 不会出现透明遮罩层残留
- [ ] 快速连续操作不会导致遮罩层叠加
- [ ] ESC 键可以关闭任何模态框
- [ ] 所有列表页面的删除功能正常

## 优先级
🔴 **高** - 影响用户体验，导致页面无法操作

## 预计工作量
- 开发：2-3 小时
- 测试：1-2 小时
- 总计：3-5 小时

## 风险评估
- **低风险**：改动集中在模态框组件，影响范围可控
- **向后兼容**：不破坏现有功能
- **易于回滚**：可以快速恢复到原始版本

## 相关链接
- [CustomDialog 组件](../../project/static/js/custom-dialog.js)
- [批量删除逻辑](../../project/templates/base.html)
- [采购列表](../../project/templates/procurement_list.html)
- [合同列表](../../project/templates/contract_list.html)

## 变更历史
- 2025-01-18: 创建提案
- 待定: 开始实施
- 待定: 完成测试
- 待定: 部署上线

## 联系人
- 提案人：Kilo Code
- 审核人：待定
- 实施人：待定

## 备注
此变更是对现有功能的 bug 修复，不涉及新功能开发。修复后将显著提升用户体验，避免因模态框问题导致的页面卡死。