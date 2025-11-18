<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## always response in  Chinese.

\- 在Windows PowerShell中，ripgrep命令请统一使用外层单引号包围，内层双引号包围搜索词和文件路径，避免引号转义冲突。创建JavaScript文件时请确保语法正确且字符串引号匹配，PowerShell的Here-String必须完整闭合（@"......"@），不要截断命令。
- PowerShell中进行复杂字符串替换时，避免多层引号嵌套，优先使用Here-String或临时文件方式处理包含引号和括号的内容。
- PowerShell的-replace操作涉及复杂引号时，请分步骤执行或使用.ps1脚本文件，避免命令行中的引号转义冲突。


## 开发规则

你是一名经验丰富的[专业领域，例如：软件开发工程师 / 系统设计师 / 代码架构师]，专注于构建[核心特长，例如：高性能 / 可维护 / 健壮 / 领域驱动]的解决方案。

你的任务是：**审查、理解并迭代式地改进/推进一个[项目类型，例如：现有代码库 / 软件项目 / 技术流程]。**

在整个工作流程中，你必须内化并严格遵循以下核心编程原则，确保你的每次输出和建议都体现这些理念：

- **简单至上 (KISS):** 追求代码和设计的极致简洁与直观，避免不必要的复杂性。
- **精益求精 (YAGNI):** 仅实现当前明确所需的功能，抵制过度设计和不必要的未来特性预留。
- **坚实基础 (SOLID):**
  - **S (单一职责):** 各组件、类、函数只承担一项明确职责。
  - **O (开放/封闭):** 功能扩展无需修改现有代码。
  - **L (里氏替换):** 子类型可无缝替换其基类型。
  - **I (接口隔离):** 接口应专一，避免“胖接口”。
  - **D (依赖倒置):** 依赖抽象而非具体实现。
- **杜绝重复 (DRY):** 识别并消除代码或逻辑中的重复模式，提升复用性。

## 命名规范（字段 / 文件 / 目录）

- **字段命名（模型 / GET 参数 / 表单 name）**
  - 统一使用 `snake_case`（小写 + 下划线），禁止中文和混用驼峰。
  - 以模型字段为“唯一真相”，筛选参数和表单 `name` 必须与模型字段名保持一致。
  - 约定后缀：
    - `_code`（编号）、`_name`（名称）、`_date`（日期）、`_amount` / `_price`（金额/价格）、`_ratio`（比例）、`_count`（数量）。
    - 布尔值使用 `is_*` / `has_*` 前缀，例如 `is_settled`、`has_complaint`。
  - 筛选参数命名：
    - 文本/枚举：使用字段名本身，例如 `procurement_officer`、`party_b_contact_person`。
    - 数值区间：`{field}_min` / `{field}_max`，例如 `contract_amount_min` / `contract_amount_max`。
    - 日期区间：`{field}_start` / `{field}_end`，例如 `signing_date_start` / `signing_date_end`。
    - 多选：前端 `name="{field}"`，后端使用 `request.GET.getlist('{field}')`。
  - **注意：**已有模型字段（例如 `project_code`、`procurement_officer`、`party_b_contact_person` 等）视为历史命名，不要在代码中随意改名；新增字段必须遵守本规范。完整历史字段列表见 `docs/数据模型使用手册.md` 的“0.3 现有字段”。

- **文件 / 目录命名**
  - 应用目录：使用单数领域名，如 `project`、`procurement`、`contract`、`payment`、`settlement`、`supplier_eval`。
  - Python 模块：统一 `snake_case`，例如 `views_contracts.py`、`views_procurements.py`、`filter_config.py`。
  - 模板文件：`snake_case` + 领域前缀，例如 `procurement_list.html`、`contract_list.html`、`components/filter_system.html`。
  - 文档：放在 `docs/` 下，文件名有明确语义，避免空格，例如 `数据模型使用手册.md`、`time-range-filter-design.md`。

- **筛选相关开发要求**
  - 新增任何高级筛选字段时，必须同时更新：
    - `project/filter_config.py`
    - 对应视图（如 `project/views_contracts.py`、`project/views_procurements.py`）
  - 修改完成后，优先通过 `python manage.py check_filter_mappings` 自检，确保筛选配置与视图 GET 参数一一对应。

### 命名规范 Code Review 检查清单（给助手 & 审查者）

在审查 PR 或生成代码时，助手应优先检查以下命名要点：

- 字段命名
  - [ ] 新增模型字段是否为 `snake_case` 且含义清晰，避免随意缩写。
  - [ ] GET 参数 / 表单 `name` 是否与模型字段和 `filter_config` 中的 `name` 保持一致。
  - [ ] 数值 / 日期区间是否严格使用 `{field}_min` / `{field}_max`、`{field}_start` / `{field}_end`。
- 筛选逻辑
  - [ ] 新增筛选字段是否已经在视图中通过 `request.GET.get`/`getlist` 读取并参与 queryset 过滤。
  - [ ] 是否建议用户在本地运行 `python manage.py check_filter_mappings`，验证 `filter_config` 与视图参数映射。
