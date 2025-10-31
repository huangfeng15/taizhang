
# 第一阶段实施方案：基础配置（测试环境简化版）

## 执行摘要

本方案针对硬编码审查报告中的 HC-02、HC-03 问题，实施业务常量的集中管理，预计耗时 2-3 小时。

**关键成果**：
- 集中管理业务常量（年份范围、监控起始日期）
- 支持通过统一配置调整起始年份
- 提供配置验证脚本和完善文档

**注意**：本版本为测试环境简化版，暂不处理安全配置模块（HC-01），安全配置将在生产环境部署时单独处理。

---

## 1. 问题分析

### 1.1 HC-02：全局年份范围固定起于 2019

**当前状况**：
- `project/context_processors.py:35` → `year_start = 2019`
- `project/views.py` 多处 → `range(2019, current_year + 1)`
- `scripts/check_data_statistics.py:27` → `range(2019, ...)`

**风险等级**：🟠 高
- 跨年需改多处代码
- 易出现遗漏和不一致

### 1.2 HC-03：更新监控默认起始日写死

**当前状况**：
```python
# project/views.py:2177
if not start_date:
    start_date = date(2025, 10, 1)
```

**风险等级**：🟡 中
- 历史数据回溯时逻辑失准

---

## 2. 解决方案设计

### 2.1 架构设计

```
project/
├── project/
│   ├── constants.py                   # 业务常量模块（新建）
│   └── context_processors.py         # 全局上下文（修改）
├── scripts/
│   ├── validate_config.py            # 配置验证脚本（新建）
│   └── check_data_statistics.py      # 数据统计脚本（修改）
└── .env.example                       # 环境变量模板（修改）
```

### 2.2 模块职责

| 模块 | 职责 | 原则 |
|------|------|------|
| `constants.py` | 集中管理业务常量，支持环境覆盖 | DRY：单点定义，多处引用 |
| `validate_config.py` | 配置验证，防止部署时配置错误 | YAGNI：仅验证必需项 |

---

## 3. 详细实施步骤

### 步骤 1：更新环境变量模板（10 分钟）

**更新 `.env.example`**，添加业务常量配置部分：

```ini
# ==================== 业务常量配置 ====================

# 系统基准年份（数据起始年份）
# 用途：定义系统数据的起始年份，影响年份筛选范围
# 默认值：2019
# 示例：如果系统从 2020 年开始使用，设置为 2020
SYSTEM_BASE_YEAR=2019

# 年份窗口（允许向未来延伸的年数）
# 用途：允许提前录入未来年度的数据
# 默认值：1（允许录入下一年度数据）
# 范围：0-5
SYSTEM_YEAR_WINDOW=1

# 更新监控默认起始日期
# 用途：更新监控功能的默认监控起始日期
# 格式：YYYY-MM-DD
# 默认值：2025-10-01
MONITOR_START_DATE=2025-10-01
```

---

### 步骤 2：新建业务常量模块（30 分钟）

**创建 `project/constants.py`**：

```python
"""
业务常量集中管理
遵循 DRY 原则，避免魔法值散落在代码各处
"""
import os
from datetime import date, datetime
from typing import List


def get_base_year() -> int:
    """
    获取系统基准年份（数据起始年份）
    
    默认为 2019，可通过环境变量 SYSTEM_BASE_YEAR 覆盖
    """
    year_str = os.environ.get('SYSTEM_BASE_YEAR', '2019').strip()
    try:
        base_year = int(year_str)
        current_year = datetime.now().year
        if base_year < 2000 or base_year > current_year:
            raise ValueError(f"基准年份必须在 2000 到 {current_year} 之间")
        return base_year
    except ValueError as e:
        print(f"⚠️  警告: SYSTEM_BASE_YEAR 配置无效 ({year_str})，使用默认值 2019")
        return 2019


def get_year_window() -> int:
    """
    获取年份窗口（向未来延伸的年数）
    
    默认为 1 年（允许录入下一年度数据），可通过环境变量 SYSTEM_YEAR_WINDOW 覆盖
    """
    window_str = os.environ.get('SYSTEM_YEAR_WINDOW', '1').strip()
    try:
        window = int(window_str)
        if window < 0 or window > 5:
            raise ValueError("年份窗口必须在 0 到 5 之间")
        return window
    except ValueError:
        print(f"⚠️  警告: SYSTEM_YEAR_WINDOW 配置无效 ({window_str})，使用默认值 1")
        return 1


def get_default_monitor_start_date() -> date:
    """
    获取更新监控默认起始日期
    
    默认为 2025-10-01，可通过环境变量 MONITOR_START_DATE 覆盖
    """
    date_str = os.environ.get('MONITOR_START_DATE', '2025-10-01').strip()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"⚠️  警告: MONITOR_START_DATE 配置无效 ({date_str})，使用默认值 2025-10-01")
        return date(2025, 10, 1)


# ==================== 导出常量 ====================

BASE_YEAR = get_base_year()
YEAR_WINDOW = get_year_window()
DEFAULT_MONITOR_START_DATE = get_default_monitor_start_date()


# ==================== 辅助函数 ====================

def get_year_range(include_future: bool = True) -> List[int]:
    """
    获取系统支持的年份范围列表
    
    Args:
        include_future: 是否包含未来年份（用于数据录入）
    
    Returns:
        年份列表，例如 [2019, 2020, ..., 2025, 2026]
    """
    current_year = datetime.now().year
    end_year = current_year + YEAR_WINDOW if include_future else current_year
    return list(range(BASE_YEAR, end_year + 1))


def get_current_year() -> int:
    """获取当前年份"""
    return datetime.now().year
```

---

### 步骤 3：修改相关业务代码（60 分钟）

#### 3.1 修改 `project/context_processors.py`

```python
# 在文件开头添加导入
from project.constants import BASE_YEAR, get_current_year

def global_filter_options(request) -> Dict[str, object]:
    """为全局筛选组件提供项目和年度选项"""
    current_year = get_current_year()
    # 使用配置化的基准年份（第 35 行）
    year_start = BASE_YEAR
    year_end = current_year + 1
    year_options: List[int] = list(range(year_start, year_end + 1))
    
    # ... 其余代码保持不变
```

#### 3.2 修改 `project/views.py`

在文件开头添加导入：
```python
from project.constants import BASE_YEAR, get_current_year, get_year_range, DEFAULT_MONITOR_START_DATE
```

需要修改的位置：

**位置 1：第 290 行附近（generate_report 函数）**
```python
# 原代码：
# available_years = list(range(2019, current_year + 2))

# 修改为：
available_years = get_year_range(include_future=True)
```

**位置 2：第 2132 行附近（archive_monitor 函数）**
```python
# 原代码：
# base_years = list(range(2019, current_year + 1))

# 修改为：
base_years = get_year_range(include_future=False)
```

**位置 3：第 2177 行（update_monitor 函数）**
```python
# 原代码：
# if not start_date:
#     start_date = date(2025, 10, 1)

# 修改为：
if not start_date:
    start_date = DEFAULT_MONITOR_START_DATE
```

**位置 4：第 2541 行附近（statistics_view 函数）**
```python
# 原代码：
# for year in range(2019, datetime.now().year + 1):

# 修改为：
for year in get_year_range(include_future=False):
```

**位置 5：第 2609 行附近（report 相关）**
```python
# 原代码：
# 'available_years': list(range(2019, current_year + 2)),

# 修改为：
'available_years': get_year_range(include_future=True),
```

#### 3.3 修改 `scripts/check_data_statistics.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查数据库中的统计数据"""
import os
import sys

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from project.constants import BASE_YEAR, get_current_year

def main():
    print('=== 数据统计 ===')
    print(f'采购总数: {Procurement.objects.count()}')
    print(f'合同总数: {Contract.objects.count()}')
    print(f'付款总数: {Payment.objects.count()}')
    
    current_year = get_current_year()
    
    print('\n=== 采购年份分布（按结果公示发布时间） ===')
    # 使用配置化的基准年份
    for year in range(BASE_YEAR, current_year + 1):
        count = Procurement.objects.filter(result_publicity_release_date__year=year).count()
        if count > 0:
            print(f'{year}年: {count}条')
    
    print('\n=== 合同年份分布（按签订日期） ===')
    for year in range(BASE_YEAR, current_year + 1):
        count = Contract.objects.filter(signing_date__year=year).count()
        if count > 0:
            print(f'{year}年: {count}条')
    
    print('\n=== 付款年份分布（按付款日期） ===')
    for year in range(BASE_YEAR, current_year + 1):
        count = Payment.objects.filter(payment_date__year=year).count()
        if count > 0:
            print(f'{year}年: {count}条')
    
    # 数据完整性检查
    print('\n=== 数据完整性检查 ===')
    proc_no_date = Procurement.objects.filter(result_publicity_release_date__isnull=True).count()
    if proc_no_date > 0:
        print(f'警告: {proc_no_date}条采购记录缺少结果公示发布时间')
    
    contract_no_date = Contract.objects.filter(signing_date__isnull=True).count()
    if contract_no_date > 0:
        print(f'警告: {contract_no_date}条合同记录缺少签订日期')
    
    payment_no_date = Payment.objects.filter(payment_date__isnull=True).count()
    if payment_no_date > 0:
        print(f'警告: {payment_no_date}条付款记录缺少付款日期')

