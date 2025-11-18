# 设计文档：删除确认模态框遮罩层问题修复

## 问题分析

### 当前实现流程
```
用户点击批量删除
  ↓
显示确认模态框 (CustomDialog.confirm)
  ↓
用户点击确认
  ↓
发送删除请求
  ↓
[如果失败]
  ↓
显示错误模态框 (CustomDialog.alert)
  ↓
问题：两个模态框的遮罩层叠加
```

### 根本原因
1. **延迟移除策略**: `_closeDialog()` 使用 200ms 延迟移除 DOM
2. **快速连续调用**: 确认模态框关闭和错误模态框打开之间没有足够的间隔
3. **DOM 清理不彻底**: 旧遮罩层未完全移除就创建了新遮罩层

## 解决方案设计

### 方案一：立即关闭 + Promise 链（推荐）

**优点**:
- 彻底解决遮罩层叠加问题
- 代码逻辑清晰
- 易于维护

**实现**:
```javascript
// 1. 修改 _closeDialog 方法
_closeDialog: function() {
    if (this.activeDialog) {
        // 立即移除，不使用延迟
        if (this.activeDialog.parentNode) {
            this.activeDialog.parentNode.removeChild(this.activeDialog);
        }
        this.activeDialog = null;
        document.body.style.overflow = '';
    }
}

// 2. 添加强制关闭方法
_forceCloseDialog: function() {
    // 移除所有可能残留的遮罩层
    const overlays = document.querySelectorAll('.custom-dialog-overlay');
    overlays.forEach(overlay => {
        if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    });
    this.activeDialog = null;
    document.body.style.overflow = '';
}

// 3. 在 _showDialog 开始时强制关闭
_showDialog: function(config) {
    // 确保旧模态框完全关闭
    this._forceCloseDialog();
    
    // ... 创建新模态框的代码
}

// 4. 修改批量删除逻辑
batchDelete: async function(apiUrl, confirmMessage) {
    // ... 前置检查代码
    
    const confirmed = await CustomDialog.confirm({...});
    
    if (!confirmed) {
        return;
    }
    
    // 确保确认框完全关闭后再继续
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // ... 发送请求
    
    // 失败时显示错误
    .catch(error => {
        CustomDialog.alert({
            title: '删除失败',
            message: error.message,
            type: 'error'
        });
        // 恢复按钮状态
    });
}
```

### 方案二：单一模态框状态管理

**优点**:
- 从根本上避免多个模态框同时存在
- 更严格的状态控制

**缺点**:
- 需要更多的重构工作
- 可能影响其他使用模态框的地方

**实现**:
```javascript
const CustomDialog = {
    activeDialog: null,
    isTransitioning: false, // 新增：过渡状态标志
    
    _showDialog: function(config) {
        // 如果正在过渡，等待完成
        if (this.isTransitioning) {
            return new Promise((resolve) => {
                const checkInterval = setInterval(() => {
                    if (!this.isTransitioning) {
                        clearInterval(checkInterval);
                        this._showDialog(config);
                        resolve();
                    }
                }, 50);
            });
        }
        
        // 标记开始过渡
        this.isTransitioning = true;
        
        // 强制关闭旧模态框
        this._forceCloseDialog();
        
        // 创建新模态框
        // ...
        
        // 标记过渡完成
        this.isTransitioning = false;
    }
}
```

## 推荐实现：方案一

选择方案一的原因：
1. **最小改动**: 只需修改关键方法，不影响现有功能
2. **立即生效**: 立即移除遮罩层，不依赖延迟
3. **防御性编程**: 添加强制清理方法作为保险
4. **向后兼容**: 不破坏现有的模态框使用方式

## 实现细节

### 1. CustomDialog 组件修改

