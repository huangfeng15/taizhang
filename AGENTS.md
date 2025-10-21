# Repository Guidelines

## 项目结构与模块分工
- 核心 Django 应用分布在 `procurement/`、`contract/`、`payment/`、`settlement/` 与 `supplier_eval/`，各自维护本域模型和 Admin 配置，避免跨模块耦合，公共跨域逻辑集中在 `project/`。
- `config/` 管理全局设置与路由；`scripts/` 收录导入校验脚本（如 `prepare_import_data.py`、`check_table_data.py`）；`docs/`、`plans/` 与 `specs/` 承载业务资料，导入中间数据置于 `data/`，敏感变量参照 `.env.example`。

## 构建、测试与开发命令
```powershell
python -m venv venv           # 初始化虚拟环境
venv\Scripts\activate         # 激活虚拟环境 (Windows)
pip install -r requirements.txt
python manage.py migrate      # 同步数据库
python manage.py runserver    # 本地启动服务
python manage.py test         # 运行单元测试
python manage.py check        # 框架一致性自检
python manage.py loaddata seed.json  # 如需导入基线数据
```
- 数据预处理统一通过 `python scripts\prepare_import_data.py <source.xlsx>`，导入失败可先执行 `scripts\check_table_data.py`。

## 代码风格与命名约定
- Python 代码按 PEP 8 使用四空格缩进，模块内函数保持单一职责；模型类采用 PascalCase，字段、工具函数与脚本文件使用 snake_case。
- Django 模板放在 `project/templates/` 内按业务子目录归档；管理后台自定义表单组件请单独封装在 `project/forms/`（待创建）以利复用，避免重复逻辑。

## 测试准则
- 默认使用 Django TestCase，测试入口统一在各应用的 `tests.py` 或 `tests/` 子包；测试函数命名为 `test_<场景>` 并覆盖成功与失败分支。
- 目前未设定强制覆盖率门槛，但提交前需至少运行 `python manage.py test`，并在 PR 描述中列出新增或受影响的测试用例。
- 涉及脚本的数据流程测试可借助 `data/fixtures/`（按需创建）存放脱敏样例，确保结果可重放。

## 提交与合并规范
- Git 历史采用动词开头的中文短语（示例：`修复高级筛选错误`），建议保持 50 字以内并描述目的而非实现细节。
- 发起 PR 前请确保通过测试、自检输出，以及说明变更范围、影响模块与手工验证步骤；若关联需求或缺陷，使用 `Refs #<编号>` 明确链接。
- 需要界面或数据示例时附上截图或关键日志片段，便于评审快速理解上下文。

## 配置与安全提示
- 生产与测试环境配置通过 `.env` 注入，切勿直接修改 `config/settings.py` 中的敏感常量；提交前确认 `.env` 未被加入版本控制。
- 数据导出、备份与临时脚本集中保存在 `backups/` 与 `logs/`，生成文件请在复核后清理，避免泄露供应商隐私。
