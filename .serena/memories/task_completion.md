# 任务完成检查
- 修改代码后运行 `python manage.py test`，必要时执行 `python manage.py check`。
- 如涉及数据导入逻辑，准备脱敏 Excel 样例并手动测试导入流程；查看 `logs/import_*.log`。
- 确认未引入敏感配置，`.env` 未提交；若有脚本生成的临时文件，清理 backups/、logs/ 中冗余内容。
- 在提交前描述影响模块与验证步骤，必要时附日志或截图。