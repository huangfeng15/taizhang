# 时间区间筛选功能设计方案（草案）

> 适用项目路径：`D:\develop\new pachong yangguangcaigou\taizhang`  
> 适用模块：全局筛选 + 各业务列表 / 统计视图（Django）

---

## 1. 背景与目标

### 1.1 当前能力

- 顶部「全局筛选」条（年度 + 项目）：
  - 模板：`project/templates/base.html:742`
  - 前端状态：`window.GlobalFilterStore`  
    - 定义文件：`project/static/js/global-filter-store.js`
  - 行为组件：`project/static/js/global-filter-component.js`
- 后端统一解析全局筛选：
  - 新版通用：`project/views_helpers.py:_resolve_global_filters`
  - 某些模块有自己的版本，例如：`supplier_eval/views.py:_resolve_global_filters`
- 使用方式：
  - 全局筛选通过 query 参数 `global_year` / `global_project` 同步到各页面；
  - 各视图通过 `_resolve_global_filters(request)` 拿到：
    - `year_filter`（具体年份或 None 表示全部年度）
    - `project_list`（选定项目编码列表）

### 1.2 新需求

- 在某一年度下，进一步按**时间区间**查看数据，例如：
  - 最近 1 个月
  - 最近 3 个月
  - 最近半年
- 关注重点：
  - 能方便查看近期业务动态（近 1–2 个月）；
  - 不明显破坏现有布局（尤其是顶部全局筛选条）；
  - 实现成本可控，便于迭代。

---

## 2. 设计原则（KISS / YAGNI / DRY / SOLID）

- **KISS（简单至上）**
  - 顶部全局筛选只负责“年度 + 项目”，保持语义清晰；
  - 时间区间下沉到具体业务页面，由页面自己决定展示粒度。
- **YAGNI（避免过度设计）**
  - 第一阶段只支持固定时间区间（近 1 / 3 / 6 个月 + 全年）；
  - 自定义日期范围等复杂功能留到后续需要时再做。
- **DRY（避免重复）**
  - 时间区间的解析逻辑抽成工具函数，在多个视图中复用；
  - `time_range` 参数命名和前端 UI 形态尽量统一。
- **SOLID（单一职责等）**
  - 全局筛选组件继续只管理“全局范围”（年度 / 项目）；
  - 各业务视图只按各自业务字段（如合同签署时间、付款时间）解释时间区间。

---

## 3. 总体方案概览

### 3.1 不建议的方案（仅说明）

- **在顶部「全局筛选」中直接增加时间区间选项**
  - 需要修改：
    - `GlobalFilterStore` 状态结构；
    - `global-filter-component.js` 的 URL 同步逻辑；
    - 所有依赖 `_resolve_global_filters` 的视图；
  - 交互问题：
    - 顶部横条已包括“系统标题 + 全局筛选（2 个下拉）+ 用户信息”，再加一组时间区间选项会非常拥挤；
    - 容易混淆“年度”和“时间区间”的语义（例如：2024 年 + 最近 3 个月，是指 2024 内的 3 个月还是跨年度的绝对最近 3 个月？）。

> 结论：**不推荐**在全局筛选条中加入时间区间。

---
## 3.2 推荐主方案：业务页面局部时间区间筛选

在**关键业务页面**（例如：统计分析页、合同列表、付款列表、供应商履约评价列表等）增加局部时间区间筛选。

- 全局筛选：仍然决定“查看哪一年度 + 哪个项目范围”的数据；
- 页面局部时间区间筛选：决定在该视图中看“该年度全年”还是“近期 N 个月”。

### 3.2.1 交互形态建议

以“供应商履约评价列表”为例：

- 视图文件：`supplier_eval/views.py:79`（`supplier_evaluation_list`）
- 模板文件：`supplier_eval/templates/supplier/evaluation_list.html`

在页面现有筛选区域（搜索框 + 评分等级下拉）右侧添加一个时间区间控件：

- **下拉菜单形式**（简单版）：

  - 字段名：`time_range`
  - 选项：
    - `year`：当前年度（默认）
    - `last_1m`：最近 1 个月
    - `last_3m`：最近 3 个月
    - `last_6m`：最近 6 个月

