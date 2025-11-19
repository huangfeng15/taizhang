# Change: 添加周报管理系统

## Why

当前系统存在采购和合同信息重复填写的问题:
- 用户需要在周报和台账系统中分别录入相同的采购、合同信息
- 缺乏采购项目全生命周期的追踪机制
- 没有自动提醒机制确保信息及时更新
- 数据录入效率低,容易出现遗漏和不一致

通过建立周报管理系统,实现数据一次录入、多处使用,提高数据质量和工作效率。

## What Changes

### 新增功能模块
- **周报管理核心模块**: 支持采购项目7阶段生命周期追踪
- **智能提醒系统**: 每周五自动推送周报填写提醒
- **阶段性信息录入**: 按采购进展阶段逐步完善信息
- **数据爬虫服务**: 从阳光采购平台自动提取招投标信息
- **信息补录机制**: 自动检测并提示补全遗漏信息
- **台账转换功能**: 归档后一键转入现有台账系统
- **周报生成导出**: 自动生成Excel格式周报

### 数据模型
- 新增 `WeeklyReport` 模型(周报主表)
- 新增 `ProcurementProgress` 模型(采购进度追踪)
- 新增 `WeeklyReportReminder` 模型(提醒记录)
- 扩展现有 `Procurement` 和 `Contract` 模型字段

### 技术实现
- Playwright for Python爬虫服务(基于现有Node.js实现迁移)
- 定时任务调度(周报提醒,使用Django-Q或Celery)
- 数据校验和自动继承机制
- Excel报表生成(使用openpyxl)

## Impact

### 影响的规范
- 新增: `weekly-report-management` - 周报管理核心功能
- 新增: `procurement-lifecycle-tracking` - 采购生命周期追踪
- 新增: `data-crawler` - 数据爬虫服务
- 修改: 现有采购和合同数据模型(添加新字段)

### 影响的代码
- 新增应用: `weekly_report/` (周报管理应用)
- 新增服务: `weekly_report/services/crawler_service.py` (爬虫服务)
- 新增服务: `weekly_report/services/reminder_service.py` (提醒服务)
- 新增视图: `weekly_report/views_*.py` (周报相关视图)
- 修改模型: `procurement/models.py`, `contract/models.py` (扩展字段)
- 新增模板: `weekly_report/templates/` (周报页面)
- 新增管理命令: `send_weekly_reminders`, `sync_to_ledger`

### 数据库变更
- **BREAKING**: 需要数据迁移,添加新表和字段
- 建议在开发环境充分测试后再部署到生产环境

### 扩展性考虑
- 预留付款、结算周报管理接口
- 支持未来扩展其他业务流程周报

### 风险评估
- 数据迁移风险: 需要仔细测试新旧数据兼容性
- 爬虫稳定性: 依赖外部网站结构,需要异常处理和监控
- 性能影响: 定时任务和爬虫可能增加系统负载
- 用户培训: 需要培训用户使用新的周报录入流程