```javascript
// custom-dialog.js

const CustomDialog = {
    activeDialog: null,
    
    /**
     * 强制关闭所有模态框（防御性清理）
     */
    _forceCloseDialog: function() {
        // 移除所有可能的遮罩层
        const overlays = document.querySelectorAll('.custom-dialog-overlay');
        overlays.forEach(overlay => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        });
        
        // 重置状态
        this.activeDialog = null;
        document.body.style.overflow = '';
        
        // 移除可能残留的事件监听器
        document.removeEventListener('keydown', this._escHandler);
    },
    
    /**
     * 关闭当前模态框（立即移除，不延迟）
     */
    _closeDialog: function() {
        if (this.activeDialog) {
            // 添加淡出动画
            this.activeDialog.style.opacity = '0';
            
            // 立即移除（不使用 setTimeout）
            if (this.activeDialog.parentNode) {
                this.activeDialog.parentNode.removeChild(this.activeDialog);
            }
            
            this.activeDialog = null;
            document.body.style.overflow = '';
        }
    },
    
    /**
     * 显示模态框
     */
    _showDialog: function(config) {
        // 在显示新模态框前，强制清理所有旧模态框
        this._forceCloseDialog();
        
        // 短暂延迟确保 DOM 更新完成
        setTimeout(() => {
            // 创建遮罩层和模态框的代码...
            // （保持原有逻辑）
        }, 10);
    }
}

// 页面加载时清理可能残留的遮罩层
document.addEventListener('DOMContentLoaded', function() {
    CustomDialog._forceCloseDialog();
});

// ESC 键强制关闭所有模态框
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        CustomDialog._forceCloseDialog();
    }
});
```

### 2. 批量删除逻辑修改

```javascript
// base.html 中的 BatchOperations.batchDelete

batchDelete: async function(apiUrl, confirmMessage) {
    const ids = this.getSelectedIds();
    if (ids.length === 0) {
        await CustomDialog.alert({
            title: '请选择项目',
            message: '请先选择要删除的项目',
            type: 'warning'
        });
        return;
    }
    
    const confirmed = await CustomDialog.confirm({
        title: '确认批量删除',
        message: confirmMessage || `确定要删除选中的 ${ids.length} 项吗？`,
        warnings: ['此操作不可恢复', '所有选中的数据将被永久删除'],
        dangerButton: true,
        type: 'warning'
    });
    
    if (!confirmed) {
        return;
    }
    
    // 关键：确保确认框完全关闭后再继续
    await new Promise(resolve => setTimeout(resolve, 50));
    
    const deleteBtn = document.getElementById('batchDeleteBtn');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 删除中...';
    deleteBtn.disabled = true;
    
    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: ids })
        });
        
        if (!response.ok) {
            throw new Error(`请求失败 (${response.status})`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            await CustomDialog.alert({
                title: '删除成功',
                message: data.message,
                type: 'success'
            });
            window.location.reload();
        } else {
            // 关键：失败时也要确保模态框正确显示
            await CustomDialog.alert({
                title: '删除失败',
                message: data.message,
                type: 'error'
            });
            deleteBtn.innerHTML = originalText;
            deleteBtn.disabled = false;
        }
    } catch (error) {
        // 关键：异常时也要确保模态框正确显示
        await CustomDialog.alert({
            title: '删除失败',
            message: error.message,
            type: 'error'
        });
        deleteBtn.innerHTML = originalText;
        deleteBtn.disabled = false;
    }
}
```

## 测试计划

### 单元测试场景
1. 快速连续弹出两个模态框
2. 模态框打开时按 ESC 键
3. 点击遮罩层外部关闭
4. 删除成功场景
5. 删除失败场景（权限不足、网络错误）

### 集成测试场景
1. 采购列表批量删除
2. 合同列表批量删除
3. 付款列表批量删除
4. 项目列表批量删除

### 浏览器兼容性测试
- Chrome
- Firefox
- Edge
- Safari

## 回滚计划

如果新实现出现问题，可以快速回滚：
1. 恢复 `custom-dialog.js` 的原始版本
2. 恢复 `base.html` 中的批量删除逻辑
3. 清除浏览器缓存

## 性能影响

- **DOM 操作**: 立即移除而非延迟移除，减少了 DOM 操作次数
- **内存占用**: 及时清理遮罩层，减少内存占用
- **用户体验**: 模态框切换更流畅，无卡顿感

## 后续优化建议

1. 考虑使用 CSS 动画替代 JavaScript 延迟
2. 实现模态框队列管理，支持多个模态框排队显示
3. 添加模态框状态监控和日志记录
4. 考虑使用成熟的模态框库（如 SweetAlert2）