- **按钮组形式**（更直观，可选）：

  - 按钮：
    - `全年`（默认，对应 `year`）
    - `近 1 月`
    - `近 3 月`
    - `近 6 月`
  - 点击后用 JS 提交表单或跳转带 `time_range` 参数。

其它页面（如：合同列表、付款列表、统计分析页）可复用同样的 UI 模式，保持一致。

### 3.2.2 后端时间区间解析工具函数（建议新增）

建议在 `project/utils/filters.py` 中增加一个通用函数，例如：

```python
# 文件：project/utils/filters.py（建议新增）

from datetime import date, timedelta
from django.utils import timezone

def resolve_time_range(request, year_filter: int | None):
    """
    解析列表视图中使用的时间区间。

    参数:
        request: Django HttpRequest
        year_filter: 来自全局筛选解析的年份（int）或 None 表示全部年度

    返回:
        {
            "time_range": str,       # "year" | "last_1m" | "last_3m" | "last_6m"
            "start_date": date | None,
            "end_date": date | None,
        }
    """
    choice = (request.GET.get("time_range") or "year").strip()
    today = timezone.now().date()

    # 默认截止时间为今天（可按需要调整）
    end_date = today

    if choice == "last_1m":
        start_date = today - timedelta(days=30)
    elif choice == "last_3m":
        start_date = today - timedelta(days=90)
    elif choice == "last_6m":
        start_date = today - timedelta(days=180)
    else:
        # 默认按“年度”视角
        if year_filter:
            start_date = date(year_filter, 1, 1)
        else:
            start_date = None  # 不限定开始日期

        choice = "year"  # 规范化返回值

    return {
        "time_range": choice,
        "start_date": start_date,
        "end_date": end_date,
    }
```

> 说明：
> - 该函数**不直接访问数据库**，只负责把 query 参数转换为可用的日期区间；
> - 各业务视图自行决定使用哪个日期字段过滤（如 `created_at`、`sign_date`、`payment_date` 等）。

### 3.2.3 在视图中的典型用法示例

以供应商履约评价列表为例：

- 位置：`supplier_eval/views.py:supplier_evaluation_list`

示例修改思路（伪代码，仅描述关键新增逻辑）：

```python
from project.utils.filters import resolve_time_range

@login_required
@require_http_methods(['GET'])
def supplier_evaluation_list(request):
    # 已有逻辑：解析全局筛选
    global_filters = _resolve_global_filters(request)
    year_filter = global_filters['year_filter']
    year_value = global_filters['year_value']
    project_list = global_filters['project_list']

    # 新增：解析时间区间
    time_ctx = resolve_time_range(request, year_filter)
    time_range_value = time_ctx['time_range']
    start_date = time_ctx['start_date']
    end_date = time_ctx['end_date']

    # 已有：获取最新评价列表
    latest_evaluations = SupplierAnalysisService.get_latest_evaluations_by_year(year_filter)

    # 新增：时间区间过滤（示例，以 evaluation.created_at 为准）
    if start_date:
        latest_evaluations = [
            item for item in latest_evaluations
            if item['evaluation'].created_at.date() >= start_date
            and item['evaluation'].created_at.date() <= end_date
        ]

    # ... 原有项目筛选、搜索、评分过滤逻辑不变 ...

    context = {
        # ...
        'time_range': time_range_value,  # 传给模板做选中态
        'time_start_date': start_date,
        'time_end_date': end_date,
        # ...
    }
    return render(request, 'supplier/evaluation_list.html', context)
```

其他视图（如合同/付款/结算列表、统计页）可复用相同模式，只需：

- 统一读取 `time_range`；
- 使用适合该业务的日期字段进行过滤。

### 3.2.4 模板中的典型用法示例

以 `supplier_eval/templates/supplier/evaluation_list.html` 为例，在现有筛选区域中增加时间区间下拉：

