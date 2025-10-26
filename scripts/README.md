# Scripts 目录说明

本目录包含项目的辅助脚本工具。

## 核心脚本(保留)

### 数据导入相关
- `prepare_import_data.py` - 数据预处理与格式验证
- `check_table_data.py` - 业务表数据统计
- `check_data_statistics.py` - 数据完整性检查

### 数据库查询工具
- `query_database.py` - 通用数据库查询工具
- `db_query.bat` - Windows快捷查询脚本
- `db_query.sh` - Linux/Mac快捷查询脚本
- `数据库查询工具使用说明.md` - 查询工具使用文档

### 权限管理
- `set_staff_permission.bat` - 用户权限设置

## 使用示例

### 数据导入前预处理
```bash
python scripts/prepare_import_data.py data/source.xlsx
```

### 数据统计检查
```bash
python scripts/check_table_data.py
python scripts/check_data_statistics.py
```

### 数据库查询
```bash
# Windows
scripts\db_query.bat "SELECT * FROM contract_contract LIMIT 10"

# Linux/Mac
./scripts/db_query.sh "SELECT * FROM contract_contract LIMIT 10"
```

## 已废弃脚本(可移除)

以下脚本为临时诊断工具,开发完成后可删除:
- `diagnose_csv_budget.py`
- `diagnose_project_import.py`
- `diagnose_real_scenario.py`
- `diagnose_seq_calculation.py`
- `fix_payment_codes.py`
- `convert_excel_to_csv.py`
- `count_tables.py`