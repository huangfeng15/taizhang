## ADDED Requirements

### Requirement: 阳光采购平台爬虫服务
系统 MUST 提供从阳光采购平台自动提取招投标信息的爬虫服务,基于Playwright for Python实现。

**ID**: REQ-DC-001
**优先级**: 高

#### Scenario: 通过URL提取信息
- **WHEN** 用户在阶段五录入界面输入阳光采购平台URL并点击"获取信息"
- **THEN** 系统应验证URL格式是否为阳光采购平台域名
- **AND** 使用Playwright启动浏览器并访问目标URL
- **AND** 等待页面加载完成(networkidle状态)
- **AND** 通过CSS选择器或API拦截提取关键字段
- **AND** 返回结构化数据填充到表单
- **AND** 显示"数据获取成功"提示

#### Scenario: 提取字段清单
- **WHEN** 爬虫成功解析页面
- **THEN** 系统应提取以下字段:
  - 采购单位(procurement_unit)
  - 中标单位(winning_bidder)
  - 中标单位联系人及方式(winning_contact)
  - 中标金额(winning_amount)
  - 候选人公示结束时间(candidate_publicity_end_date)
  - 结果公示发布时间(result_publicity_release_date)
  - 中标通知书发放日期(notice_issue_date)
  - 采购平台(procurement_platform)
  - 资格审查方式(qualification_review_method)
  - 评标谈判方式(bid_evaluation_method)
  - 定标方法(bid_awarding_method)
  - 公告发布时间(announcement_release_date)
  - 报名截止时间(registration_deadline)
  - 开标时间(bid_opening_date)
- **AND** 对金额字段进行格式化(去除逗号、单位转换)
- **AND** 对日期字段进行标准化(统一为YYYY-MM-DD格式)

#### Scenario: 爬虫失败处理
- **WHEN** 爬虫请求失败或页面结构变更
- **THEN** 系统应捕获异常并记录错误日志
- **AND** 显示友好的错误提示:"无法获取信息,请手动录入"
- **AND** 保留用户已输入的URL
- **AND** 允许用户重试或切换到手动录入模式

### Requirement: 多中标人处理
系统 MUST 支持处理存在多个中标单位或中标金额的情况。

**ID**: REQ-DC-002
**优先级**: 高

#### Scenario: 检测多中标人
- **WHEN** 爬虫解析到多个中标单位
- **THEN** 系统应识别所有中标单位和对应金额
- **AND** 返回中标人列表数据结构:
```json
{
  "multiple_winners": true,
  "winners": [
    {"name": "单位A", "amount": 1000000.00, "contact": "联系方式A"},
    {"name": "单位B", "amount": 800000.00, "contact": "联系方式B"}
  ]
}
```
- **AND** 不自动填充表单,等待用户选择

#### Scenario: 用户选择中标人
- **WHEN** 系统检测到多中标人并显示选择界面
- **THEN** 系统应以表格形式展示所有中标人信息
- **AND** 每行包含单选按钮
- **AND** 用户选择一行后点击"确认"
- **AND** 将选中的中标人信息填充到表单
- **AND** 记录用户的选择(用于审计)

### Requirement: Playwright浏览器自动化
系统 MUST 使用Playwright实现浏览器自动化和数据提取。

**ID**: REQ-DC-003
**优先级**: 高

#### Scenario: 浏览器初始化
- **WHEN** 爬虫服务启动
- **THEN** 系统应使用Playwright启动Chromium浏览器
- **AND** 配置无头模式(headless=True)
- **AND** 设置合理的超时时间(navigation: 15s, default: 8s)
- **AND** 配置User-Agent模拟真实浏览器

#### Scenario: API监听拦截
- **WHEN** 页面加载过程中
- **THEN** 系统应监听网络请求
- **AND** 拦截阳光采购平台的API响应
- **AND** 直接从JSON响应中提取数据(避免DOM解析)
- **AND** 提高数据提取效率和准确性

