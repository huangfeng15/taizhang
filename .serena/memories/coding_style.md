# 编码与设计规范
- Python 遵循 PEP 8，四空格缩进；模型类 PascalCase，字段与工具函数 snake_case。
- 坚持 KISS、YAGNI、DRY、SOLID 原则；各 Django 应用保持领域内聚，跨域逻辑放在 project/。
- 管理后台自定义表单组件需集中在待建的 project/forms/ 以复用。
- 测试使用 Django TestCase；测试函数命名 `test_<场景>`，覆盖成功与失败分支。
- Git 提交信息使用中文动词短语，约 50 字内强调目的。