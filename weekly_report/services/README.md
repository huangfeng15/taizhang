# 周报管理服务模块

## 概述

本模块提供周报管理系统的核心服务，包括：
- **爬虫服务 (CrawlerService)**: 从阳光采购平台自动提取招投标信息
- **提醒服务 (ReminderService)**: 管理周报填写和信息补录提醒

## 爬虫服务 (CrawlerService)

### 功能特性

1. **基于Playwright for Python**
   - 支持无头模式和有头模式运行
   - 自动处理页面加载和等待
   - 支持API请求拦截

2. **智能数据提取**
   - 自动识别和提取32+个采购字段
   - 支持多中标人识别
   - 自动数据清洗和格式化

3. **容错机制**
   - 自动重试（最多3次）
   - 指数退避策略
   - 备用数据源切换

4. **数据清洗**
   - 金额解析（支持万元、千元等单位）
   - 日期标准化（多种格式支持）
   - 文本清洗（去除空白、换行等）

### 安装依赖

```bash
# 安装Python依赖
pip install playwright==1.48.0

# 安装浏览器驱动
python -m playwright install chromium
```

### 基本使用

#### 方式1: 使用便捷函数

```python
import asyncio
from weekly_report.services.crawler_service import crawl_procurement

async def main():
    # 爬取单个采购项目
    data = await crawl_procurement('GC2025001')
    
    if data:
        print(f"项目名称: {data.get('project_name')}")
        print(f"中标单位: {data.get('winning_bidder')}")
        print(f"中标金额: {data.get('winning_amount')}")

asyncio.run(main())
```

#### 方式2: 使用服务类

```python
import asyncio
from weekly_report.services.crawler_service import CrawlerService

async def main():
    # 创建爬虫服务实例
    crawler = CrawlerService()
    
    try:
        # 初始化浏览器
        await crawler.initialize()
        
        # 爬取数据
        data = await crawler.crawl_procurement_data('GC2025001')
        
        if data:
            print(f"成功提取数据: {data}")
    
    finally:
        # 关闭浏览器
        await crawler.close()

asyncio.run(main())
```

#### 方式3: 使用上下文管理器（推荐）

```python
import asyncio
from weekly_report.services.crawler_service import CrawlerService

async def main():
    # 使用上下文管理器自动管理资源
    async with CrawlerService() as crawler:
        data = await crawler.crawl_procurement_data('GC2025001')
        
        if data:
            print(f"项目名称: {data.get('project_name')}")
            print(f"中标单位: {data.get('winning_bidder')}")

asyncio.run(main())
```

### 配置说明

配置文件位于 `weekly_report/config/crawler_config.yml`

#### 浏览器配置

```yaml
browser:
  headless: false  # 是否无头模式
  timeout: 30000   # 超时时间(毫秒)
  slow_mo: 100     # 操作延迟(毫秒)
  viewport:
    width: 1920
    height: 1080
```

#### 重试配置

```yaml
retry:
  max_attempts: 3      # 最大重试次数
  delay: 2000          # 重试延迟(毫秒)
  backoff_factor: 2    # 退避因子
```

#### 字段提取配置

```yaml
field_extraction:
  project_name:
    selector: ".project-name"
    required: true
    
  winning_amount:
    selector: ".winning-amount"
    required: false
    parser: "amount"  # 使用金额解析器
```

### 数据格式

爬取返回的数据格式：

```python
{
    'project_name': '某某工程项目',
    'procurement_code': 'GC2025001',
    'procurement_method': '公开招标',
    'budget_amount': Decimal('1000000.00'),
    'control_price': Decimal('950000.00'),
    'winning_amount': Decimal('920000.00'),
    'winning_bidder': ['深圳市某某建筑公司', '广州市某某工程公司'],
    'announcement_release_date': '2025-01-15',
    'bid_opening_date': '2025-02-01',
    'result_publicity_release_date': '2025-02-10',
    '_metadata': {
        'crawled_at': '2025-01-20T10:30:00',
        'procurement_code': 'GC2025001',
        'source': 'crawler',
        'attempt': 1
    }
}
```

### 多中标人处理

爬虫服务自动识别多中标人：

```python
# 自动识别以下模式：
# - "第一中标候选人：公司A"
# - "第二中标候选人：公司B"
# - "中标候选人一：公司A"
# - "中标候选人二：公司B"

data = await crawl_procurement('GC2025001')
winners = data.get('winning_bidder', [])

if isinstance(winners, list):
    for i, winner in enumerate(winners, 1):
        print(f"第{i}中标人: {winner}")
```

