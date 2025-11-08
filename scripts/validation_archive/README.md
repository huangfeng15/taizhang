# 测试验证脚本归档

本目录包含项目开发阶段的一次性验证脚本，用于验证特定功能的正确性。

## 脚本说明

### test_procurement_dedup_statistics.py (143行)
**用途**: 验证采购数据去重统计逻辑的正确性

**验证内容**:
- 采购记录的去重规则
- 统计数据的一致性
- 边界情况处理

**使用场景**: 修改采购统计逻辑后的回归验证

---

### test_statistics_detail_consistency.py (181行)
**用途**: 验证统计数据与明细数据的一致性

**验证内容**:
- 汇总数据与明细数据的匹配
- 各业务模块统计的准确性
- 数据完整性检查

**使用场景**: 统计服务重构后的数据一致性验证

---

### test_helptext.py (124行)
**用途**: 测试模型字段的帮助文本配置

**验证内容**:
- 字段help_text的完整性
- 帮助文本的可读性
- 多语言支持（如适用）

**使用场景**: 模型字段修改后的文档完整性检查

---

### validate_helptext.py (155行)
**用途**: 验证帮助文本的格式和内容规范

**验证内容**:
- 帮助文本格式规范
- 术语使用一致性
- 文本长度限制

**使用场景**: 批量更新帮助文本后的质量检查

---

## 归档原因

这些脚本是**一次性验证工具**，完成了特定阶段的质量保证任务。归档而非删除的原因：

1. **参考价值**: 提供了测试用例的实现参考
2. **可复用性**: 未来类似功能修改时可以快速复用
3. **历史记录**: 保留项目质量保证的历史轨迹

## 建议

这些验证逻辑应该转换为正式的单元测试，集成到CI/CD流程中：

```python
# 推荐做法：转换为单元测试
# project/tests/test_procurement_statistics.py

from django.test import TestCase
from project.services.statistics import get_procurement_statistics

class ProcurementStatisticsTest(TestCase):
    def test_deduplication_logic(self):
        # 原test_procurement_dedup_statistics.py的验证逻辑
        pass
```

## 使用方法

如需运行这些脚本：

```bash
# 进入项目根目录
cd D:\develop\new pachong yangguangcaigou\taizhang

# 激活虚拟环境
venv\Scripts\activate

# 运行验证脚本
python scripts/validation_archive/test_procurement_dedup_statistics.py
```

---

遵循YAGNI原则，将完成使命的验证脚本移出主脚本目录，保持代码库整洁的同时保留其参考价值。