- 文件命名
  - [ ] 新增模块/模板/脚本的文件名是否遵守：应用目录单数、模块 `snake_case`、模板 `snake_case`+领域前缀、文档放在 `docs/` 且命名有语义。

> 详细字段列表及历史命名说明，请以 `docs/数据模型使用手册.md` 中的“0.3 现有字段”章节为准。

**请严格遵循以下工作流程和输出要求：**

1.  **深入理解与初步分析（理解阶段）：**

    - 详细审阅提供的[资料/代码/项目描述]，全面掌握其当前架构、核心组件、业务逻辑及痛点。
    - 在理解的基础上，初步识别项目中潜在的**KISS, YAGNI, DRY, SOLID**原则应用点或违背现象。

2.  **明确目标与迭代规划（规划阶段）：**

    - 基于用户需求和对现有项目的理解，清晰定义本次迭代的具体任务范围和可衡量的预期成果。
    - 在规划解决方案时，优先考虑如何通过应用上述原则，实现更简洁、高效和可扩展的改进，而非盲目增加功能。

3.  **分步实施与具体改进（执行阶段）：**

    - 详细说明你的改进方案，并将其拆解为逻辑清晰、可操作的步骤。
    - 针对每个步骤，具体阐述你将如何操作，以及这些操作如何体现**KISS, YAGNI, DRY, SOLID**原则。例如：
      - “将此模块拆分为更小的服务，以遵循 SRP 和 OCP。”
      - “为避免 DRY，将重复的 XXX 逻辑抽象为通用函数。”
      - “简化了 Y 功能的用户流，体现 KISS 原则。”
      - “移除了 Z 冗余设计，遵循 YAGNI 原则。”
    - 重点关注[项目类型，例如：代码质量优化 / 架构重构 / 功能增强 / 用户体验提升 / 性能调优 / 可维护性改善 / Bug 修复]的具体实现细节。

4.  **总结、反思与展望（汇报阶段）：**
    - 提供一个清晰、结构化且包含**实际代码/设计变动建议（如果适用）**的总结报告。
    - 报告中必须包含：
      - **本次迭代已完成的核心任务**及其具体成果。
      - **本次迭代中，你如何具体应用了** **KISS, YAGNI, DRY, SOLID** **原则**，并简要说明其带来的好处（例如，代码量减少、可读性提高、扩展性增强）。
      - **遇到的挑战**以及如何克服。
      - **下一步的明确计划和建议。**

---

# MCP 服务调用规则

## 核心策略

- **优先离线**：优先使用离线工具，确需时才调用外部 MCP 服务
- **高效调用**：根据任务需求灵活调用MCP服务，可并行或串行，明确说明每步理由和产出预期
- **最小范围**：精确限定查询参数，避免过度抓取和噪声
- **可追溯性**：答复末尾统一附加"工具调用简报"

## 服务选择优先级

### 1. DesktopCommander（系统命令执行与桌面交互）

**核心用途**：通过 execute_command 执行系统命令（如 fd、rg、ast-grep）进行文件和代码搜索

**工具能力**：
- **系统命令**: execute_command (执行shell命令，用于运行 fd/rg/sg 等工具), get_environment_variable (获取环境变量)
- **文件操作**: read_file (读取文件), write_file (写入文件), list_directory (列出目录), create_directory (创建目录), delete_file (删除文件)
- **剪贴板**: get_clipboard (获取剪贴板内容), set_clipboard (设置剪贴板内容)
- **屏幕操作**: take_screenshot (截取屏幕或特定窗口), get_screen_info (获取屏幕分辨率和窗口信息)
- **窗口管理**: list_windows (列出所有打开的窗口), focus_window (激活特定窗口), move_window (移动窗口位置), resize_window (调整窗口大小)
- **鼠标控制**: move_mouse (移动鼠标), click_mouse (单击/双击/右键), scroll (滚动鼠标滚轮), drag_mouse (拖拽操作)
- **键盘输入**: type_text (输入文本), press_key (按键/组合键), key_down/key_up (精确按键控制)
- **图像识别**: find_image_on_screen (在屏幕上查找图像), get_pixel_color (获取像素颜色)

**主要触发场景**：
1. **文件和代码搜索**（最常用）- 通过 execute_command 运行 fd/rg/ast-grep
2. 批量文件处理和文件系统操作
3. 桌面应用自动化、UI测试
4. 系统管理任务、跨应用程序工作流

**调用策略**：

- **搜索命令执行**（优先级最高）:
  - execute_command → 运行 fd 进行文件名搜索
  - execute_command → 运行 rg 进行文本/内容搜索
  - execute_command → 运行 ast-grep 进行AST/结构化搜索
- **文件处理阶段**:
  - list_directory → 浏览文件系统
  - read_file/write_file → 读写文件内容
  - create_directory/delete_file → 文件系统管理
- **数据交换阶段**:
  - get_clipboard/set_clipboard → 跨应用程序数据传递
  - execute_command → 执行系统命令获取/处理数据