if __name__ == '__main__':
    main()
```

---

### 步骤 4：创建配置验证脚本（20 分钟）

**创建 `scripts/validate_config.py`**（简化版，仅验证业务常量）：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置验证脚本（测试环境简化版）
用于检查业务常量配置是否正确设置
"""
import os
import sys
from pathlib import Path


def validate_constants():
    """验证业务常量"""
    print("\n📋 检查业务常量配置...")
    
    # 添加项目路径
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        from project.constants import BASE_YEAR, YEAR_WINDOW, DEFAULT_MONITOR_START_DATE
        
        print(f"   ✓ BASE_YEAR (基准年份): {BASE_YEAR}")
        print(f"   ✓ YEAR_WINDOW (年份窗口): {YEAR_WINDOW}")
        print(f"   ✓ DEFAULT_MONITOR_START_DATE (监控起始日): {DEFAULT_MONITOR_START_DATE}")
        
        # 验证合理性
        from datetime import datetime
        current_year = datetime.now().year
        
        if BASE_YEAR < 2000 or BASE_YEAR > current_year:
            print(f"   ⚠️  警告: BASE_YEAR ({BASE_YEAR}) 不在合理范围内")
            return False
        
        if YEAR_WINDOW < 0 or YEAR_WINDOW > 5:
            print(f"   ⚠️  警告: YEAR_WINDOW ({YEAR_WINDOW}) 不在合理范围内")
            return False
        
        print("\n   ✅ 业务常量配置正确")
        return True
        
    except Exception as e:
        print(f"   ❌ 业务常量加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 业务常量配置验证工具（测试环境版）")
    print("=" * 60)
    
    # 验证业务常量
    passed = validate_constants()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 验证结果")
    print("=" * 60)
    
    if passed:
        print("\n🎉 业务常量配置验证通过！\n")
        return 0
    else:
        print("\n⚠️  配置验证失败，请检查上述错误并修正。\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

---

## 4. 测试计划

### 4.1 单元测试清单

创建 `project/tests/test_constants.py`（可选）：

```python
"""业务常量模块单元测试"""
import os
from datetime import date
from django.test import TestCase


class ConstantsTestCase(TestCase):
    """测试业务常量模块"""
    
    def test_base_year_default(self):
        """测试默认基准年份"""
        from project.constants import get_base_year
        self.assertEqual(get_base_year(), 2019)
    
    def test_base_year_from_env(self):
        """测试从环境变量读取基准年份"""
        os.environ['SYSTEM_BASE_YEAR'] = '2020'
        from importlib import reload
        import project.constants
        reload(project.constants)
        self.assertEqual(project.constants.BASE_YEAR, 2020)
        del os.environ['SYSTEM_BASE_YEAR']
    
    def test_year_range(self):
        """测试年份范围生成"""
        from project.constants import get_year_range, BASE_YEAR
        from datetime import datetime
        
        years = get_year_range(include_future=False)
        self.assertEqual(years[0], BASE_YEAR)
        self.assertEqual(years[-1], datetime.now().year)
    
    def test_monitor_start_date(self):
        """测试监控起始日期"""
        from project.constants import get_default_monitor_start_date
        start_date = get_default_monitor_start_date()
        self.assertIsInstance(start_date, date)
```

### 4.2 集成测试场景

| 场景 | 测试步骤 | 预期结果 |
|------|----------|----------|
| 默认配置测试 | 不设置环境变量，运行 `runserver` | 使用默认年份 2019，正常启动 |
| 配置验证 | 运行 `python scripts/validate_config.py` | 显示业务常量检查结果 |
| 年份切换 | 设置 `SYSTEM_BASE_YEAR=2020` | 年份选项从 2020 开始 |
| 数据统计 | 运行 `python scripts/check_data_statistics.py` | 使用配置的年份范围 |

---

## 5. 实施检查清单

### 5.1 代码变更清单

- [ ] **新建文件**
  - [ ] `project/constants.py`
  - [ ] `scripts/validate_config.py`
  - [ ] `project/tests/test_constants.py`（可选）

- [ ] **修改文件**
  - [ ] `.env.example`（添加业务常量配置）
  - [ ] `project/context_processors.py`（1 处修改）
  - [ ] `project/views.py`（5 处修改）
  - [ ] `scripts/check_data_statistics.py`（3 处修改）

### 5.2 测试验证清单

- [ ] **测试环境测试**
  ```bash
  # 1. 运行配置验证
  python scripts/validate_config.py
  
  # 2. 启动开发服务器
  python manage.py runserver
  
  # 3. 验证年份范围
  python scripts/check_data_statistics.py
  
  # 4. 访问页面测试
  # - 访问 http://127.0.0.1:3500/
  # - 测试全局年份筛选器
  # - 测试监控页面
  ```

- [ ] **年份配置测试**
  ```bash
  # 1. 设置自定义年份
  set SYSTEM_BASE_YEAR=2020
  set SYSTEM_YEAR_WINDOW=2
  
  # 2. 运行配置验证
  python scripts/validate_config.py
  
  # 3. 验证年份范围
  python scripts/check_data_statistics.py
  ```

- [ ] **功能回归测试**
  - [ ] 全局筛选器年份选项正确
  - [ ] 项目列表页年份筛选正常
  - [ ] 监控页面年份范围正确
  - [ ] 更新监控起始日期使用配置值
  - [ ] 数据统计脚本年份范围正确

### 5.3 配置检查清单

- [ ] 年份常量未在代码中硬编码
- [ ] 业务常量集中在 `constants.py` 管理
- [ ] 所有年份引用已替换为配置值
- [ ] 监控起始日期使用配置值
- [ ] `.env.example` 包含业务常量说明

---

## 6. 风险管理

### 6.1 风险识别与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 年份范围修改影响现有数据统计 | 中 | 低 | 保持默认值不变，充分测试 |
| 配置文件错误导致功能异常 | 中 | 低 | 修改前备份，测试环境先验证 |
| 导入顺序问题导致循环依赖 | 中 | 低 | 遵循 Django 最佳实践 |

### 6.2 回滚方案

**快速回滚步骤**：
```bash
# 1. 使用 Git 回滚
git log --oneline -5  # 查看最近提交
git revert <commit-hash>  # 回滚到指定提交

# 2. 删除新增文件（如有必要）
rm project/constants.py
rm scripts/validate_config.py

# 3. 恢复修改的文件
git checkout project/context_processors.py
git checkout project/views.py
git checkout scripts/check_data_statistics.py
```

---

## 7. 实施时间表

| 阶段 | 任务 | 预计时间 | 状态 |
|------|------|----------|------|
| **开发** | 更新环境变量模板 | 10 分钟 | ⬜ 待开始 |
| **开发** | 实现业务常量模块 | 30 分钟 | ⬜ 待开始 |
| **开发** | 修改业务代码 | 60 分钟 | ⬜ 待开始 |
| **开发** | 创建验证脚本 | 20 分钟 | ⬜ 待开始 |
| **测试** | 功能测试 | 30 分钟 | ⬜ 待开始 |
| **文档** | 更新相关文档 | 20 分钟 | ⬜ 待开始 |
| **总计** | | **2-3 小时** | |

---

## 8. 成功标准

### 8.1 功能标准
- [ ] 年份范围可通过环境变量调整
- [ ] 监控起始日期可配置
- [ ] 所有现有功能正常运行
- [ ] 默认值保持不变（2019）

### 8.2 质量标准
- [ ] 配置验证脚本通过
- [ ] 代码符合 DRY 原则
- [ ] 无重复的硬编码年份

### 8.3 文档标准
- [ ] `.env.example` 包含清晰说明
- [ ] 提供配置示例
- [ ] 验证脚本易于使用

---

## 9. Git 提交建议

实施完成后，建议分阶段提交：

```bash
# 提交 1：业务常量模块
git add project/constants.py
git commit -m "feat(config): 新增业务常量模块，消除硬编码

- 集中管理年份范围、监控起始日期等业务常量
- 支持通过环境变量覆盖默认值
- 遵循 DRY 原则，单点维护

