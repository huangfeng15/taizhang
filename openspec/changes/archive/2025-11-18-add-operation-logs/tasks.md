# 实施任务清单

## 1. 数据模型和迁移
- [ ] 1.1 在 `project/models.py` 中创建 `OperationLog` 模型
- [ ] 1.2 生成并执行数据库迁移

## 2. 中间件实现
- [ ] 2.1 创建 `project/middleware/operation_log.py` 中间件
- [ ] 2.2 在 `config/settings.py` 中注册中间件

## 3. 视图和模板
- [ ] 3.1 创建 `project/views_logs.py` 视图函数
- [ ] 3.2 创建 `project/templates/operation_logs.html` 模板
- [ ] 3.3 在 `config/urls.py` 中添加路由

## 4. 导航栏调整
- [ ] 4.1 修改 `project/templates/base.html` 移除左侧导航栏的"系统管理"和"使用手册"

## 5. 日志清理功能
- [ ] 5.1 创建 `project/management/commands/cleanup_old_logs.py` 管理命令
- [ ] 5.2 配置定时任务(cron)每天执行清理

## 6. 权限控制
- [ ] 6.1 在视图中实现超级用户删除权限检查
- [ ] 6.2 在模板中根据权限显示/隐藏删除按钮

## 7. 测试验证
- [ ] 7.1 测试日志记录功能(修改、新增操作)
- [ ] 7.2 测试超级用户不记录日志
- [ ] 7.3 测试日志查看页面
- [ ] 7.4 测试超级用户删除日志
- [ ] 7.5 测试普通用户无法删除日志
- [ ] 7.6 测试自动清理功能
- [ ] 7.7 验证导航栏调整