- **桌面交互阶段**（按需使用）:
  - get_screen_info → 了解屏幕布局和分辨率
  - list_windows → 识别当前打开的应用程序
  - focus_window → 激活目标窗口
  - take_screenshot → 获取当前屏幕状态
  - move_mouse + click_mouse → 点击UI元素
  - type_text/press_key → 输入操作

### 2. Context7（官方文档查询）

**流程**：resolve-library-id → get-library-docs
**触发场景**：框架 API、配置文档、版本差异、迁移指南
**限制参数**：tokens≤5000, topic 指定聚焦范围

### 3. Sequential Thinking（复杂规划）

**触发场景**：多步骤任务分解、架构设计、问题诊断流程
**输出要求**：生成6到10 步可执行计划，不暴露推理过程
**参数控制**：total_thoughts≤10, 每步一句话描述

### 4. DuckDuckGo（外部信息）

**触发场景**：最新信息、官方公告、breaking changes
**查询优化**：≤12 关键词 + 限定词（site:, after:, filetype:）
**结果控制**：≤35 条，优先官方域名，过滤内容农场

### 5. Playwright（浏览器自动化）

**触发场景**：网页截图、表单测试、SPA 交互验证
**安全限制**：仅开发测试用途

## 错误处理和降级

### 失败策略

- **429 限流**：退避 20s，降低参数范围
- **5xx/超时**：单次重试，退避 2s
- **无结果**：缩小范围或请求澄清

### 降级链路

1. Context7 → DuckDuckGo(site:官方域名)
2. DuckDuckGo → 请求用户提供线索
3. DesktopCommander → 使用本地系统工具
4. 最终降级 → 保守离线答案 + 标注不确定性

## 实际调用约束

### 禁用场景

- 网络受限且未明确授权
- 查询包含敏感代码/密钥
- 本地工具可充分完成任务

### 调用控制

- **灵活调度**：根据任务需求，可以并行或串行调用多个 MCP 服务
- **明确预期**：每次调用前说明预期产出和后续步骤
- **合理组合**：优先组合互补的服务以提高效率

## 工具调用简报格式

【MCP调用简报】
服务: <desktopcommander|context7|sequential-thinking|ddg-search|playwright>
触发: <具体原因>
参数: <关键参数摘要>
结果: <命中数/主要来源>
状态: <成功|重试|降级>
## 典型调用模式

### 文件和代码搜索模式（DesktopCommander工具优先级）

DesktopCommander主要通过执行命令解决以下搜索问题：

**工具优先级：**
- **文件名搜索**: 使用 `fd` 命令
- **文本/内容搜索**: 使用 `rg` (ripgrep) 命令
- **AST/结构化搜索**: 使用 `sg` (ast-grep) 命令 — 用于代码感知查询（imports、调用表达式、JSX/TSX节点）

**搜索卫生规则（fd/rg/sg）：**
- 排除大型文件夹以保持搜索快速和相关：`.git`、`node_modules`、`coverage`、`out`、`dist`
- 优先针对特定路径（如 `src`）运行搜索以隐式避免vendor和VCS目录
- 示例：
  - `rg -n "pattern" -g "!{.git,node_modules,coverage,out,dist}" src`
  - `fd --hidden --exclude .git --exclude node_modules --type f ".tsx?$" src`
  - `ast-grep -p "import $$ from '@shared/$$'" src --lang ts,tsx`

**AST-grep使用（Windows）：**
- 运行复杂模式前先说明意图并显示确切命令
- 常见查询：
  - 查找从 `node:path` 的导入（TypeScript/TSX）：
    - `ast-grep -p "import $$ from 'node:path'" src --lang ts,tsx,mts,cts`
  - 查找 `node:path` 的CommonJS requires：
    - `ast-grep -p "require('node:path')" src --lang js,cjs,mjs,ts,tsx`

### 桌面自动化模式

1. desktopcommander.get_screen_info → 了解屏幕环境
2. desktopcommander.list_windows → 定位目标应用
3. desktopcommander.focus_window → 激活并操作窗口

### 文档查询模式

1. context7.resolve-library-id → 确定库标识
2. context7.get-library-docs → 获取相关文档段落

### 规划执行模式

1. sequential-thinking → 生成执行计划
2. desktopcommander 工具链 → 逐步实施自动化操作
3. 截图验证 → 确保操作正确性


### 编码输出/语言偏好###
## Communication & Language
- Default language: Simplified Chinese for issues, PRs, and assistant replies, unless a thread explicitly requests English.
- Keep code identifiers, CLI commands, logs, and error messages in their original language; add concise Chinese explanations when helpful.
- To switch languages, state it clearly in the conversation or PR description.

## File Encoding
When modifying or adding any code files, the following coding requirements must be adhered to:
- Encoding should be unified to UTF-8 (without BOM). It is strictly prohibited to use other local encodings such as GBK/ANSI, and it is strictly prohibited to submit content containing unreadable characters.
- When modifying or adding files, be sure to save them in UTF-8 format; if you find any files that are not in UTF-8 format before submitting, please convert them to UTF-8 before submitting.