#### Scenario: 标签页切换
- **WHEN** 需要提取不同标签页的数据
- **THEN** 系统应使用page.getByText()定位标签
- **AND** 点击标签切换到对应内容
- **AND** 等待内容加载完成
- **AND** 提取标签页内的表格数据

### Requirement: 数据清洗和验证
系统 MUST 对爬取的数据进行清洗和格式验证。

**ID**: REQ-DC-004
**优先级**: 高

#### Scenario: 金额字段清洗
- **WHEN** 爬虫提取到金额字段(如"1,000,000.00元")
- **THEN** 系统应执行以下清洗步骤:
  - 移除千分位逗号
  - 移除货币单位("元"、"万元"等)
  - 转换为Decimal类型
  - 如果单位为"万元",乘以10000
- **AND** 验证金额为正数
- **AND** 保留两位小数

#### Scenario: 日期字段清洗
- **WHEN** 爬虫提取到日期字段(如"2025年1月15日")
- **THEN** 系统应执行以下清洗步骤:
  - 识别日期格式(支持多种中文格式)
  - 转换为标准格式(YYYY-MM-DD)
  - 验证日期有效性
- **AND** 如果解析失败,返回None并记录警告

#### Scenario: 文本字段清洗
- **WHEN** 爬虫提取到文本字段
- **THEN** 系统应执行以下清洗步骤:
  - 去除首尾空白字符
  - 移除多余的换行符和空格
  - 统一全角/半角字符
- **AND** 限制字段长度(根据数据库定义)

### Requirement: 爬虫配置管理
系统 MUST 使用配置文件管理爬虫的字段映射和解析规则。

**ID**: REQ-DC-005
**优先级**: 中

#### Scenario: YAML配置文件
- **WHEN** 系统初始化爬虫服务
- **THEN** 系统应加载YAML配置文件(如crawler_config.yml)
- **AND** 配置文件包含以下内容:
  - 字段映射(页面元素 → 数据库字段)
  - CSS选择器或XPath表达式
  - 数据清洗规则
  - 超时设置
  - 重试策略
- **AND** 支持热更新配置(无需重启服务)

#### Scenario: 配置示例
```yaml
fields:
  procurement_unit:
    selector: "div.unit-name"
    type: "text"
    required: true
  winning_amount:
    selector: "span.amount"
    type: "decimal"
    unit: "万元"
    multiplier: 10000
  bid_opening_date:
    selector: "td.date"
    type: "date"
    format: "%Y年%m月%d日"
```

### Requirement: 异常处理和重试
系统 MUST 实现健壮的异常处理和重试机制。

**ID**: REQ-DC-006
**优先级**: 高

#### Scenario: 网络超时重试
- **WHEN** 爬虫请求超时(默认10秒)
- **THEN** 系统应自动重试最多3次
- **AND** 每次重试间隔递增(1秒、2秒、4秒)
- **AND** 3次失败后返回错误
- **AND** 记录详细的错误日志

#### Scenario: 页面结构变更检测
- **WHEN** 爬虫无法找到预期的CSS选择器或元素
- **THEN** 系统应记录警告日志
- **AND** 尝试使用备用选择器
- **AND** 标记该字段为"未提取"
- **AND** 继续提取其他字段
- **AND** 在返回结果中注明哪些字段提取失败

#### Scenario: 反爬虫应对
- **WHEN** 目标网站返回403或验证码页面
- **THEN** 系统应识别反爬虫机制
- **AND** 记录错误并通知管理员
- **AND** 提示用户使用手动录入
- **AND** 暂停该URL的爬取(避免IP封禁)

### Requirement: 爬虫日志和监控
系统 MUST 记录爬虫的执行日志,支持问题排查和性能监控。

**ID**: REQ-DC-007
**优先级**: 中

