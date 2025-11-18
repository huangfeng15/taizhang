# Change: 添加操作日志功能和优化导航栏

## Why
当前系统缺少对非超级用户操作的审计追踪能力,无法有效监控和回溯用户的修改和新增操作。同时,左侧导航栏存在功能重复(系统管理和用户手册在右上角账户下拉菜单中已有),影响界面简洁性。

## What Changes
- **新增操作日志功能**:记录除超级用户外所有用户的修改和新增操作
- **日志查看页面**:在导航栏添加操作日志入口,展示日志列表
- **自动清理机制**:日志保留1周后自动清理
- **权限控制**:仅超级用户可删除日志,其他用户只读
- **导航栏优化**:移除左侧导航栏的"系统管理"和"使用手册"项(保留右上角下拉菜单中的入口)

## Impact
- 影响的规范:需要新增 `operation-logs` 规范
- 影响的代码:
  - 新增 `project/models.py` 中的 `OperationLog` 模型
  - 新增 `project/middleware/operation_log.py` 中间件
  - 新增 `project/views_logs.py` 视图
  - 新增 `project/templates/operation_logs.html` 模板
  - 修改 `project/templates/base.html` 导航栏
  - 新增 `project/management/commands/cleanup_old_logs.py` 清理命令
  - 修改 `config/urls.py` 添加路由
  - 修改 `config/settings.py` 注册中间件

## Performance Considerations
- 日志记录采用异步方式,不阻塞主请求
- 日志刷新频率:每次请求后异步写入,对性能影响最小
- 数据库索引:在 `created_at` 和 `user` 字段上建立索引以优化查询
- 自动清理:通过定时任务(cron)每天凌晨执行,避免影响业务高峰期