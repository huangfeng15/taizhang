# 项目硬编码审查报告

## 1. 背景与目标
- 目的：系统梳理 Django 采购与成本管理平台中的硬编码问题，提出配置化与组件化的落地建议，降低未来维护和定制化成本。
- 方法：遵循 KISS、YAGNI、SOLID、DRY 原则，逐模块检查配置文件、视图层、脚本、管理后台与数据导入逻辑。
- 范围：`config/`、`project/`、各业务应用的 admin/model、`scripts/` 及管理命令。

## 2. 硬编码问题清单
| 编号 | 问题描述 | 影响 | 相关位置 |
| --- | --- | --- | --- |
| HC-01 | SECRET_KEY、DEBUG、ALLOWED_HOSTS 采用不安全默认值，允许通配访问 | 安全风险高；生产环境易误用 | `config/settings.py:11`, `config/settings.py:14`, `config/settings.py:17`, `.env.example:1-7` |
| HC-02 | 全局年份范围固定起于 2019，且多处重复写死 | 新年度需改代码，多模块不一致 | `project/context_processors.py:22`, `project/views.py:290`, `project/views.py:331`, `project/views.py:2132`, `project/views.py:2541`, `scripts/check_data_statistics.py:23` |
| HC-03 | 更新监控默认起始日写死为 2025-10-01 | 新上线/历史数据回溯时逻辑失准 | `project/views.py:2120` |
| HC-04 | 导入模板定义（文件名、表头、说明、年份范围）内联于视图 | 模板调整需发版，难以按客户定制 | `project/views.py:136-334` |
| HC-05 | 管理后台字段、分组、分页等配置散落在各 Admin | 多应用重复维护，易出现差异 | `procurement/admin.py:8-82`, `contract/admin.py:29-93`, `payment/admin.py:8-33` |
| HC-06 | 筛选器配置硬编码且重复枚举模型 choices | 违背 DRY，修改枚举需双改 | `project/filter_config.py:34-215` |
| HC-07 | 数据导入命令写死模块列表、列映射、枚举、编码映射 | 新模块/字段不可配置，测试环境难复用 | `procurement/management/commands/import_excel.py:42-129`, `procurement/management/commands/import_excel.py:270-363` |
| HC-08 | 数据清洗脚本写死文件路径、列索引（例：列 44-56） | 模板微调即脚本失效，无法复用 | `scripts/prepare_import_data.py:58-154`, `scripts/prepare_import_data.py:197-215` |
| HC-09 | 表统计脚本写死业务表及中文描述 | 系统扩展模块需改脚本 | `scripts/check_table_data.py:12-31` |
| HC-10 | 评估/合同等枚举在模型与其他模块重复定义 | 违背 DRY，增加维护点 | `contract/models.py:24-40`, `supplier_eval/models.py:39-45`, `project/filter_config.py:85-104` |
| HC-11 | 导入模板说明中写死“采购方式”常见选项 | 新增/调整枚举需改代码，难以按项目自定义 | `project/views.py:205` |
| HC-12 | 模型帮助文本硬编码示例电话与姓名 | 示例需按实际场景调整，不利于外部发布 | `procurement/models.py:171`, `procurement/models.py:189` |

## 3. 改进建议与配置方案
### 3.1 配置中心与环境变量治理（体现 KISS / YAGNI）
- 建议：建立 `config/settings_components/security.py`（或类似模块）集中读取环境变量，提供安全默认；`.env.example` 中标注生产需覆盖的变量，不再给出危险默认值。
- 好处：部署时明确需要配置的项，避免误用；符合 KISS，减少多处判断。

### 3.2 时间范围与常量统一（体现 DRY）
- 建议：在 `project/constants.py` 定义 `BASE_YEAR`, `YEAR_WINDOW`, `DEFAULT_MONITOR_START_DATE` 等常量，由配置或环境驱动，供 context processor、视图、脚本共用。
- 应用：替换 `project/context_processors.py`、`project/views.py`、`scripts/check_data_statistics.py` 等硬编码；同时允许通过 `.env` 覆盖，满足 YAGNI（仅暴露当前必需）。

### 3.3 导入模板与脚本组件化（体现 SRP / OCP）
- 建议：新建 `project/import_templates/*.yml` 配置文件描述模板元数据（文件名、表头、说明、年份范围等），视图及命令读取配置生成模板；脚本改为接收配置文件路径/CLI 参数，避免固定列索引。
- 好处：模板新增列或年份只改配置；命令遵循 SRP，易于扩展新模块（OCP）。

### 3.4 管理后台与筛选配置抽象（体现 SOLID / DRY）
- Admin：提取公共 `BaseAuditAdmin`（统一分页、审计字段 readonly、返回前端逻辑），字段组可通过元数据（字典/tuple）驱动，减少重复。
- 筛选器：将过滤项描述下沉至 `project/filter_config.py` 内部的数据结构，并改为动态读取模型 `choices`，避免魔法值；可考虑注册式配置（Dict + 工厂函数）扩展新业务类型。
- 好处：减少重复代码，易于统一改动，符合 DRY；通过接口化（I）隔离不同页面需求，维持 SOLID。

### 3.5 数据导入命令参数化（体现 KISS / OCP）
- 将 `choices=['project', ...]` 等模块列表、冲突策略、关键列等改为从配置读取；支持传入自定义列映射文件（CSV/JSON）或选择预置模板。
- `_is_template_note_row` 的关键字段列表改由配置管理，并允许按模块扩展；保证新模块无需修改核心逻辑。