Refs: HC-02, HC-03"

# 提交 2：修改业务代码
git add project/context_processors.py project/views.py scripts/check_data_statistics.py
git commit -m "refactor: 应用业务常量模块替换硬编码

- project/context_processors.py: 使用 BASE_YEAR 常量
- project/views.py: 替换所有年份硬编码
- scripts/check_data_statistics.py: 使用配置化年份范围

Refs: HC-02, HC-03"

# 提交 3：配置验证和文档
git add scripts/validate_config.py .env.example
git commit -m "docs: 添加配置验证脚本和环境变量说明

- 新增 validate_config.py 业务常量验证脚本
- 完善 .env.example 业务常量配置说明

Refs: HC-02, HC-03"
```

---

## 10. 总结

### 10.1 实施成果

本方案通过以下措施解决了硬编码审查报告中的 HC-02、HC-03 问题：

1. **业务常量统一维护**
   - 创建 `project/constants.py` 模块
   - 支持环境变量覆盖
   - 消除魔法值和重复代码

2. **简单的验证机制**
   - 提供 `validate_config.py` 验证脚本
   - 快速检查配置状态

3. **清晰的文档支持**
   - 更新 `.env.example` 配置说明
   - 提供使用示例

### 10.2 原则体现

**KISS（简单至上）**：
- 每个函数职责单一，逻辑清晰
- 避免过度设计，仅实现必需功能

**YAGNI（精益求精）**：
- 仅解决当前明确的硬编码问题
- 不引入不必要的配置框架

**DRY（杜绝重复）**：
- 年份范围单点定义
- 配置读取逻辑不重复

---

**文档版本**：v2.0（测试环境简化版）  
**创建日期**：2025-10-27  
**最后更新**：2025-10-27  
**文档状态**：待审批  


---

# 第二阶段实施方案：模板与脚本治理

## 执行摘要

本阶段针对 HC-04、HC-07、HC-08、HC-09 问题，实施导入模板和脚本的配置化改造，预计耗时 12-15 小时。

**关键成果**：
- 导入模板元数据配置化（YAML/JSON）
- 数据导入命令参数化和模块化
- 数据清洗脚本支持配置文件
- 表统计脚本配置驱动

---

## 1. 问题分析

### 1.1 HC-04：导入模板定义内联于视图

**当前状况**：
- `project/views.py:136-334` → 模板文件名、表头、说明等硬编码在视图函数中
- 每次调整模板需要修改代码并重新部署

**风险等级**：🔴 严重
- 模板调整需要发版
- 难以按客户定制化
- 违反 OCP 原则

### 1.2 HC-07：数据导入命令配置固化

**当前状况**：
- `procurement/management/commands/import_excel.py` 写死模块列表、列映射
- 新增模块或字段需要修改命令代码

**风险等级**：🟠 高
- 扩展性差
- 测试环境难以复用

### 1.3 HC-08：数据清洗脚本路径和列索引写死

**当前状况**：
- `scripts/prepare_import_data.py:58-154` 硬编码列索引（如列 44-56）
- 文件路径固定，模板变化即失效

**风险等级**：🟠 高
- 模板微调导致脚本失效
- 无法复用于其他场景

### 1.4 HC-09：表统计脚本业务表写死

**当前状况**：
- `scripts/check_table_data.py:12-31` 硬编码业务表名和中文描述

**风险等级**：🟡 中
- 系统扩展需改脚本

---

## 2. 解决方案设计

### 2.1 架构设计

```
project/
├── project/
│   ├── import_templates/              # 导入模板配置目录（新建）
│   │   ├── procurement.yml           # 采购模板配置
│   │   ├── contract.yml              # 合同模板配置
│   │   ├── payment.yml               # 付款模板配置
│   │   └── supplier_eval.yml         # 供应商评价模板配置
│   ├── template_generator.py         # 模板生成器（新建）
│   └── views.py                       # 视图（重构）
├── procurement/management/commands/
│   └── import_excel.py               # 导入命令（重构）
├── scripts/
│   ├── prepare_import_data.py        # 数据清洗（重构）
│   ├── check_table_data.py           # 表统计（重构）
│   └── configs/                       # 脚本配置目录（新建）
│       ├── table_stats.yml           # 表统计配置
│       └── data_cleanup.yml          # 数据清洗配置
└── docs/
    └── 导入模板配置指南.md            # 配置文档（新建）
