# 项目采购与成本管理系统概览
- 目的：整合并管理采购、合同、付款、结算与供应商评价数据，提供统一查询与追溯。
- 类型：内部部署的 Django 4.2 + SQLite 数据管理平台（Python 3.10+），后台基于 Django Admin。
- 关键模块：procurement、contract、payment、settlement、supplier_eval；跨域逻辑集中在 project/；settings 与路由在 config/；运维脚本在 scripts/。
- 文档：业务与技术资料集中在 docs/、plans/、specs/，数据模板与导入文件在 data/。
- 核心特性：支持标准长表导入、历史宽表自动转长表、数据校验、全局搜索与追溯、自动备份。