```django
{# 现有 form 内，在评分筛选旁边新增时间范围下拉 #}
<select name="time_range" class="filter-select" onchange="this.form.submit()">
    <option value="year" {% if time_range == 'year' %}selected{% endif %}>全年</option>
    <option value="last_1m" {% if time_range == 'last_1m' %}selected{% endif %}>近 1 个月</option>
    <option value="last_3m" {% if time_range == 'last_3m' %}selected{% endif %}>近 3 个月</option>
    <option value="last_6m" {% if time_range == 'last_6m' %}selected{% endif %}>近 6 个月</option>
</select>
```

> 注意：
> - 保持现有的全局参数透传逻辑（`global_year` / `global_project` 的 hidden input）不变；
> - 当用户通过“重置筛选”链接返回列表时，可考虑保留 `time_range` 或重置为 `year`，视需求而定。

---

## 3.3 可选方案：独立的「近期项目动态」页面

如果后续希望有一个专门页面总览近期所有模块的变动，可在第二阶段增加一个精简页面。

### 3.3.1 功能定位

- 菜单项（建议）：挂在“数据概览”下方，如「近期项目动态」；
- 核心问题：在最近一段时间（1–3 个月）内，所有项目发生了哪些关键业务动作。

### 3.3.2 页面内容结构建议

- 头部筛选区：
  - 时间区间下拉 / 按钮（复用 `time_range` 逻辑）；
  - 可选：项目下拉（沿用全局项目筛选）。
- 内容：
  - 小型统计卡片：
    - 近 X 天新增采购数量 / 新签合同金额 / 新增付款金额 / 完成结算数量等；
  - 时间线式列表：
    - 按时间倒序列出关键事件（采购创建、合同签署、付款、结算、供应商评价等）；
    - 每行包含：日期、项目名称、事件类型、金额（如有）、状态等。

### 3.3.3 实现建议（简要）

- 新增 URL + 视图，例如：`project/views_recent.py:recent_activity_view`；
- 汇总服务层函数（可放在 `project/services/metrics_recent.py`）：
  - 输入：`start_date`、`end_date`、`project_list`；
  - 输出：事件列表 + 各类汇总数据；
- 复用第 3.2 节中的 `resolve_time_range` 和 `_resolve_global_filters`。

---

## 4. 逐步落地建议

建议按以下顺序实施，以降低风险且便于体验迭代：

1. **第一步：抽象时间区间解析工具**
   - 在 `project/utils/filters.py` 新增 `resolve_time_range`；
   - 为该函数写简单的单元测试，确保 4 种取值（`year`/`last_1m`/`last_3m`/`last_6m`）行为正确。

2. **第二步：选择一个试点页面**
   - 推荐：
     - 统计分析页：`project/views_statistics.py:statistics_view`；或
     - 某个你日常最关注的列表（如合同列表 / 付款列表）。
   - 在该视图：
     - 使用 `_resolve_global_filters` 获取 `year_filter`；
     - 使用 `resolve_time_range` 获取时间区间；
     - 对核心 QuerySet 增加时间过滤；
   - 在对应模板中：
     - 增加 `time_range` 下拉 / 按钮；
     - 渲染选中态。

3. **第三步：观察效果并微调**
   - 日常使用中观察：
     - 近 1 / 3 / 6 个月的数据量和分布是否符合预期；
     - 交互是否直观（是否需要调整默认值或增加提示文案）。
   - 视反馈决定：
     - 是否在更多页面复制这套时间区间筛选；
     - 是否需要第二阶段的「近期项目动态」总览页面。

4. **第四步（可选）：扩展/高级功能**
   - 增加自定义日期区间（开始日期 + 结束日期）；
   - 增加图表上的“区间高亮”或“只显示近 N 月曲线”等。

---

## 5. 小结

- **全局筛选**继续只负责“年度 + 项目范围”，保持简单清晰；
- **时间区间**作为**局部筛选**引入到关键视图中，以 `time_range` 参数驱动；
- 核心实现点只有三个：
  1. 新增 `resolve_time_range` 工具函数；
  2. 在试点视图中按时间区间过滤数据；
  3. 在模板中加入时间区间控件并保持与全局参数兼容。

该方案在不打乱现有布局和结构的前提下，满足“看某年某个时间段（特别是近 1–2 个月）业务数据”的需求，并且后续可以平滑扩展到更多页面。
