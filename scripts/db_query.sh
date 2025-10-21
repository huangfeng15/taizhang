#!/bin/bash

echo "数据库查询工具"
echo "================"
echo

if [ $# -eq 0 ]; then
    echo "用法:"
    echo "  ./db_query.sh \"SQL语句\" [格式]"
    echo "  ./db_query.sh --list-tables"
    echo "  ./db_query.sh --describe 表名"
    echo "  ./db_query.sh --count 表名"
    echo
    echo "示例:"
    echo "  ./db_query.sh \"SELECT * FROM contract_contract LIMIT 10\""
    echo "  ./db_query.sh \"SELECT * FROM contract_contract LIMIT 10\" json"
    echo "  ./db_query.sh --list-tables"
    echo "  ./db_query.sh --describe contract_contract"
    echo "  ./db_query.sh --count contract_contract"
    echo
    echo "或者直接运行进入交互模式:"
    echo "  ./db_query.sh"
    echo
    exit 0
fi

python scripts/query_database.py "$@"