### 3.6 脚本可配置化
- `scripts/prepare_import_data.py` 接受命令行参数（输入路径、列映射、年份范围），并提供默认配置文件；列索引用列名匹配而非魔法下标。
- `scripts/check_table_data.py` 读取列表自 `settings` 或独立 YAML，以便扩展。

### 3.7 域枚举统一出口
- 在模型层保留 choices，同时提供枚举常量 `Enum` 或 `TextChoices`，供过滤配置、模板等直接引用，避免硬编码字符串。
- 逐步将字符串比较替换为枚举引用（LSP：子类枚举依旧适配原逻辑）。
- 将导入模板、报表说明中的“常见选项”（如采购方式）改由统一枚举驱动，自动生成提示文案。

### 3.8 帮助文案与示例数据配置
- 将包含示例姓名、电话的 `help_text` 统一抽取至配置（如 `project/helptext.py` 或国际化资源），支持按部署环境覆盖。
- 提供可替换的占位符（如 `{{CONTACT_SAMPLE}}`），由配置或翻译文件在运行时注入，避免对外环境暴露固定电话。

## 4. 组件化与配置化机会汇总
| 领域 | 现状问题 | 抽象建议 |
| --- | --- | --- |
| 导入模板 | 视图内嵌大段表头说明 | 以 YAML/JSON + 数据类解析，形成模板注册中心 |
| Admin 配置 | 分散、重复 | 公共基类 + 元数据驱动字段组装 |
| 筛选器 | 手写选项、重复 choices | 读取模型枚举或配置，支持插件式注册 |
| 年份/时间范围 | 多处写死 | 全局常量 + 环境覆盖 |
| CLI 脚本 | 文件路径、列索引写死 | 引入 argparse 参数和配置文件 |
| 帮助文案 | 示例电话及提示散落在模型中 | 建立可配置帮助文案中心 |

## 5. 实施计划（迭代建议）
1. **2**
   - 梳理现有环境变量使用点，补充 `.env.example` 注释并删除不安全默认值。
   - 新建 `config/settings_components/security.py` 与 `project/constants.py`，集中读取 `SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`、`BASE_YEAR`、`DEFAULT_MONITOR_START_DATE` 等常量。
   - 全量替换 `project/context_processors.py`、`project/views.py`、`scripts/check_data_statistics.py` 等对年份/日期的硬编码引用，新增单元测试验证跨年度表现。
   - 更新部署手册，明确生产必须配置的变量列表和示例。
2. **第二阶段（模板与脚本治理）**
   - 设计导入模板 YAML/JSON 结构，沉淀到 `project/import_templates/` 并覆盖采购/合同/付款/评价四类模板。
   - 重构 `import_excel` 管理命令与 `scripts/prepare_import_data.py`，从配置读取列定义、模块列表、冲突策略及“常见选项”提示。
   - 增加命令行参数（输入路径、列映射、年份范围、跳过校验等），并提供示例配置文件与使用文档。
   - 针对模板生成与脚本执行编写集成测试或最小演练脚本，确保配置驱动生效。
3. **第三阶段（界面与枚举组件化）**
   - 抽象 `BaseAuditAdmin`，统一 `list_per_page`、审计字段、跳转逻辑；将采购/合同/付款 Admin 切换至元数据驱动字段组装。
   - 改造 `project/filter_config.py` 为注册式配置：按模块读取字段描述，自动引用模型 `TextChoices` 与格式化器。
   - 整理采购方式、文件定位等业务枚举为单点导出，供模板、报表、导入提示复用；同步替换视图与模板中的硬编码文案。
   - 补充 UI 回归脚本或手工检查清单，确保筛选与分页行为一致。
4. **第四阶段（帮助文案与示例数据配置）**
   - 建立帮助文案资源（如 `project/helptext.py` 或 i18n 翻译项），统一维护示例姓名、电话及提示语。
   - 将模型 `help_text`、模板提示调用配置项或占位符（`{{CONTACT_SAMPLE}}` 等），支持不同部署场景快速替换。
   - 增加配置校验脚本，提示缺失或未覆盖的文案键值；更新开发指南说明自定义方式。

每阶段均应编写最小化测试或脚本验证（KISS），仅实现当期明确需求（YAGNI），同时确保新结构对扩展开放（OCP）且复用现有逻辑（DRY）。

## 6. 本次迭代回顾
- **已完成**：定位 10 处主要硬编码风险，覆盖配置、安全、模板、脚本与界面层面；梳理配置化与组件化方向。
- **原则落实**：
  - KISS：建议以常量/配置集中管理，避免额外复杂框架。
  - YAGNI：仅提议现有痛点所需的配置化，不引入不必要的通用平台。
  - SOLID：通过拆分配置中心、Admin 基类、模板注册等方式保证单一职责、开放扩展、依赖抽象。
  - DRY：重点清除年份、枚举、字段分组等重复定义。
- **挑战与对策**：
  - 模板与脚本分散，需逐个梳理；通过建立统一配置格式解决。
  - 年份范围分布广，建议引入中央常量并增加单元测试覆盖。
- **下一步建议**：
  1. 由运维/安全先行调整环境变量策略与部署说明。
  2. 选择导入模板治理作为试点，实现配置驱动的首个模块。
  3. 结合试点经验完善组件化文档，为后续模块迁移提供示例。
