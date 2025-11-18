# OpenSpec 使用指南

**版本**: 1.0
**日期**: 2025-11-18
**适用于**: Claude Code 和 Kilocode

---

## 目录

1. [项目简介](#项目简介)
2. [安装与初始化](#安装与初始化)
3. [Claude Code 使用指南](#claude-code-使用指南)
4. [Kilocode 使用指南](#kilocode-使用指南)
5. [OpenSpec 核心概念](#openspec-核心概念)
6. [完整工作流程示例](#完整工作流程示例)
7. [常用命令参考](#常用命令参考)
8. [最佳实践](#最佳实践)
9. [常见问题](#常见问题)
10. [高级技巧](#高级技巧)

---

## 项目简介

### 什么是 OpenSpec？

OpenSpec 是一个**规范驱动的开发工具**，专为 AI 编码助手设计。它通过轻量级的工作流，在你开始编码之前，确保人类和 AI 就需求达成共识。

### 核心优势

- **确定性输出**: 通过明确规范，AI 生成可预测、可审查的代码
- **轻量级**: 简单工作流，无需 API 密钥，最小化配置
- **变更追踪**: 提案、任务和规范更新集中管理
- **多工具支持**: 兼容 Claude Code、Kilocode、Cursor 等主流 AI 工具
- **棕地友好**: 特别适合已有项目的功能迭代

### 工作原理

```
┌────────────────────┐
│  起草变更提案      │
│  (Draft Proposal)  │
└────────┬───────────┘
         │ 分享意图
         ▼
┌────────────────────┐
│  审查与对齐        │
│  (Review & Align)  │◀──── 反馈循环
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  实施任务          │
│  (Implement)       │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  归档并更新规范    │
│  (Archive)         │
└────────────────────┘
```

---

## 安装与初始化

### 前提条件

- Node.js >= 20.19.0
- npm 包管理器

### 安装步骤

```bash
# 1. 全局安装 OpenSpec CLI
npm install -g @fission-ai/openspec@latest

# 2. 验证安装
openspec --version

# 3. 进入项目目录
cd my-project

# 4. 初始化 OpenSpec
openspec init
```

### 初始化选项

在初始化过程中，系统会询问你使用的 AI 工具：

**对于 Claude Code**：
```
Which AI tools do you use? (Press space to select, enter to confirm)
  [✓] Claude Code
```

**对于 Kilocode**：
```
Which AI tools do you use? (Press space to select, enter to confirm)
  [✓] Kilo Code
```

可以同时选择多个工具。

### 初始化后结构

```
my-project/
├── .claude/                    # Claude Code 配置 (选择 Claude Code 时创建)
│   └── commands/
│       └── openspec/
│           ├── proposal.md
│           ├── apply.md
│           └── archive.md
├── .kilocode/                  # Kilocode 配置 (选择 Kilocode 时创建)
│   └── workflows/
│           ├── openspec-proposal.md
│           ├── openspec-apply.md
│           └── openspec-archive.md
├── openspec/                   # OpenSpec 主目录
│   ├── specs/                  # 源规范 (当前真相)
│   │   ├── auth/
│   │   │   └── spec.md
│   │   └── profile/
│   │       └── spec.md
│   ├── changes/                # 活动变更 (初始为空)
│   └── archive/                # 已归档变更
├── AGENTS.md                   # AGENTS.md 兼容配置
└── openspec/project.md         # 项目级配置
```

---

## Claude Code 使用指南

### 斜杠命令

Claude Code 提供三个原生斜杠命令：

#### 1. `/openspec:proposal` - 创建变更提案

**语法**: `/openspec:proposal <变更描述>`

**示例**:
```
/openspec:proposal 添加用户角色筛选功能
/openspec:proposal 修复订单详情页加载慢的问题
/openspec:proposal 重构支付模块的错误处理
```

**工作原理**:
- 在 `openspec/changes/` 创建变更目录
- 生成 `proposal.md` (变更说明)
- 生成 `tasks.md` (任务清单)
- 生成 `specs/` (规范增量)

#### 2. `/openspec:apply` - 实施变更

**语法**: `/openspec:apply <变更名称>`

**示例**:
```
/openspec:apply add-user-role-filters
/openspec:apply fix-order-performance
/openspec:apply refactor-payment-error-handling
```

**工作原理**:
- 读取 `tasks.md` 中的任务清单
- 逐条执行编码任务
- 自动标记完成的任务
- 输出进度报告

#### 3. `/openspec:archive` - 归档变更

**语法**: `/openspec:archive <变更名称>`

**示例**:
```
/openspec:archive add-user-role-filters
```

**工作原理**:
- 验证所有任务已完成
- 将变更移动到 `openspec/archive/`
- 合并规范到源规范
- 清理变更目录

### 自然语言替代

如果不使用斜杠命令，也可以使用自然语言：

```
创建一个 OpenSpec 变更提案，添加用户角色筛选功能
```

```
请实施 add-user-role-filters 变更
```

```
请归档 add-user-role-filters 变更
```

### 完整工作流程示例

#### 场景：添加两步验证功能

**步骤 1：创建提案**
```
你：/openspec:proposal 添加两步验证功能

Claude Code：我会创建添加两步验证的变更提案

正在分析现有代码...
找到认证模块：auth/
找到用户模型：models/user.py

创建目录：openspec/changes/add-2fa/
创建：proposal.md
创建：tasks.md
创建：specs/auth/spec.md

✓ 提案已创建！请审查并迭代规范。
```

**步骤 2：审查和迭代**
```
你：请审查提案内容

Claude Code：提案包含以下内容：

[proposal.md]
- 添加 TOTP 两步验证
- 使用 Google Authenticator
- 提供恢复代码

[tasks.md]
- 数据库迁移
- 后端 API
- 前端界面

[spec delta]
- 新增 2FA 需求
- OTP 验证场景

是否需要调整？
```

```
你：请为 OTP 验证添加错误处理场景

Claude Code：我会更新规范以添加错误处理

更新：openspec/changes/add-2fa/specs/auth/spec.md

## ADDED Requirements
### Requirement: OTP Error Handling
The system MUST handle OTP verification errors.

#### Scenario: Invalid OTP
- WHEN user enters incorrect OTP
- THEN return error "Invalid OTP code"
- AND increment failed attempts counter

✓ 规范已更新！
```

**步骤 3：实施变更**
```
你：规范看起来不错，开始实施

Claude Code：开始实施：add-user-2fa

任务 1.1：添加 two_factor_secret 列
✓ 创建迁移文件
✓ 运行迁移

任务 1.2：添加 two_factor_enabled 标志
✓ 更新用户模型
✓ 添加默认值

任务 2.1：创建 OTP 生成端点
✓ 生成 QR 代码
✓ 返回 setup URI

...（更多任务）

✓ 所有任务已完成！
```

**步骤 4：归档**
```
你：/openspec:archive add-2fa

Claude Code：正在归档：add-user-2fa

验证任务状态... ✓
合并规范... ✓
移动目录... ✓

✓ 变更已成功归档！
```

### 命令行工具

除了 Claude Code 集成，也可以直接使用命令行：

```bash
# 查看活动变更
openspec list

# 查看变更详情
openspec show add-2fa

# 验证规范格式
openspec validate add-2fa

# 交互式仪表板
openspec view
```

---

## Kilocode 使用指南

### 工作流文件

Kilocode 使用 `.kilocode/workflows/` 目录下的工作流文件：

#### 1. `/openspec-proposal.md` - 创建变更提案

**使用方式**：在 Kilocode 命令面板输入

**示例**:
```
/openspec-proposal.md 添加用户角色筛选功能
```

**生成文件**:
- `.kilocode/workflows/openspec-proposal.md`

#### 2. `/openspec-apply.md` - 实施变更

**使用方式**：
```
/openspec-apply.md add-user-role-filters
```

**生成文件**:
- `.kilocode/workflows/openspec-apply.md`

#### 3. `/openspec-archive.md` - 归档变更

**使用方式**:
```
/openspec-archive.md add-user-role-filters
```

**生成文件**:
- `.kilocode/workflows/openspec-archive.md`

### 自动发现机制

Kilocode 会自动发现团队工作流：
- 将生成的文件保存在 `.kilocode/workflows/`
- 从命令面板触发工作流

### 完整工作流程示例

#### 场景：重构订单服务

**步骤 1：创建提案**
```
你：/openspec-proposal.md 重构订单服务以提高性能

Kilocode：我会创建重构订单服务的变更提案

创建：openspec/changes/refactor-order-service/
创建：proposal.md
创建：tasks.md
创建：specs/order/spec.md

✓ 提案已创建！
```

**步骤 2：审查和迭代**
```
你：请添加缓存策略

Kilocode：我会更新规范以包含缓存策略

更新：specs/order/spec.md

## ADDED Requirements
### Requirement: Order Cache
The system MUST cache order details for 5 minutes.

#### Scenario: Cache hit
- WHEN user requests order within 5 minutes
- THEN return cached data
- AND skip database query

✓ 规范已更新！
```

**步骤 3：实施**
```
你：/openspec-apply.md refactor-order-service

Kilocode：开始实施重构...

任务 1：优化数据库查询
✓ 添加索引
✓ 重写查询

任务 2：实现缓存层
✓ 集成 Redis
✓ 添加缓存装饰器

✓ 所有任务已完成！
```

**步骤 4：归档**
```
你：/openspec-archive.md refactor-order-service

Kilocode：归档完成！
```

### 命令行工具

与 Claude Code 相同，Kilocode 也支持命令行：

```bash
# 查看活动变更
openspec list

# 查看变更详情
openspec show refactor-order-service

# 验证规范格式
openspec validate refactor-order-service

# 归档变更（无确认）
openspec archive refactor-order-service --yes
```

---

## OpenSpec 核心概念

### 1. 规范格式

#### 源规范 (Source Specs)

位置：`openspec/specs/<模块>/spec.md`

**格式**: ```markdown
# <模块名> Specification

## Purpose
<模块的目的>

## Requirements

### Requirement: <需求名称>
The system SHALL/MUST <行为描述>

#### Scenario: <场景名称>
- WHEN <条件>
- THEN <结果>
- AND <附加结果>
```

**示例** (`openspec/specs/auth/spec.md`): ```markdown
# Auth Specification

## Purpose
Authentication and session management system.

## Requirements

### Requirement: User Login
The system SHALL authenticate users with email and password.

#### Scenario: Valid credentials
- WHEN a user submits valid email and password
- THEN a JWT token is issued
- AND the user session is created

#### Scenario: Invalid credentials
- WHEN a user submits incorrect password
- THEN return 401 Unauthorized
- AND increment failed login counter
```

#### 变更规范 (Change Specs)

位置：`openspec/changes/<变更名>/specs/<模块>/spec.md`

**格式**: ```markdown
# Delta for <模块名>

## ADDED Requirements
### Requirement: <新需求名称>
...

## MODIFIED Requirements
### Requirement: <修改的需求名称>
...

## REMOVED Requirements
### Requirement: <移除的需求名称>
...
```

**示例**: ```markdown
# Delta for Auth

## ADDED Requirements

### Requirement: Two-Factor Authentication
The system MUST require a second factor during login.

#### Scenario: OTP required
- WHEN a user submits valid credentials
- THEN an OTP challenge is presented
- AND the user must enter a 6-digit code
```

### 2. 提案文件

位置：`openspec/changes/<变更名>/proposal.md`

**格式**: ```markdown
# Proposal: <变更名称>

## Summary
<一句话总结>

## Motivation
<为什么要做这个变更>

## Technical Approach
<技术方案概述>

## Acceptance Criteria
<验收标准>
```

**示例**: ```markdown
# Proposal: Add Two-Factor Authentication

## Summary
Implement two-factor authentication (2FA) using TOTP.

## Motivation
Current authentication is single-factor and does not meet security requirements.

## Technical Approach
- Use pyotp library for TOTP generation
- Store secret in user profile
- Support Google Authenticator

## Acceptance Criteria
- Users can enable/disable 2FA
- Login requires OTP after password
- Recovery codes are provided
```

### 3. 任务清单

位置：`openspec/changes/<变更名>/tasks.md`

**格式**: ```markdown
## <阶段号>. <阶段名称>
- [ ] <任务号>.<子任务号> <任务描述>
- [ ] <任务号>.<子任务号> <任务描述>

## <阶段号>. <阶段名称>
- [ ] <任务号>.<子任务号> <任务描述>
```

**示例**: ```markdown
## 1. Database Schema
- [ ] 1.1 Add OTP secret column to users table
- [ ] 1.2 Add OTP enabled flag
- [ ] 1.3 Create recovery codes table

## 2. Backend API
- [ ] 2.1 Create OTP setup endpoint
- [ ] 2.2 Create OTP verification endpoint
- [ ] 2.3 Update login flow

## 3. Frontend
- [ ] 3.1 Create 2FA setup page
- [ ] 3.2 Update login form

## 4. Documentation
- [ ] 4.1 Update API docs
- [ ] 4.2 Add user guide
```

### 4. 目录结构

```
openspec/
├── specs/                      # 源规范（当前真相）
│   ├── auth/
│   │   └── spec.md
│   ├── profile/
│   │   └── spec.md
│   └── order/
│       └── spec.md
│
├── changes/                    # 活动变更
│   ├── add-user-profile/
│   │   ├── proposal.md
│   │   ├── tasks.md
│   │   └── specs/
│   │       └── profile/
│   │           └── spec.md
│   │
│   └── refactor-order-service/
│       ├── proposal.md
│       ├── tasks.md
│       └── specs/
│           └── order/
│               └── spec.md
│
└── archive/                    # 已归档变更
    └── 2025-11-18-add-user-profile/
        ├── proposal.md
        ├── tasks.md
        └── specs/
            └── profile/
                └── spec.md
```

### 5. 命名约定

#### 变更名称

使用 **kebab-case**（短横线连接）：

```
✅ Good:
- add-user-authentication
- fix-payment-bug
- refactor-order-service
- update-dependency-versions

❌ Bad:
- AddUserAuthentication (PascalCase)
- fix_payment_bug (snake_case)
- Add User Authentication (有空格)
- addUserAuthentication (camelCase)
```

#### 任务编号

使用 `<阶段>.<序号>` 格式：

```
## 1. Backend
- [ ] 1.1 Create API endpoint
- [ ] 1.2 Add validation
- [ ] 1.3 Write tests

## 2. Frontend
- [ ] 2.1 Create UI component
- [ ] 2.2 Add form validation
```

---

## 完整工作流程示例

### 示例：添加用户资料页面

#### 阶段 1：创建提案

**Claude Code 方式**: ```
/openspec:proposal 添加用户资料页面
```

**Kilocode 方式**: ```
/openspec-proposal.md 添加用户资料页面
```

**输出**: ```
创建：openspec/changes/add-user-profile/
├── proposal.md
├── tasks.md
└── specs/
    └── profile/
        └── spec.md
```

**proposal.md**: ```markdown
# Proposal: Add User Profile Page

## Summary
Create a user profile page where users can view and edit their information.

## Motivation
Currently users cannot view their profile information after registration.

## Acceptance Criteria
- Users can view their profile
- Users can edit their profile
- Avatar upload is supported
```

**tasks.md**: ```markdown
## 1. Backend API
- [ ] 1.1 Create Profile model
- [ ] 1.2 Create profile API endpoints
- [ ] 1.3 Add avatar upload endpoint

## 2. Frontend
- [ ] 2.1 Create profile page component
- [ ] 2.2 Create profile edit form
- [ ] 2.3 Integrate avatar upload

## 3. Documentation
- [ ] 3.1 Update API documentation
```

#### 阶段 2：审查和迭代

**你**: ```请添加邮箱验证功能
```

**AI**: ```
我会更新规范以包含邮箱验证

更新：openspec/changes/add-user-profile/specs/profile/spec.md

## ADDED Requirements

### Requirement: Email Validation
The system MUST validate email format in profile updates.

#### Scenario: Valid email
- WHEN user updates email to valid format
- THEN update succeeds

#### Scenario: Invalid email
- WHEN user updates email to invalid format
- THEN return error "Invalid email format"

✓ 规范已更新！
```

#### 阶段 3：实施

**Claude Code**: ```
/openspec:apply add-user-profile
```

**Kilocode**: ```
/openspec-apply.md add-user-profile
```

**AI 执行过程**: ```
开始实施：add-user-profile

任务 1.1: 创建 Profile 模型
✓ 创建 models/profile.py
✓ 添加字段：user, bio, avatar, email

任务 1.2: 创建 API 端点
✓ 创建 views/profile.py
✓ 添加 CRUD 操作
✓ 配置路由

任务 2.1: 创建前端组件
✓ 创建 ProfilePage.vue
✓ 添加数据显示

...（所有任务）

✓ 所有任务已完成！
```

#### 阶段 4：归档

**Claude Code**: ```
/openspec:archive add-user-profile
```

**Kilocode**: ```
/openspec-archive.md add-user-profile
```

**输出**: ```
✓ 变更已归档
✓ 源规范已更新
✓ 准备下一个功能
```

**归档后目录结构**: ```
openspec/
├── specs/
│   ├── auth/
│   │   └── spec.md
│   └── profile/
│       └── spec.md           # ← 已更新
│
├── changes/                    # ← 为空
│
└── archive/
    └── 2025-11-18-add-user-profile/  # ← 已移动
        ├── proposal.md
        ├── tasks.md
        └── specs/
            └── profile/
                └── spec.md
```

---

## 常用命令参考

### OpenSpec CLI 命令

```bash
# 查看活动变更
openspec list

# 查看变更详情
openspec show <变更名称>

# 验证规范格式
openspec validate <变更名称>

# 归档变更（交互式）
openspec archive <变更名称>

# 归档变更（无确认）
openspec archive <变更名称> --yes

# 交互式仪表板
openspec view

# 更新 OpenSpec
openspec update
```

### 实用命令脚本

#### 查看所有变更（活动 + 归档）
```bash
#!/bin/bash
echo "=== Active Changes ==="
openspec list

echo ""
echo "=== Archived Changes ==="
ls -la openspec/archive/ | grep "^d" | awk '{print $9}' | grep -v "^\\.$\\|^-2$"
```

#### 快速创建并实施变更
```bash
#!/bin/bash
# 使用：./quick-change.sh "变更描述"

DESCRIPTION="$1"
if [ -z "$DESCRIPTION" ]; then
  echo "Usage: $0 \"变更描述\""
  exit 1
fi

# 创建提案
echo "Creating proposal..."
openspec init-change "$DESCRIPTION"

# 获取变更名称
CHANGE_NAME=$(openspec list | tail -1 | awk '{print $1}')

echo "Created: $CHANGE_NAME"
echo ""
echo "Next steps:"
echo "1. Review: openspec/changes/$CHANGE_NAME/"
echo "2. Apply: openspec apply $CHANGE_NAME"
echo "3. Archive: openspec archive $CHANGE_NAME --yes"
```

---

## 最佳实践

### 1. 提案创建

✅ **应该**:
- 使用清晰、简洁的变更描述
- 从小功能开始（首次使用）
- 确保规范包含成功和失败场景
- 任务应该单一职责、可测试

❌ **不应该**:
- 创建过大的变更（超过 10 个任务）
- 在规范中描述实现细节
- 遗漏错误处理场景
- 任务太大或不可测试

### 2. 审查和迭代

✅ **应该**:
- 仔细审查生成的规范
- 在编码前迭代到满意为止
- 添加验收标准
- 考虑边界情况

❌ **不应该**:
- 未经审查直接实施
- 忽视安全考虑
- 遗漏性能要求
- 不考虑用户体验

### 3. 实施阶段

✅ **应该**:
- 按顺序执行任务
- 每个任务完成后提交代码
- 运行测试验证每个任务
- 标记完成的任务

❌ **不应该**:
- 跳过任务
- 一次性修改太多文件
- 不测试就继续
- 忽略失败的测试

### 4. 归档前检查清单

归档前确认：
- [ ] 所有任务已完成
- [ ] 代码已通过测试
- [ ] 文档已更新
- [ ] 代码已提交并推送
- [ ] 代码审查通过（团队项目）

### 5. 团队协作

✅ **应该**:
- 所有成员使用统一命名
- 及时归档已完成的变更
- 定期审查活跃变更
- 保持规范最新

❌ **不应该**:
- 多个变更修改同一模块（避免冲突）
- 长期保留活动变更
- 忽略团队规范约定

### 6. 规范编写技巧

**良好规范示例**: ```markdown
### Requirement: Password Reset
The system MUST allow users to reset their password via email.

#### Scenario: Valid reset request
- WHEN user submits registered email
- THEN send reset link to email
- AND link expires in 1 hour

#### Scenario: Invalid email
- WHEN user submits unregistered email
- THEN return "Email not found" error
- AND do not reveal email existence

#### Scenario: Expired link
- WHEN user clicks expired reset link
- THEN show "Link expired" message
- AND allow requesting new link
```

**差规范示例**（❌ 避免）: ```markdown
### Requirement: Password Reset
Make a password reset feature. Should be secure.

#### Scenario: User forgot password
- User enters email
- Gets link
- Can reset
```

---

## 常见问题

### Q1: Claude Code 无法识别 `/openspec:` 命令？

**解决方案**:

1. 确认选择了 Claude Code：
   ```bash
   openspec init  # 重新运行，确保选择 Claude Code
   ```

2. 检查配置目录：
   ```bash
   ls -la .claude/commands/openspec/
   ```

3. 应该看到三个文件：
   - proposal.md
   - apply.md
   - archive.md

4. 如果不存在，重新生成：
   ```bash
   openspec update --tool claude
   ```

5. 重启 Claude Code（命令在启动时加载）

### Q2: Kilocode 无法找到工作流？

**解决方案**:

1. 确认选择了 Kilo Code：
   ```bash
   openspec init  # 重新运行，确保选择 Kilo Code
   ```

2. 检查工作流目录：
   ```bash
   ls -la .kilocode/workflows/
   ```

3. 应该看到三个文件：
   - openspec-proposal.md
   - openspec-apply.md
   - openspec-archive.md

4. 如果不存在，重新生成：
   ```bash
   openspec update --tool kilocode
   ```

### Q3: 如何修改已创建的提案？

**解决方案**:

使用自然语言或直接编辑：

```
请修改 add-user-profile 提案，添加邮箱验证功能
```

**或直接编辑文件**: ```bash
# 编辑规范
vim openspec/changes/add-user-profile/specs/profile/spec.md

# 编辑任务
vim openspec/changes/add-user-profile/tasks.md

# 重新验证
openspec validate add-user-profile
```

### Q4: 可以暂停实施吗？

**答案**：可以！

Claude Code/Kilocode 会：
- 保存当前状态
- 标记已完成的任务
- 下次从上次停止处继续

**恢复实施**: ```
请继续实施 add-user-profile
```

### Q5: 如何处理冲突？

**场景**：并行变更修改同一文件

**解决方案**:

1. **方案 A**：顺序实施
   ```bash
   openspec apply change-1
   git commit
   openspec apply change-2
   ```

2. **方案 B**：合并变更
   ```bash
   # 手动合并冲突
   git mergetool

   # 验证功能
   npm test

   # 继续归档
   openspec archive change-1 --yes
   openspec archive change-2 --yes
   ```

3. **预防**: 避免创建重叠的变更
   - 按模块组织变更
   - 及时归档完成的变更
   - 团队沟通变更计划

### Q6: 如何查看变更历史？

**查看归档变更**: ```bash
# 列出所有归档
ls openspec/archive/

# 显示归档日期和名称
ls -lt openspec/archive/ | head -20
```

**查看特定变更**: ```bash
# 显示提案内容
cat openspec/archive/2025-11-18-add-user-profile/proposal.md

# 显示任务完成情况
cat openspec/archive/2025-11-18-add-user-profile/tasks.md
```

### Q7: 可以在变更中途添加新任务吗？

**答案**：可以！

**方法**: ```bash
# 编辑任务文件
vim openspec/changes/add-user-profile/tasks.md

# 添加新任务
## 3. Documentation
- [ ] 3.1 Update API docs
- [ ] 3.2 Write user guide
- [ ] 3.3 Add inline comments  # ← 新任务
```

**然后继续实施**: ```
请继续实施 add-user-profile
```

### Q8: 如何处理失败的测试？

**步骤**:

1. 修复测试：
   ```bash
   # 查看失败的测试
   npm test

   # 修复代码
   vim src/auth/2fa.js

   # 重新运行测试
   npm test
   ```

2. 如果测试无法立即修复：
   - 在 tasks.md 中添加修复任务
   - 继续归档（记录技术债）
   - 优先安排修复任务

**在 tasks.md 中记录**: ```markdown
## 4. Technical Debt
- [ ] 4.1 Fix failing 2FA tests
- [ ] 4.2 Add missing error handling
```

---

## 高级技巧

### 1. 模板化常见变更

创建常用变更模板：

**`templates/add-api-endpoint.md`**: ```markdown
# Proposal: Add {{NAME}} API Endpoint

## Summary
Add REST API endpoint for {{NAME}} resource.

## Requirements

### Requirement: {{METHOD}} /api/{{RESOURCE}}
The system MUST support {{METHOD}} requests for {{RESOURCE}}.

#### Scenario: Successful request
- WHEN client sends valid {{METHOD}} request
- THEN return {{STATUS_CODE}} with resource data

#### Scenario: Invalid request
- WHEN client sends invalid data
- THEN return 400 with error details

## Tasks
## 1. Backend
- [ ] 1.1 Create {{RESOURCE}} model
- [ ] 1.2 Create {{METHOD}} endpoint
- [ ] 1.3 Add validation
- [ ] 1.4 Write tests

## 2. Documentation
- [ ] 2.1 Update API docs
```

**使用模板**: ```bash
# 替换占位符
sed 's/{{NAME}}/User/g; s/{{RESOURCE}}/users/g; s/{{METHOD}}/POST/g; s/{{STATUS_CODE}}/201/g' \
  templates/add-api-endpoint.md > proposal.md
```

### 2. 集成 Git 钩子

**`.git/hooks/pre-commit`**: ```bash
#!/bin/bash
# 检查是否有未归档的变更

ACTIVE_CHANGES=$(openspec list 2>/dev/null | wc -l)

if [ "$ACTIVE_CHANGES" -gt 0 ]; then
  echo "⚠️  Warning: You have $ACTIVE_CHANGES active OpenSpec changes."
  echo "   Consider archiving completed changes before committing."
  echo ""
  openspec list
fi

exit 0
```

### 3. CI/CD 集成

**GitHub Actions 示例** (`.github/workflows/openspec.yml`): ```yaml
name: OpenSpec Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'

    - name: Install OpenSpec
      run: npm install -g @fission-ai/openspec@latest

    - name: Validate Active Changes
      run: |
        for change in $(openspec list | tail -n +2 | awk '{print $1}'); do
          echo "Validating $change..."
          openspec validate $change
        done

    - name: Check for Unarchived Changes
      run: |
        COUNT=$(openspec list 2>/dev/null | wc -l)
        if [ "$COUNT" -gt 0 ]; then
          echo "Active changes: $COUNT"
          echo "Consider archiving completed changes."
        fi
```

### 4. 自定义命令别名

**添加到 `~/.bashrc` 或 `~/.zshrc`**: ```bash
# OpenSpec 别名
alias oslist='openspec list'
alias oshow='openspec show'
alias osapply='openspec apply'
alias osarchive='openspec archive'

# 快速创建、应用、归档
alias osquick='openspec proposal "$1" && sleep 2 && osapply $(oslist | tail -1 | awk "{print \$1}")'

# 查看最近的归档
alias osrecent='ls -lt openspec/archive/ | head -10'
```

### 5. 批量操作

**批量归档脚本** (`scripts/bulk-archive.sh`): ```bash
#!/bin/bash
# 批量归档多个变更

for change in "$@"; do
  echo "Archiving $change..."
  openspec archive "$change" --yes

  if [ $? -eq 0 ]; then
    echo "✓ $change archived"
  else
    echo "✗ $change failed"
  fi
done
```

**使用**: ```bash
chmod +x scripts/bulk-archive.sh
./scripts/bulk-archive.sh change-1 change-2 change-3
```

### 6. 规范检查清单

**审查规范时使用**: ```markdown
## Spec Review Checklist

- [ ] 需求描述清晰
- [ ] 包含成功场景
- [ ] 包含失败场景
- [ ] 边界情况已考虑
- [ ] 性能要求已定义（如适用）
- [ ] 安全要求已定义（如适用）
- [ ] 使用 SHALL/MUST（非 SHOULD/MAY）
- [ ] 场景格式正确（WHEN/THEN）
- [ ] 可追溯（与需求关联）
```

### 7. 跨工具协作

**场景**: 团队成员使用不同 AI 工具

**解决方案**: AGENTS.md 文件

**示例** (`AGENTS.md`): ```markdown
# OpenSpec Workflow

## For All AI Tools

When asked to create a proposal:
1. Run `openspec init-change "<description>"`
2. Create comprehensive spec in `openspec/changes/`
3. Include success and failure scenarios
4. Break down into testable tasks

When asked to apply a change:
1. Read `openspec/changes/<name>/tasks.md`
2. Implement tasks in order
3. Mark tasks as complete
4. Run tests after each task

When asked to archive:
1. Verify all tasks are complete
2. Run `openspec archive <name> --yes`
3. Confirm specs are merged

## Project Context

- **Language**: Python 3.10+
- **Framework**: Django 5.2
- **Database**: SQLite
- **Testing**: pytest
- **Style**: PEP 8

## Conventions

- Use snake_case for functions and variables
- Use PascalCase for classes
- Add docstrings to all public functions
- Write tests for all new features
```

---

## 参考资源

### 官方资源

- **官网**: https://openspec.dev/
- **GitHub**: https://github.com/Fission-AI/OpenSpec
- **Discord**: 加入社区获取帮助
- **Twitter**: @0xTab（关注更新）

### 文档结构

```
项目目录/
├── docs/
│   ├── OpenSpec使用指南.md          # 本文档
│   ├── 系统架构分析文档.md
│   ├── 数据模型使用手册.md
│   └── 性能优化说明.md
├── openspec/
│   ├── specs/                      # 源规范
│   ├── changes/                    # 活动变更
│   └── archive/                    # 已归档变更
├── .claude/                        # Claude Code 配置
├── .kilocode/                      # Kilocode 配置
└── AGENTS.md                       # 代理共享配置
```

### 快速开始检查清单

- [ ] Node.js >= 20.19.0 已安装
- [ ] OpenSpec CLI 已安装: `npm install -g @fission-ai/openspec`
- [ ] 项目中运行: `openspec init`
- [ ] 选择了正确的 AI 工具（Claude Code 或 Kilocode）
- [ ] 配置目录已生成（`.claude/commands/` 或 `.kilocode/workflows/`）
- [ ] 重启 AI 工具以识别命令
- [ ] 运行: `openspec list` 验证安装
- [ ] 创建第一个提案测试完整流程

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0  | 2025-11-18 | 初始版本 |

---

**文档维护**: 开发团队
**最后更新**: 2025-11-18