#### Scenario: 详细日志记录
- **WHEN** 爬虫执行任何操作
- **THEN** 系统应记录以下信息:
  - 请求时间和URL
  - 响应状态码和耗时
  - 提取的字段数量
  - 成功/失败状态
  - 错误信息(如有)
  - 用户ID和IP地址
- **AND** 日志级别分为INFO、WARNING、ERROR
- **AND** 日志保留30天

#### Scenario: 爬虫性能监控
- **WHEN** 管理员访问爬虫监控页面
- **THEN** 系统应显示以下统计信息:
  - 今日爬取次数
  - 成功率(%)
  - 平均响应时间
  - 失败原因分布
  - 最近10次爬取记录
- **AND** 支持按日期范围查询
- **AND** 支持导出监控报表

### Requirement: 爬虫安全性
系统 MUST 确保爬虫服务的安全性,防止滥用和攻击。

**ID**: REQ-DC-008
**优先级**: 高

#### Scenario: URL白名单验证
- **WHEN** 用户提交URL进行爬取
- **THEN** 系统应验证URL是否在白名单中
- **AND** 白名单仅包含阳光采购平台域名
- **AND** 拒绝其他域名的爬取请求
- **AND** 记录非法请求尝试

#### Scenario: 频率限制
- **WHEN** 同一用户短时间内多次触发爬虫
- **THEN** 系统应限制爬取频率(如每分钟最多5次)
- **AND** 超过限制时显示"请求过于频繁"提示
- **AND** 要求用户等待一段时间后重试
- **AND** 记录频繁请求的用户

#### Scenario: 数据脱敏
- **WHEN** 爬虫日志包含敏感信息(如联系方式)
- **THEN** 系统应对敏感字段进行脱敏
- **AND** 手机号显示为"138****8000"
- **AND** 邮箱显示为"user***@example.com"
- **AND** 完整数据仅管理员可见

### Requirement: 爬虫测试和验证
系统 MUST 提供爬虫功能的独立测试工具。

**ID**: REQ-DC-009
**优先级**: 低

#### Scenario: 独立测试脚本
- **WHEN** 开发人员运行爬虫测试脚本
- **THEN** 系统应提供Django管理命令:
```bash
python manage.py test_crawler --url "https://ygcg.szexgrp.com/jyxxDetails.htm?..."
```
- **AND** 输出提取的字段和值
- **AND** 显示执行时间和成功状态
- **AND** 支持批量测试多个URL

#### Scenario: 爬虫单元测试
- **WHEN** 执行自动化测试
- **THEN** 系统应包含以下测试用例:
  - URL验证测试
  - Playwright浏览器启动测试
  - 字段提取测试(使用真实页面或mock)
  - API拦截测试
  - 数据清洗测试
  - 异常处理测试
  - 多中标人处理测试
- **AND** 测试覆盖率应达到80%以上

### Requirement: 现有爬虫逻辑复用
系统 MUST 复用现有Node.js爬虫的核心算法和经验。

**ID**: REQ-DC-010
**优先级**: 高

#### Scenario: 参考现有实现
- **WHEN** 开发Python爬虫服务
- **THEN** 系统应参考`D:\develop\new pachong yangguangcaigou\learning-crawler`中的实现
- **AND** 复用以下核心逻辑:
  - API监听拦截技术(page.route)
  - 标签页数据提取方法(extractResultTabData)
  - 多中标人识别算法(extractMultipleWinners)
  - 备用数据源切换机制(_attemptFallbackResolution)
  - 超时和重试策略
- **AND** 保持数据结构一致性

#### Scenario: 技术栈对应关系
- **WHEN** 从Node.js迁移到Python
- **THEN** 系统应使用以下对应关系:
  - `playwright` (Node.js) → `playwright` (Python)
  - `chromium.launch()` → `chromium.launch()`
  - `page.locator()` → `page.locator()`
  - `page.getByText()` → `page.get_by_text()`
  - `page.waitForLoadState()` → `page.wait_for_load_state()`
- **AND** API高度相似,迁移成本低