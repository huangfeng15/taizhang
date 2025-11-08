# PDF字段提取配置

## 当前版本

- `field_mapping.yml`: v2.0 - 生产环境使用，100%提取率验证版本
- `pdf_patterns.yml`: PDF类型识别模式配置

## 配置说明

### field_mapping.yml

定义了5种PDF文档类型的字段提取规则：

1. **procurement_request** - 采购请示OA审批
2. **control_price_approval** - 采购控制价OA审批
3. **procurement_notice** - 采购公告
4. **candidate_publicity** - 中标候选人公示
5. **result_publicity** - 采购结果公示

每种类型包含：
- 字段映射关系（PDF字段 → 数据库字段）
- 提取方法（horizontal_keyvalue, vertical_keyvalue, amount, date等）
- 特殊处理规则

### pdf_patterns.yml

定义PDF类型识别的关键词模式，用于自动判断PDF文档类型。

## 版本管理原则

遵循KISS和YAGNI原则：
- 配置文件的版本历史通过Git管理，无需在文件名中添加版本号
- 只保留当前使用的配置文件
- 重大配置变更应先在测试环境验证后再替换生产配置

## 修改配置

修改配置后需要：
1. 使用`pdf_import/standalone_extract.py`验证提取效果
2. 确保所有PDF类型的提取率达到预期
3. 提交前在commit message中说明变更原因