```

### 2.2 模块职责

| 模块 | 职责 | 原则 |
|------|------|------|
| `import_templates/*.yml` | 定义模板元数据（字段、说明、验证规则） | SRP：单一职责 |
| `template_generator.py` | 根据配置生成Excel模板 | OCP：开放扩展 |
| `import_excel.py` | 从配置读取导入规则 | DRY：避免重复 |
| `scripts/configs/*.yml` | 脚本运行参数配置 | KISS：简单配置 |

---

## 3. 详细实施步骤

### 步骤 1：设计模板配置格式（60 分钟）

**创建 `project/import_templates/procurement.yml`**：

```yaml
# 采购导入模板配置
metadata:
  name: "采购信息导入模板"
  description: "用于批量导入采购项目基本信息"
  version: "1.0"
  module: "procurement"
  model: "Procurement"
  
# 文件生成配置
file:
  name_template: "采购信息导入模板_{year}.xlsx"
  sheet_name: "采购信息"
  start_row: 3  # 数据从第3行开始（前2行为说明和表头）
  
# 说明行配置
instructions:
  row: 1
  content: |
    导入说明：
    1. 请勿修改表头行的列名和顺序
    2. 必填字段不能为空
    3. 日期格式：YYYY-MM-DD
    4. 金额单位：元
    5. 采购方式可选值：{procurement_method_choices}

# 字段配置
fields:
  - name: "项目名称"
    field: "project_name"
    required: true
    data_type: "string"
    max_length: 200
    help_text: "采购项目的完整名称"
    
  - name: "采购方式"
    field: "procurement_method"
    required: true
    data_type: "choice"
    choices_from_model: true  # 从模型读取choices
    help_text: "公开招标、邀请招标、竞争性谈判等"
    
  - name: "预算金额"
    field: "budget_amount"
    required: true
    data_type: "decimal"
    decimal_places: 2
    help_text: "采购预算金额，单位：元"
    
  - name: "中标供应商"
    field: "winning_supplier"
    required: false
    data_type: "string"
    max_length: 200
    help_text: "中标供应商名称"
    
  - name: "结果公示发布时间"
    field: "result_publicity_release_date"
    required: false
    data_type: "date"
    format: "YYYY-MM-DD"
    help_text: "中标结果公示的发布日期"

# 验证规则
validation:
  - field: "budget_amount"
    rule: "positive"
    message: "预算金额必须大于0"
    
  - field: "result_publicity_release_date"
    rule: "date_range"
    params:
      min_year: 2000
      max_year: "current+1"
    message: "日期必须在合理范围内"

# 数据导入配置
import:
  conflict_strategy: "update"  # update, skip, error
  batch_size: 100
  key_fields: ["project_name", "procurement_method"]  # 用于判断重复的字段
```

**创建其他模板配置**：
- `contract.yml` - 合同模板
- `payment.yml` - 付款模板
- `supplier_eval.yml` - 供应商评价模板

---

### 步骤 2：实现模板生成器（120 分钟）

**创建 `project/template_generator.py`**：

```python
"""
Excel 导入模板生成器
根据 YAML 配置文件生成标准化的导入模板
"""
import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.apps import apps


class TemplateGenerator:
    """模板生成器"""
    
    def __init__(self, config_path: str):
        """
        初始化生成器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.model = self._get_model()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_model(self):
        """获取 Django 模型类"""
        module_name = self.config['metadata']['module']
        model_name = self.config['metadata']['model']
        return apps.get_model(module_name, model_name)
    
    def _get_choices_text(self, field_config: Dict) -> str:
        """获取选项文本"""
        if not field_config.get('choices_from_model'):
            return ""
        
        field_name = field_config['field']
        model_field = self.model._meta.get_field(field_name)
        
        if hasattr(model_field, 'choices') and model_field.choices:
            choices = [display for value, display in model_field.choices]
            return "、".join(choices)
        
        return ""
    
    def _format_instructions(self) -> str:
        """格式化说明文本"""
        instructions = self.config['instructions']['content']
        
        # 替换占位符
        for field in self.config['fields']:
            if field.get('choices_from_model'):
                placeholder = f"{{{field['field']}_choices}}"
                choices_text = self._get_choices_text(field)
                instructions = instructions.replace(placeholder, choices_text)
        
        return instructions
    
    def generate(self, output_path: str, year: int = None) -> str:
        """
        生成模板文件
        
        Args:
            output_path: 输出目录
            year: 年份（用于文件名）
        
        Returns:
            生成的文件路径
        """
        if year is None:
            year = datetime.now().year
        
        # 生成文件名
        filename_template = self.config['file']['name_template']
        filename = filename_template.format(year=year)
        filepath = Path(output_path) / filename
        
        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = self.config['file']['sheet_name']
        
        # 样式定义
        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        instruction_font = Font(size=10, color="FF0000")
        instruction_alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # 写入说明行
        instructions_row = self.config['instructions']['row']
        ws.merge_cells(start_row=instructions_row, start_column=1, 
                      end_row=instructions_row, end_column=len(self.config['fields']))
        cell = ws.cell(row=instructions_row, column=1)
        cell.value = self._format_instructions()
        cell.font = instruction_font
        cell.alignment = instruction_alignment
        ws.row_dimensions[instructions_row].height = 80
        
        # 写入表头
        header_row = instructions_row + 1
        for col_idx, field in enumerate(self.config['fields'], start=1):
            cell = ws.cell(row=header_row, column=col_idx)
            
            # 字段名（必填字段标记*）
            field_name = field['name']
            if field.get('required'):
                field_name += "*"
            
            cell.value = field_name
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            
            # 设置列宽
            ws.column_dimensions[cell.column_letter].width = 15
            
            # 添加批注（帮助文本）
            if field.get('help_text'):
                from openpyxl.comments import Comment
                comment = Comment(field['help_text'], "系统")
                cell.comment = comment
        
        # 保存文件
        wb.save(filepath)
        return str(filepath)


def generate_all_templates(output_dir: str, year: int = None):
    """
    生成所有模板
    
    Args:
        output_dir: 输出目录
        year: 年份
    """
    templates_dir = Path(__file__).parent / 'import_templates'
    
    for config_file in templates_dir.glob('*.yml'):
        print(f"正在生成模板: {config_file.name}")
        generator = TemplateGenerator(config_file)
        filepath = generator.generate(output_dir, year)
        print(f"  ✓ 已生成: {filepath}")
```

---


**适用环境**：测试环境
### 步骤 3：重构视图层模板生成逻辑（90 分钟）

**修改 `project/views.py` 中的模板生成函数**：

```python
from project.template_generator import TemplateGenerator
from pathlib import Path

def generate_import_template(request):
    """生成导入模板"""
    module = request.GET.get('module', 'procurement')
    year = request.GET.get('year', datetime.now().year)
    
    # 获取配置文件路径
    config_dir = Path(__file__).parent / 'import_templates'
    config_file = config_dir / f'{module}.yml'
    
    if not config_file.exists():
        return JsonResponse({'error': f'模板配置不存在: {module}'}, status=400)
    
    try:
        # 生成模板
        generator = TemplateGenerator(config_file)
        output_dir = Path(settings.MEDIA_ROOT) / 'templates'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = generator.generate(str(output_dir), year)
        
        # 返回文件下载
        with open(filepath, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{Path(filepath).name}"'
            return response
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

### 步骤 4：重构导入命令（120 分钟）

**修改 `procurement/management/commands/import_excel.py`**：

```python
import yaml
from pathlib import Path
from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    help = '从Excel文件导入数据（配置驱动）'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Excel文件路径')
        parser.add_argument('--module', type=str, required=True, help='模块名（procurement/contract/payment/supplier_eval）')
        parser.add_argument('--config', type=str, help='自定义配置文件路径')
        parser.add_argument('--dry-run', action='store_true', help='仅验证不导入')
        parser.add_argument('--batch-size', type=int, default=100, help='批量导入大小')
        parser.add_argument('--conflict', type=str, choices=['update', 'skip', 'error'], default='update', help='冲突处理策略')

    def handle(self, *args, **options):
        file_path = options['file']
        module = options['module']
        
        # 加载配置
        if options.get('config'):
            config_path = Path(options['config'])
        else:
            config_path = Path(__file__).parent.parent.parent.parent / 'project' / 'import_templates' / f'{module}.yml'
        
        if not config_path.exists():
            self.stdout.write(self.style.ERROR(f'配置文件不存在: {config_path}'))
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 获取模型
        model_name = config['metadata']['model']
        Model = apps.get_model(module, model_name)
        
        # 读取Excel
        import openpyxl
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        
        # 获取配置
        start_row = config['file']['start_row']
        header_row = start_row - 1
        fields_config = {f['name']: f for f in config['fields']}
        conflict_strategy = options.get('conflict', config['import'].get('conflict_strategy', 'update'))
        batch_size = options.get('batch_size', config['import'].get('batch_size', 100))
        
        # 读取表头映射
        header_map = {}
        for col_idx, cell in enumerate(ws[header_row], start=1):
            field_name = str(cell.value).strip().rstrip('*')
            if field_name in fields_config:
                header_map[col_idx] = fields_config[field_name]
        
        # 处理数据
        success_count = 0
        error_count = 0
        skip_count = 0
        
        for row_idx in range(start_row, ws.max_row + 1):
            row = ws[row_idx]
            
            # 跳过空行
            if all(cell.value is None for cell in row):
                continue
            
            # 提取数据
            data = {}
            for col_idx, field_config in header_map.items():
                cell_value = row[col_idx - 1].value
                field_name = field_config['field']
                
                # 数据转换和验证
                try:
                    data[field_name] = self._convert_value(cell_value, field_config)
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f'第{row_idx}行，字段"{field_config["name"]}"错误: {e}'))
                    error_count += 1
                    continue
            
            # 检查必填字段
            for field_config in config['fields']:
                if field_config.get('required') and not data.get(field_config['field']):
                    self.stdout.write(self.style.ERROR(f'第{row_idx}行，必填字段"{field_config["name"]}"为空'))
                    error_count += 1
                    continue
            
            # 导入数据
            if not options['dry_run']:
                try:
                    # 根据关键字段判断是否存在
                    key_fields = config['import'].get('key_fields', [])
                    filter_dict = {k: data[k] for k in key_fields if k in data}
                    
                    if filter_dict and Model.objects.filter(**filter_dict).exists():
                        if conflict_strategy == 'skip':
                            skip_count += 1
                            continue
                        elif conflict_strategy == 'error':
                            self.stdout.write(self.style.ERROR(f'第{row_idx}行，记录已存在'))
                            error_count += 1
                            continue
                        elif conflict_strategy == 'update':
                            Model.objects.filter(**filter_dict).update(**data)
                            success_count += 1
                    else:
                        Model.objects.create(**data)
                        success_count += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'第{row_idx}行导入失败: {e}'))
                    error_count += 1
        
        # 输出统计
        self.stdout.write(self.style.SUCCESS(f'\n导入完成:'))
        self.stdout.write(f'  成功: {success_count}')
        self.stdout.write(f'  跳过: {skip_count}')
        self.stdout.write(f'  失败: {error_count}')
    
    def _convert_value(self, value, field_config):
        """转换和验证字段值"""
        if value is None:
            return None
        
        data_type = field_config.get('data_type', 'string')
        
        if data_type == 'string':
            return str(value).strip()
        elif data_type == 'decimal':
            return float(value)
        elif data_type == 'date':
            from datetime import datetime
            if isinstance(value, datetime):
                return value.date()
            return datetime.strptime(str(value), field_config.get('format', '%Y-%m-%d')).date()
        elif data_type == 'choice':
            return str(value).strip()
        
        return value
```

---

### 步骤 5：重构数据清洗脚本（90 分钟）

**创建 `scripts/configs/data_cleanup.yml`**：

```yaml
# 数据清洗配置
input:
  default_path: "data/imports/raw_data.xlsx"
  encoding: "utf-8"
  
output:
  default_path: "data/imports/cleaned_data.xlsx"
  
# 列映射配置（使用列名而非索引）
column_mapping:
  procurement:
    "项目名称": "project_name"
    "采购方式": "procurement_method"
    "预算金额": "budget_amount"
    "中标供应商": "winning_supplier"
    "结果公示发布时间": "result_publicity_release_date"
  
  contract:
    "合同名称": "contract_name"
    "合同编号": "contract_code"
    "签订日期": "signing_date"
    "合同金额": "contract_amount"

# 数据清洗规则
cleanup_rules:
  - field: "budget_amount"
    rules:
      - type: "remove_non_numeric"
      - type: "convert_to_decimal"
  
  - field: "result_publicity_release_date"
    rules:
      - type: "parse_date"
        format: "%Y-%m-%d"
      - type: "validate_date_range"
        min_year: 2000
        max_year: 2030
  
  - field: "procurement_method"
    rules:
      - type: "trim"
      - type: "standardize_choices"
        mapping:
          "公开招标": "公开招标"
          "公开竞标": "公开招标"
          "邀请招标": "邀请招标"
```

**重构 `scripts/prepare_import_data.py`**：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据清洗脚本（配置驱动版本）
"""
import argparse
import yaml
from pathlib import Path
import openpyxl
from datetime import datetime
import re


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, config_path: str):
        """初始化清洗器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def clean_file(self, input_file: str, output_file: str = None, module: str = 'procurement'):
        """
        清洗数据文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            module: 模块名称
        """
        if output_file is None:
            output_file = self.config['output']['default_path']
        
        # 读取Excel
        wb = openpyxl.load_workbook(input_file)
        ws = wb.active
        
        # 获取列映射
        column_mapping = self.config['column_mapping'].get(module, {})
        
        # 找到列索引
        header_row = 1
        col_indices = {}
        for col_idx, cell in enumerate(ws[header_row], start=1):
            col_name = str(cell.value).strip()
            if col_name in column_mapping:
                col_indices[column_mapping[col_name]] = col_idx
        
        # 处理数据行
        for row_idx in range(2, ws.max_row + 1):
            for field_name, col_idx in col_indices.items():
                cell = ws.cell(row=row_idx, column=col_idx)
                
                # 应用清洗规则
                cleaned_value = self._apply_rules(cell.value, field_name)
                cell.value = cleaned_value
        
        # 保存
        wb.save(output_file)
        print(f"✓ 数据清洗完成: {output_file}")
    
    def _apply_rules(self, value, field_name):
        """应用清洗规则"""
        if value is None:
            return None
        
        # 查找字段规则
        rules = None
        for rule_config in self.config['cleanup_rules']:
            if rule_config['field'] == field_name:
                rules = rule_config['rules']
                break
        
        if not rules:
            return value
        
        # 依次应用规则
        result = value
        for rule in rules:
            rule_type = rule['type']
            
            if rule_type == 'trim':
                result = str(result).strip()
            
            elif rule_type == 'remove_non_numeric':
                result = re.sub(r'[^\d.]', '', str(result))
            
            elif rule_type == 'convert_to_decimal':
                try:
                    result = float(result) if result else None
                except ValueError:
                    result = None
            
            elif rule_type == 'parse_date':
                if isinstance(result, datetime):
                    result = result.date()
                else:
                    try:
                        result = datetime.strptime(str(result), rule.get('format', '%Y-%m-%d')).date()
                    except:
                        result = None
            
            elif rule_type == 'standardize_choices':
                mapping = rule.get('mapping', {})
                result = mapping.get(str(result), result)
        
        return result


def main():
    parser = argparse.ArgumentParser(description='数据清洗工具')
    parser.add_argument('input_file', help='输入Excel文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--module', '-m', default='procurement', help='模块名称')
    parser.add_argument('--config', '-c', help='配置文件路径')
    
    args = parser.parse_args()
    
    # 默认配置路径
    if args.config is None:
        config_path = Path(__file__).parent / 'configs' / 'data_cleanup.yml'
    else:
        config_path = Path(args.config)
    
    # 执行清洗
    cleaner = DataCleaner(config_path)
    cleaner.clean_file(args.input_file, args.output, args.module)


if __name__ == '__main__':
    main()
```

---

### 步骤 6：重构表统计脚本（60 分钟）

**创建 `scripts/configs/table_stats.yml`**：

```yaml
# 表统计配置
tables:
  - name: "procurement_procurement"
    display_name: "采购信息"
    module: "procurement"
    model: "Procurement"
    
  - name: "contract_contract"
    display_name: "合同信息"
    module: "contract"
    model: "Contract"
    
  - name: "payment_payment"
    display_name: "付款信息"
    module: "payment"
    model: "Payment"
    
  - name: "settlement_settlement"
    display_name: "结算信息"
    module: "settlement"
    model: "Settlement"
    
  - name: "supplier_eval_supplierevaluation"
    display_name: "供应商评价"
    module: "supplier_eval"
    model: "SupplierEvaluation"
    
  - name: "project_project"
    display_name: "项目信息"
    module: "project"
    model: "Project"
```

**重构 `scripts/check_table_data.py`**：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
表数据统计脚本（配置驱动版本）
"""
import os
import sys
import yaml
import argparse
from pathlib import Path

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.apps import apps


def load_config(config_path: str = None):
    """加载配置"""
    if config_path is None:
        config_path = Path(__file__).parent / 'configs' / 'table_stats.yml'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_table_stats(config_path: str = None, verbose: bool = False):
    """检查表数据统计"""
    config = load_config(config_path)
    
    print('=' * 60)
    print('数据库表统计')
    print('=' * 60)
    
    total_records = 0
    
    for table_config in config['tables']:
        module_name = table_config['module']
        model_name = table_config['model']
        display_name = table_config['display_name']
        
        try:
            Model = apps.get_model(module_name, model_name)
            count = Model.objects.count()
            total_records += count
            
            status = "✓" if count > 0 else "○"
            print(f"{status} {display_name:12} : {count:6} 条")
            
            if verbose and count > 0:
                # 显示详细信息
                print(f"   表名: {table_config['name']}")
                print(f"   最新记录: {Model.objects.last()}")
                
        except Exception as e:
            print(f"✗ {display_name:12} : 错误 - {e}")
    
    print('=' * 60)
    print(f"总计: {total_records} 条记录")
    print('=' * 60)


def main():
    parser = argparse.ArgumentParser(description='表数据统计工具')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    check_table_stats(args.config, args.verbose)


if __name__ == '__main__':
    main()
```

---

## 4. 测试计划

### 4.1 模板生成测试



```bash
# 测试模板生成
python manage.py shell
>>> from project.template_generator import generate_all_templates
>>> generate_all_templates('data/exports', 2025)
```

### 4.2 导入命令测试

```bash
# 测试采购数据导入
python manage.py import_excel data/test/procurement_sample.xlsx --module procurement --dry-run

# 实际导入
python manage.py import_excel data/test/procurement_sample.xlsx --module procurement --conflict update
```

### 4.3 数据清洗测试

```bash
# 测试数据清洗
python scripts/prepare_import_data.py data/test/raw_data.xlsx -o data/test/cleaned.xlsx -m procurement
```

### 4.4 表统计测试

```bash
# 测试表统计
python scripts/check_table_data.py --verbose
```

---

## 5. 实施时间表

| 阶段 | 任务 | 预计时间 | 状态 |
|------|------|----------|------|
| **设计** | 设计模板配置格式 | 60 分钟 | ⬜ 待开始 |
| **开发** | 实现模板生成器 | 120 分钟 | ⬜ 待开始 |
| **开发** | 重构视图层逻辑 | 90 分钟 | ⬜ 待开始 |
| **开发** | 重构导入命令 | 120 分钟 | ⬜ 待开始 |
| **开发** | 重构数据清洗脚本 | 90 分钟 | ⬜ 待开始 |
| **开发** | 重构表统计脚本 | 60 分钟 | ⬜ 待开始 |
| **测试** | 集成测试 | 120 分钟 | ⬜ 待开始 |
| **文档** | 编写配置指南 | 60 分钟 | ⬜ 待开始 |
| **总计** | | **12-15 小时** | |

---

## 6. 成功标准

- [ ] 所有导入模板通过配置生成
- [ ] 导入命令支持配置文件
- [ ] 数据清洗脚本使用列名而非索引
- [ ] 表统计脚本配置驱动
- [ ] 新增模块无需修改核心代码

---

# 第三阶段实施方案：界面与枚举组件化

## 执行摘要

本阶段针对 HC-05、HC-06、HC-10 问题，实施 Admin 配置和筛选器的组件化改造，预计耗时 8-10 小时。

**关键成果**：
- 抽象 BaseAuditAdmin 统一管理后台配置
- 筛选器配置注册式管理
- 业务枚举单点定义和复用
- 减少重复代码，提升可维护性

---

## 1. 问题分析

### 1.1 HC-05：Admin 配置分散重复

**当前状况**：
- `procurement/admin.py`、`contract/admin.py`、`payment/admin.py` 等重复定义分页、审计字段配置
- 相同的返回前端逻辑重复实现

**风险等级**：🟠 高
- 违反 DRY 原则
- 统一修改困难

### 1.2 HC-06：筛选器配置硬编码

**当前状况**：
- `project/filter_config.py:34-215` 重复枚举模型 choices
- 字段配置分散，不易维护

**风险等级**：🟠 高
- 枚举变更需多处修改
- 违反 DRY 原则

### 1.3 HC-10：枚举重复定义

**当前状况**：
- 合同、评估等枚举在多处重复定义
- 模型、筛选器、模板说明等都有硬编码

**风险等级**：🟡 中
- 增加维护成本
- 易出现不一致

---

## 2. 解决方案设计

### 2.1 架构设计

```
project/
├── project/
│   ├── admin_base.py                 # Admin 基类（新建）
│   ├── enums.py                      # 业务枚举统一定义（新建）
│   ├── filter_registry.py           # 筛选器注册中心（新建）
│   └── filter_config.py             # 筛选器配置（重构）
├── procurement/
│   └── admin.py                      # 采购Admin（重构）
├── contract/
│   └── admin.py                      # 合同Admin（重构）
└── payment/
    └── admin.py                      # 付款Admin（重构）
```

---

## 3. 详细实施步骤

### 步骤 1：创建业务枚举模块（45 分钟）

**创建 `project/enums.py`**：

```python
"""
业务枚举统一定义
所有业务枚举集中在此管理，供模型、表单、筛选器、模板等使用
"""
from django.db import models


class ProcurementMethod(models.TextChoices):
    """采购方式"""
    PUBLIC_BIDDING = 'PUBLIC_BIDDING', '公开招标'
    INVITED_BIDDING = 'INVITED_BIDDING', '邀请招标'
    COMPETITIVE_NEGOTIATION = 'COMPETITIVE_NEGOTIATION', '竞争性谈判'
    COMPETITIVE_CONSULTATION = 'COMPETITIVE_CONSULTATION', '竞争性磋商'
    SINGLE_SOURCE = 'SINGLE_SOURCE', '单一来源'
    INQUIRY = 'INQUIRY', '询价'


class ContractType(models.TextChoices):
    """合同类型"""
    PROCUREMENT = 'PROCUREMENT', '采购合同'
    SERVICE = 'SERVICE', '服务合同'
    CONSTRUCTION = 'CONSTRUCTION', '工程合同'
    OTHER = 'OTHER', '其他合同'


class FilePositioning(models.TextChoices):
    """文件定位"""
    PROCUREMENT = 'PROCUREMENT', '采购文件'
    CONTRACT = 'CONTRACT', '合同文件'
    PAYMENT = 'PAYMENT', '付款文件'
    EVALUATION = 'EVALUATION', '评价文件'


class PaymentStatus(models.TextChoices):
    """付款状态"""
    PENDING = 'PENDING', '待付款'
    PARTIAL = 'PARTIAL', '部分付款'
    COMPLETED = 'COMPLETED', '已完成'
    CANCELLED = 'CANCELLED', '已取消'


class EvaluationLevel(models.TextChoices):
    """评价等级"""
    EXCELLENT = 'EXCELLENT', '优秀'
    GOOD = 'GOOD', '良好'
    QUALIFIED = 'QUALIFIED', '合格'
    UNQUALIFIED = 'UNQUALIFIED', '不合格'


# 枚举辅助函数
def get_enum_choices(enum_class):
    """获取枚举的 choices 列表"""
    return [(choice.value, choice.label) for choice in enum_class]


def get_enum_display_dict(enum_class):
    """获取枚举的显示字典"""
    return {choice.value: choice.label for choice in enum_class}


def get_enum_values(enum_class):
    """获取枚举的所有值"""
    return [choice.value for choice in enum_class]
```

---

### 步骤 2：创建 Admin 基类（60 分钟）

**创建 `project/admin_base.py`**：

```python
"""
Django Admin 基类
统一管理审计字段、分页、返回链接等通用配置
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse


class BaseAuditAdmin(admin.ModelAdmin):
    """
    审计模型基类 Admin
    包含创建/更新时间和用户等审计字段的通用配置
    """
    
    # 分页配置
    list_per_page = 50
    
    # 审计字段（只读）
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    # 日期过滤
    date_hierarchy = 'created_at'
    
    def get_readonly_fields(self, request, obj=None):
        """动态设置只读字段"""
        readonly = list(super().get_readonly_fields(request, obj))
        
        # 编辑时，ID字段也设为只读
        if obj:
            readonly.append('id')
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """保存时自动设置创建/更新用户"""
        if not change:  # 新建
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_list_display(self, request):
        """获取列表显示字段（子类可覆盖）"""
        return self.list_display
    
    def get_fieldsets(self, request, obj=None):
        """
        获取字段分组
        子类应实现 get_main_fieldsets() 返回主要字段
        """
        main_fieldsets = self.get_main_fieldsets(request, obj)
        
        # 添加审计信息分组
        audit_fieldset = ('审计信息', {
            'classes': ('collapse',),
            'fields': self.readonly_fields
        })
        
        return main_fieldsets + (audit_fieldset,)
    
    def get_main_fieldsets(self, request, obj=None):
        """
        子类需要实现此方法，返回主要字段的分组
        例如：
        return (
            ('基本信息', {'fields': ('name', 'code')}),
            ('详细信息', {'fields': ('description',)}),
        )
        """
        raise NotImplementedError("子类必须实现 get_main_fieldsets 方法")


class BusinessModelAdmin(BaseAuditAdmin):
    """
    业务模型基类 Admin
    在审计基类上增加关联跳转、高级搜索等功能
    """
    
    # 搜索字段（子类覆盖）
    search_fields = []
    
    # 列表过滤（子类覆盖）
    list_filter = []
    
    # 可排序字段
    sortable_by = []
    
    def get_related_link(self, obj, field_name, display_text=None):
        """
        生成关联对象的链接
        
        Args:
            obj: 当前对象
            field_name: 关联字段名
            display_text: 显示文本（默认使用对象的 __str__）
        
        Returns:
            HTML 链接或 '-'
        """
        related_obj = getattr(obj, field_name, None)
        if not related_obj:
            return '-'
        
        # 获取关联对象的 Admin URL
        app_label = related_obj._meta.app_label
        model_name = related_obj._meta.model_name
        url = reverse(f'admin:{app_label}_{model_name}_change', args=[related_obj.pk])
        
        # 显示文本
        text = display_text or str(related_obj)
        
        return format_html('<a href="{}">{}</a>', url, text)
    
    def get_back_link(self, request):
        """生成返回列表的链接"""
        referer = request.META.get('HTTP_REFERER', '')
        if 'changelist' in referer:
            return format_html('<a href="{}">← 返回列表</a>', referer)
        return ''
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """添加返回链接到上下文"""
        extra_context = extra_context or {}
        extra_context['back_link'] = self.get_back_link(request)
        return super().change_view(request, object_id, form_url, extra_context)
```

---

### 步骤 3：重构 Admin 配置（90 分钟）

**修改 `procurement/admin.py`**：

```python
from django.contrib import admin
from project.admin_base import BusinessModelAdmin
from project.enums import ProcurementMethod
from .models import Procurement


@admin.register(Procurement)
class ProcurementAdmin(BusinessModelAdmin):
    """采购信息管理"""
    
    list_display = [
        'id', 'procurement_code', 'project_link', 'procurement_method',
        'budget_amount', 'winning_supplier', 'result_publicity_release_date'
    ]
    
    search_fields = ['procurement_code', 'project__project_name', 'winning_supplier']
    
    list_filter = ['procurement_method', 'result_publicity_release_date']
    
    def get_main_fieldsets(self, request, obj=None):
        """主要字段分组"""
        return (
            ('基本信息', {
                'fields': ('procurement_code', 'project', 'procurement_method')
            }),
            ('金额信息', {
                'fields': ('budget_amount',)
            }),
            ('中标信息', {
                'fields': ('winning_supplier', 'result_publicity_release_date')
            }),
        )
    
    @admin.display(description='关联项目', ordering='project__project_name')
    def project_link(self, obj):
        """项目链接"""
        return self.get_related_link(obj, 'project')
```

**类似地修改 `contract/admin.py` 和 `payment/admin.py`**。

---

### 步骤 4：重构筛选器配置（90 分钟）

**创建 `project/filter_registry.py`**：

```python
"""
筛选器注册中心
动态管理各模块的筛选器配置
"""
from typing import Dict, List, Any
from project.enums import *


class FilterRegistry:
    """筛选器注册中心"""
    
    def __init__(self):
        self._filters = {}
    
    def register(self, module_name: str, filters: List[Dict[str, Any]]):
        """
        注册筛选器
        
        Args:
            module_name: 模块名称
            filters: 

筛选器配置列表
        """
        self._filters[module_name] = filters
    
    def get_filters(self, module_name: str) -> List[Dict[str, Any]]:
        """获取指定模块的筛选器配置"""
        return self._filters.get(module_name, [])
    
    def get_all_modules(self) -> List[str]:
        """获取所有已注册的模块"""
        return list(self._filters.keys())


# 全局注册实例
filter_registry = FilterRegistry()


# 注册采购模块筛选器
filter_registry.register('procurement', [
    {
        'key': 'procurement_method',
        'label': '采购方式',
        'type': 'select',
        'enum': ProcurementMethod,
        'field': 'procurement_method'
    },
    {
        'key': 'budget_range',
        'label': '预算范围',
        'type': 'range',
        'field': 'budget_amount',
        'data_type': 'decimal'
    },
    {
        'key': 'date_range',
        'label': '公示日期',
        'type': 'date_range',
        'field': 'result_publicity_release_date'
    }
])


# 注册合同模块筛选器
filter_registry.register('contract', [
    {
        'key': 'contract_type',
        'label': '合同类型',
        'type': 'select',
        'enum': ContractType,
        'field': 'contract_type'
    },
    {
        'key': 'file_positioning',
        'label': '文件定位',
        'type': 'select',
        'enum': FilePositioning,
        'field': 'file_positioning'
    }
])


# 注册付款模块筛选器
filter_registry.register('payment', [
    {
        'key': 'payment_status',
        'label': '付款状态',
        'type': 'select',
        'enum': PaymentStatus,
        'field': 'payment_status'
    }
])
```

**重构 `project/filter_config.py`**：

```python
"""
筛选器配置（重构版）
基于注册中心动态生成筛选器选项
"""
from project.filter_registry import filter_registry
from project.enums import get_enum_display_dict


def get_filter_options(module_name: str):
    """
    获取指定模块的筛选器选项
    
    Args:
        module_name: 模块名称
    
    Returns:
        筛选器配置字典
    """
    filters = filter_registry.get_filters(module_name)
    options = {}
    
    for filter_config in filters:
        key = filter_config['key']
        filter_type = filter_config['type']
        
        if filter_type == 'select' and 'enum' in filter_config:
            # 从枚举类动态生成选项
            enum_class = filter_config['enum']
            options[key] = {
                'label': filter_config['label'],
                'type': 'select',
                'choices': get_enum_display_dict(enum_class)
            }
        
        elif filter_type == 'range':
            options[key] = {
                'label': filter_config['label'],
                'type': 'range',
                'data_type': filter_config.get('data_type', 'number')
            }
        
        elif filter_type == 'date_range':
            options[key] = {
                'label': filter_config['label'],
                'type': 'date_range'
            }
    
    return options
```

---

## 4. 测试计划

### 4.1 Admin 测试

```bash
# 访问 Admin 后台测试
# 1. 检查各模块 Admin 页面正常显示
# 2. 验证审计字段自动填充
# 3. 测试关联对象跳转
# 4. 验证返回列表链接
```

### 4.2 筛选器测试

```python
# 测试筛选器配置
from project.filter_config import get_filter_options

# 获取采购模块筛选器
options = get_filter_options('procurement')
print(options)
```

---

## 5. 实施时间表

| 阶段 | 任务 | 预计时间 | 状态 |
|------|------|----------|------|
| **开发** | 创建业务枚举模块 | 45 分钟 | ⬜ 待开始 |
| **开发** | 创建 Admin 基类 | 60 分钟 | ⬜ 待开始 |
| **开发** | 重构 Admin 配置 | 90 分钟 | ⬜ 待开始 |
| **开发** | 重构筛选器配置 | 90 分钟 | ⬜ 待开始 |
| **开发** | 更新模型引用枚举 | 60 分钟 | ⬜ 待开始 |
| **测试** | 功能测试 | 60 分钟 | ⬜ 待开始 |
| **文档** | 更新开发文档 | 45 分钟 | ⬜ 待开始 |
| **总计** | | **8-10 小时** | |

---

## 6. 成功标准

- [ ] 所有 Admin 继承自基类
- [ ] 业务枚举单点定义
- [ ] 筛选器配置注册式管理
- [ ] 消除重复的 choices 定义
- [ ] 审计字段自动管理

---

# 第四阶段实施方案：帮助文案与示例数据配置

## 执行摘要

本阶段针对 HC-11、HC-12 问题，实施帮助文案和示例数据的配置化，预计耗时 4-6 小时。

**关键成果**：
- 帮助文案集中管理
- 示例数据可配置
- 支持多环境差异化配置
- 便于国际化扩展

---

## 1. 问题分析

### 1.1 HC-11：模板说明写死常见选项

**当前状况**：
- `project/views.py:205` 导入模板说明中硬编码"采购方式"等选项
- 枚举变更需改代码

**风险等级**：🟡 中
- 枚举调整需要改代码
- 难以定制化

### 1.2 HC-12：模型帮助文本硬编码示例

**当前状况**：
- `procurement/models.py:171, 189` 硬编码示例电话、姓名
- 不利于外部发布

**风险等级**：🟡 中
- 示例数据可能泄露信息
- 按场景调整困难

---

## 2. 解决方案设计

### 2.1 架构设计

```
project/
├── project/
│   ├── helptext.py                   # 帮助文案配置（新建）
│   └── configs/
│       └── helptexts.yml             # 帮助文案配置文件（新建）
├── procurement/
│   └── models.py                     # 模型（修改）
└── contract/
    └── models.py                     # 模型（修改）
```

---

## 3. 详细实施步骤

### 步骤 1：创建帮助文案配置（60 分钟）

**创建 `project/configs/helptexts.yml`**：

```yaml
# 帮助文案配置
# 可根据部署环境自定义示例数据

contacts:
  default:
    name: "张三"
    phone: "138****8888"
    email: "zhangsan@example.com"
  
  production:
    name: "联系人姓名"
    phone: "联系电话"
    email: "电子邮箱"

fields:
  procurement:
    contact_person:
      label: "联系人"
      help_text: "采购项目联系人姓名，示例：{contact_name}"
      placeholder: "请输入联系人姓名"
    
    contact_phone:
      label: "联系电话"
      help_text: "联系人电话号码，示例：{contact_phone}"
      placeholder: "请输入联系电话"
    
    procurement_method:
      label: "采购方式"
      help_text: "采购方式类型，可选：{procurement_method_choices}"
  
  contract:
    party_a_contact:
      label: "甲方联系人"
      help_text: "合同甲方联系人，示例：{contact_name}"
    
    party_b_contact:
      label: "乙方联系人"
      help_text: "合同乙方联系人，示例：{contact_name}"

messages:
  import:
    procurement_template: |
      导入说明：
      1. 请勿修改表头行的列名和顺序
      2. 必填字段不能为空
      3. 采购方式可选值：{procurement_method_choices}
      4. 日期格式：YYYY-MM-DD
      5. 金额单位：元
```

**创建 `project/helptext.py`**：

```python
"""
帮助文案管理
集中管理所有帮助文本和示例数据
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from django.conf import settings
from project.enums import *


class HelpTextManager:
    """帮助文案管理器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.environment = self._get_environment()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(__file__).parent / 'configs' / 'helptexts.yml'
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_environment(self) -> str:
        """获取当前环境"""
        debug = getattr(settings, 'DEBUG', True)
        return 'default' if debug else 'production'
    
    def get_contact_example(self, field: str) -> str:
        """
        获取联系人示例
        
        Args:
            field: 字段名（name/phone/email）
        
        Returns:
            示例值
        """
        contacts = self.config['contacts']
        env_contacts = contacts.get(self.environment, contacts['default'])
        return env_contacts.get(field, '')
    
    def get_field_config(self, module: str, field: str) -> Dict[str, str]:
        """
        获取字段配置
        
        Args:
            module: 模块名
            field: 字段名
        
        Returns:
            字段配置字典
        """
        fields = self.config.get('fields', {})
        module_fields = fields.get(module, {})
        field_config = module_fields.get(field, {})
        
        # 替换占位符
        return self._replace_placeholders(field_config)
    
    def get_help_text(self, module: str, field: str) -> str:
        """获取字段的帮助文本"""
        config = self.get_field_config(module, field)
        return config.get('help_text', '')
    
    def get_message(self, category: str, key: str) -> str:
        """
        获取消息文本
        
        Args:
            category: 消息类别
            key: 消息键
        
        Returns:
            消息文本
        """
        messages = self.config.get('messages', {})
        category_messages = messages.get(category, {})
        message = category_messages.get(key, '')
        
        return self._replace_placeholders({'text': message})['text']
    
    def _replace_placeholders(self, config: Dict) -> Dict:
        """替换配置中的占位符"""
        result = {}
        
        for key, value in config.items():
            if isinstance(value, str):
                # 替换联系人占位符
                value = value.replace('{contact_name}', self.get_contact_example('name'))
                value = value.replace('{contact_phone}', self.get_contact_example('phone'))
                value = value.replace('{contact_email}', self.get_contact_example('email'))
                
                # 替换枚举占位符
                value = self._replace_enum_placeholders(value)
            
            result[key] = value
        
        return result
    
    def _replace_enum_placeholders(self, text: str) -> str:
        """替换枚举占位符"""
        # 采购方式
        if '{procurement_method_choices}' in text:
            choices = '、'.join([label for _, label in ProcurementMethod.choices])
            text = text.replace('{procurement_method_choices}', choices)
        
        # 合同类型
        if '{contract_type_choices}' in text:
            choices = '、'.join([label for _, label in ContractType.choices])
            text = text.replace('{contract_type_choices}', choices)
        
        # 付款状态
        if '{payment_status_choices}' in text:
            choices = '、'.join([label for _, label in PaymentStatus.choices])
            text = text.replace('{payment_status_choices}', choices)
        
        return text


# 全局实例
helptext_manager = HelpTextManager()


# 便捷函数
def get_help_text(module: str, field: str) -> str:
    """获取帮助文本的快捷函数"""
    return helptext_manager.get_help_text(module, field)


def get_message(category: str, key: str) -> str:
    """获取消息文本的快捷函数"""
    return helptext_manager.get_message(category, key)
```

---

### 步骤 2：更新模型定义（60 分钟）

**修改 `procurement/models.py`**：

```python
from django.db import models
from project.helptext import get_help_text
from project.enums import ProcurementMethod


class Procurement(models.Model):
    """采购信息模型"""
    
    procurement_code = models.CharField(
        max_length=50,
        verbose_name="采购编号"
    )
    
    procurement_method = models.CharField(
        max_length=50,
        choices=ProcurementMethod.choices,
        verbose_name="采购方式",
        help_text=get_help_text('procurement', 'procurement_method')
    )
    
    contact_person = models.CharField(
        max_length=50,
        verbose_name="联系人",
        help_text=get_help_text('procurement', 'contact_person'),
        blank=True
    )
    
    contact_phone = models.CharField(
        max_length=20,
        verbose_name="联系电话",
        help_text=get_help_text('procurement', 'contact_phone'),
        blank=True
    )
    
    # ... 其他字段
```

**类似地修改 `contract/models.py`**。

---

### 步骤 3：更新模板生成逻辑（45 分钟）

**修改 `project/template_generator.py`**：

```python
from project.helptext import get_message

class TemplateGenerator:
    # ... 现有代码
    
    def _format_instructions(self) -> str:
        """格式化说明文本"""
        module = self.config['metadata']['module']
        
        # 从配置获取说明模板
        instructions = get_message('import', f'{module}_template')
        
        return instructions
```

---

### 步骤 4：创建配置验证脚本（30 分钟）

**创建 

`scripts/validate_helptext.py`**：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
帮助文案配置验证脚本
检查配置文件的完整性和占位符
"""
import os
import sys
from pathlib import Path

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from project.helptext import helptext_manager


def validate_config():
    """验证配置"""
    print("=" * 60)
    print("帮助文案配置验证")
    print("=" * 60)
    
    config = helptext_manager.config
    issues = []
    
    # 检查联系人配置
    print("\n检查联系人配置...")
    for env in ['default', 'production']:
        if env not in config.get('contacts', {}):
            issues.append(f"缺少 {env} 环境的联系人配置")
        else:
            contacts = config['contacts'][env]
            for field in ['name', 'phone', 'email']:
                if field not in contacts:
                    issues.append(f"{env} 环境缺少联系人字段: {field}")
    
    # 检查字段配置
    print("检查字段配置...")
    modules = ['procurement', 'contract', 'payment']
    for module in modules:
        if module not in config.get('fields', {}):
            issues.append(f"缺少模块 {module} 的字段配置")
    
    # 检查消息配置
    print("检查消息配置...")
    if 'import' not in config.get('messages', {}):
        issues.append("缺少导入消息配置")
    
    # 输出结果
    print("\n" + "=" * 60)
    if issues:
        print("❌ 发现以下问题：")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ 配置验证通过")
        
        # 显示示例
        print("\n示例文案：")
        print(f"  联系人: {helptext_manager.get_contact_example('name')}")
        print(f"  电话: {helptext_manager.get_contact_example('phone')}")
        print(f"  采购方式帮助: {helptext_manager.get_help_text('procurement', 'procurement_method')}")
        
        return True


if __name__ == '__main__':
    success = validate_config()
    sys.exit(0 if success else 1)
```

---

## 4. 测试计划

### 4.1 帮助文案测试

```python
# 测试帮助文案
from project.helptext import get_help_text, get_message

# 获取字段帮助文本
help_text = get_help_text('procurement', 'contact_person')
print(help_text)

# 获取消息
message = get_message('import', 'procurement_template')
print(message)
```

### 4.2 环境差异测试

```bash
# 测试开发环境
python manage.py shell
>>> from project.helptext import helptext_manager
>>> print(helptext_manager.environment)
>>> print(helptext_manager.get_contact_example('name'))

# 测试生产环境（设置 DEBUG=False）
```

---

## 5. 实施时间表

| 阶段 | 任务 | 预计时间 | 状态 |
|------|------|----------|------|
| **开发** | 创建帮助文案配置 | 60 分钟 | ⬜ 待开始 |
| **开发** | 更新模型定义 | 60 分钟 | ⬜ 待开始 |
| **开发** | 更新模板生成逻辑 | 45 分钟 | ⬜ 待开始 |
| **开发** | 创建配置验证脚本 | 30 分钟 | ⬜ 待开始 |
| **测试** | 功能测试 | 45 分钟 | ⬜ 待开始 |
| **文档** | 更新配置指南 | 30 分钟 | ⬜ 待开始 |
| **总计** | | **4-6 小时** | |

---

## 6. 成功标准

- [ ] 帮助文案集中配置管理
- [ ] 示例数据可按环境差异化
- [ ] 模型 help_text 使用配置
- [ ] 枚举选项自动注入说明
- [ ] 配置验证脚本完善

---

# 全阶段总结

## 实施路线图

```
第一阶段（2-3小时）
  ↓
基础配置完成
  ↓
第二阶段（12-15小时）
  ↓
模板与脚本配置化
  ↓
第三阶段（8-10小时）
  ↓
界面组件化
  ↓
第四阶段（4-6小时）
  ↓
全面配置化完成
```

## 总耗时估算

| 阶段 | 预计耗时 | 累计耗时 |
|------|----------|----------|
| 第一阶段 | 2-3 小时 | 2-3 小时 |
| 第二阶段 | 12-15 小时 | 14-18 小时 |
| 第三阶段 | 8-10 小时 | 22-28 小时 |
| 第四阶段 | 4-6 小时 | 26-34 小时 |

**总计：26-34 小时**（约 3-5 个工作日）

---

## 原则落实总结

### KISS（简单至上）
- ✅ 配置文件使用简单的 YAML 格式
- ✅ 每个工具函数职责单一
- ✅ 避免引入复杂框架

### YAGNI（精益求精）
- ✅ 仅实现当前明确需求
- ✅ 不做过度设计
- ✅ 按需扩展

### SOLID
- ✅ **S**：每个类单一职责
- ✅ **O**：通过配置扩展功能
- ✅ **L**：基类可被子类安全替换
- ✅ **I**：接口精简专一
- ✅ **D**：依赖配置抽象而非具体实现

### DRY（杜绝重复）
- ✅ 年份范围单点定义
- ✅ 枚举统一管理
- ✅ Admin 配置复用基类
- ✅ 帮助文案集中配置

---

## 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 配置文件格式错误 | 高 | 提供验证脚本，部署前检查 |
| 向后兼容性问题 | 中 | 保持默认值，渐进式迁移 |
| 学习曲线 | 低 | 提供详细文档和示例 |
| 测试覆盖不足 | 中 | 每阶段独立测试验证 |

---

## 后续优化建议

1. **配置中心化**
   - 如果配置项继续增长，考虑引入配置管理系统
   - 支持配置版本管理和审计

2. **国际化支持**
   - 帮助文案模块可扩展支持多语言
   - 使用 Django i18n 框架

3. **配置 UI 化**
   - 开发配置管理界面
   - 支持在线修改和预览

4. **监控告警**
   - 配置变更通知
   - 异常配置自动检测

---

## 文档清单

完成所有阶段后，需要更新以下文档：

- [ ] `docs/配置管理指南.md` - 配置项说明和使用指南
- [ ] `docs/导入模板配置指南.md` - 模板配置详细说明
- [ ] `docs/开发实践指南.md` - 添加配置化开发规范
- [ ] `README.md` - 更新部署和配置说明
- [ ] `.env.example` - 完整的环境变量模板

---

**文档版本**：v3.0（完整四阶段方案）  
**创建日期**：2025-10-27  
**最后更新**：2025-10-27  
**文档状态**：待审批  
**适用范围**：测试环境 → 生产环境渐进式推进
