"""
人员统计通用工具

目的：归档统计与周期统计存在相似的“按人员聚合计数”逻辑，
抽取为公共实现以遵循 DRY，且不改变原有外部行为。
"""
from __future__ import annotations

from typing import List, Dict, Optional

from procurement.models import Procurement
from contract.models import Contract
from django.db.models import Count


def get_person_list(
    *,
    year_filter: Optional[int] = None,
    global_project: Optional[str] = None,
    procurement_method: Optional[str] = None,
) -> List[Dict[str, int]]:
    """
    汇总“采购/合同负责人”的工作量计数，并返回按 count 降序的人员列表。

    Args:
        year_filter: 年份过滤（None 或 'all' 表示全量）
        global_project: 指定项目ID（project_id）过滤（与现有实现保持一致）
        procurement_method: 仅在周期统计中使用的额外过滤条件

    Returns:
        [{'name': '张三', 'count': 10}, ...]
    """
    # 采购负责人计数
    procurement_officers = Procurement.objects.values('procurement_officer').annotate(
        count=Count('procurement_code')
    ).filter(procurement_officer__isnull=False)

    if year_filter and year_filter != 'all':
        procurement_officers = procurement_officers.filter(
            result_publicity_release_date__year=int(year_filter)
        )
    if global_project:
        procurement_officers = procurement_officers.filter(project_id=global_project)
    if procurement_method:
        procurement_officers = procurement_officers.filter(procurement_method=procurement_method)

    # 合同负责人计数
    contract_officers = Contract.objects.values('contract_officer').annotate(
        count=Count('contract_code')
    ).filter(contract_officer__isnull=False)

    if year_filter and year_filter != 'all':
        contract_officers = contract_officers.filter(signing_date__year=int(year_filter))
    if global_project:
        contract_officers = contract_officers.filter(project_id=global_project)

    # 合并去重
    person_dict: Dict[str, int] = {}
    for item in procurement_officers:
        name = item['procurement_officer']
        person_dict[name] = person_dict.get(name, 0) + item['count']
    for item in contract_officers:
        name = item['contract_officer']
        person_dict[name] = person_dict.get(name, 0) + item['count']

    result = [{'name': name, 'count': cnt} for name, cnt in person_dict.items()]
    result.sort(key=lambda x: x['count'], reverse=True)
    return result