### 错误处理

```python
import asyncio
from weekly_report.services.crawler_service import CrawlerService

async def main():
    async with CrawlerService() as crawler:
        try:
            data = await crawler.crawl_procurement_data('GC2025001')
            
            if data is None:
                print("爬取失败，请检查日志")
            else:
                print(f"成功爬取: {data.get('project_name')}")
                
        except Exception as e:
            print(f"发生错误: {e}")

asyncio.run(main())
```

### 日志配置

爬虫服务使用Python标准logging模块：

```python
import logging

# 配置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 或在Django settings.py中配置
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/crawler.log',
        },
    },
    'loggers': {
        'weekly_report.services.crawler_service': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

## 提醒服务 (ReminderService)

### 功能特性

1. **周报填写提醒**
   - 每周五自动生成提醒
   - 针对未提交周报的用户

2. **信息补录提醒**
   - 检测缺失字段
   - 自动生成补录提醒

3. **提醒记录管理**
   - 持久化提醒记录
   - 跟踪已读/已处理状态

### 基本使用

```python
from weekly_report.services.reminder_service import ReminderService

# 创建提醒服务实例
reminder_service = ReminderService()

# 生成周报提醒
weekly_reminders = reminder_service.generate_weekly_reminders()

# 生成信息补录提醒
missing_info_reminders = reminder_service.generate_missing_info_reminders()
```

## 测试

### 运行单元测试

```bash
# 运行所有测试
python manage.py test weekly_report.tests

# 运行爬虫服务测试
python manage.py test weekly_report.tests.test_crawler_service

# 使用pytest运行
pytest weekly_report/tests/test_crawler_service.py -v
```

### 测试覆盖率

```bash
# 生成测试覆盖率报告
pytest weekly_report/tests/ --cov=weekly_report.services --cov-report=html
```

## 开发指南

### 添加新的字段提取

1. 在 `crawler_config.yml` 中添加字段配置：

```yaml
field_extraction:
  new_field:
    selector: ".new-field-selector"
    required: false
    parser: "text"  # 或 "amount", "date"
```

2. 如需自定义解析器，在 `CrawlerService` 中添加：

```python
def _parse_custom(self, value: str) -> Any:
    """自定义解析器"""
    # 实现解析逻辑
    return parsed_value
```

### 添加新的数据源

1. 在 `crawler_config.yml` 中配置新数据源：

```yaml
target_sites:
  secondary:
    name: "新数据源"
    base_url: "https://example.com"
    search_url: "https://example.com/search"
```

2. 在 `CrawlerService` 中实现切换逻辑：

```python
async def switch_to_fallback_source(self):
    """切换到备用数据源"""
    # 实现切换逻辑
    pass
```

## 常见问题

### Q: 浏览器启动失败？

A: 确保已安装浏览器驱动：
```bash
python -m playwright install chromium
```

### Q: 爬取超时？

A: 调整配置文件中的超时设置：
```yaml
browser:
  timeout: 60000  # 增加到60秒
```

### Q: 数据提取失败？

A: 检查选择器配置是否正确，可以使用浏览器开发者工具验证CSS选择器。

### Q: 如何调试爬虫？

A: 设置 `headless: false` 并增加 `slow_mo` 延迟：
```yaml
browser:
  headless: false
  slow_mo: 500  # 每个操作延迟500ms
```

## 性能优化

1. **使用无头模式**: 生产环境建议使用 `headless: true`
2. **调整超时时间**: 根据网络情况调整timeout
3. **批量处理**: 对于多个采购项目，复用同一个浏览器实例
4. **缓存结果**: 对已爬取的数据进行缓存

## 安全注意事项

1. **遵守robots.txt**: 确保爬取行为符合目标网站规则
2. **控制频率**: 避免过于频繁的请求
3. **错误处理**: 妥善处理异常，避免泄露敏感信息
4. **日志脱敏**: 日志中不要记录敏感数据

## 更新日志

### v1.0.0 (2025-01-19)
- 初始版本发布
- 实现基于Playwright的爬虫服务
- 支持多中标人识别
- 实现自动重试和数据清洗
- 添加完整的单元测试

## 许可证

内部项目使用