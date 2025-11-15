from io import BytesIO
from datetime import datetime
import pandas as pd
import re
from decimal import Decimal
from django.db import transaction

from project.utils.excel_beautifier import beautify_worksheet
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from project.models import Project
from project.enums import FilePositioning


CONTRACT_PARENT_COLUMN = '关联主合同编号'
CONTRACT_PROCUREMENT_COLUMN = '关联采购编号'
IMPORT_ROLLBACK_MESSAGE = '项目数据导入存在错误，所有写入已回滚'


class ProjectDataImportError(Exception):
    """批量导入校验失败时抛出的异常，附带统计信息以便前端提示。"""

    def __init__(self, message: str, stats: dict):
        super().__init__(message)
        self.stats = stats


# ========== 报表导出（统一门面，委托 report_generator，行为不变） ==========

def export_to_word(report_data, file_path: str) -> str:
    """标准版 Word 导出（兼容旧接口），委托 report_generator 实现。"""
    from project.services.report_generator import export_to_word as _export
    return _export(report_data, file_path)


def export_to_word_professional(report_data, file_path: str) -> str:
    """专业版 Word 导出（兼容旧接口），委托 report_generator 实现。"""
    from project.services.report_generator import export_to_word_professional as _export
    return _export(report_data, file_path)


def export_to_excel(report_data, file_path: str) -> str:
    """Excel 导出（兼容旧接口），委托 report_generator 实现。"""
    from project.services.report_generator import export_to_excel as _export
    return _export(report_data, file_path)


def extract_code_parts(code):
    """
    提取编号的各个部分用于排序
    处理如下格式：
    - BHHY-K-004
    - BHHY-ZC-026
    - 2025-PGCHT-014
    - 2025-PGCHT-013-001
    
    返回: (前缀部分, 主数字, 子数字或None)
    """
    if not code:
        return ('', 0, 0)
    
    # 移除空白字符
    code = str(code).strip()
    
    # 尝试匹配类似 2025-PGCHT-013-001 的格式（有子编号）
    match = re.match(r'^(.+?)-(\d+)-(\d+)$', code)
    if match:
        prefix = match.group(1)
        main_num = int(match.group(2))
        sub_num = int(match.group(3))
        return (prefix, main_num, sub_num)
    
    # 尝试匹配类似 2025-PGCHT-014 或 BHHY-K-004 的格式（无子编号）
    match = re.match(r'^(.+?)-(\d+)$', code)
    if match:
        prefix = match.group(1)
        main_num = int(match.group(2))
        return (prefix, main_num, 999999)  # 使用大数字确保无子编号的排在后面
    
    # 如果都不匹配，尝试提取所有数字
    numbers = re.findall(r'\d+', code)
    if numbers:
        return (code, int(numbers[0]), 999999)
    
    # 完全无法解析，返回字符串本身
    return (code, 0, 999999)


def sort_procurement_list(procurements):
    """
    对采购列表进行排序
    规则：
    1. 相同编号规则（前缀相同）的，按照招采编号从小到大排序
    2. 不同编号规则（前缀不同）的，按照结果公示发布时间从早到晚排序
    3. 特殊处理：2025-PGCHT-013-001 应该排在 2025-PGCHT-014 之前
    """
    def sort_key(proc):
        prefix, main_num, sub_num = extract_code_parts(proc.procurement_code)
        # 使用结果公示发布时间作为主要排序依据（用于不同前缀的情况）
        date_sort = proc.result_publicity_release_date if proc.result_publicity_release_date else datetime.max.date()
        # 返回：先按日期，再按前缀，最后按编号
        return (date_sort, prefix, main_num, sub_num)
    
    return sorted(procurements, key=sort_key)


def sort_contract_list(contracts):
    """
    对合同列表进行排序
    规则：
    1. 相同编号规则（前缀相同）的，按照合同序号从小到大排序
    2. 不同编号规则（前缀不同）的，按照合同签订日期从早到晚排序
    3. 特殊处理：2025-PGCHT-013-001 应该排在 2025-PGCHT-014 之前
    """
    def sort_key(contract):
        # 优先使用合同序号，如果没有则使用合同编号
        code = contract.contract_sequence if contract.contract_sequence else contract.contract_code
        prefix, main_num, sub_num = extract_code_parts(code)
        # 使用合同签订日期作为主要排序依据（用于不同前缀的情况）
        date_sort = contract.signing_date if contract.signing_date else datetime.max.date()
        # 返回：先按日期，再按前缀，最后按编号
        return (date_sort, prefix, main_num, sub_num)
    
    return sorted(contracts, key=sort_key)


def generate_project_excel(project, user):
    """为单个项目生成 Excel 文件,返回 BytesIO。包含采购、合同、付款、结算、供应商管理五个工作表。"""
    from settlement.models import Settlement
    from supplier_eval.models import SupplierEvaluation

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # ========== 1. 采购表 ==========
        # 参照procurement导入模板定义的字段顺序
        procurement_headers = [
            '项目编码', '招采编号', '采购项目名称', '采购单位', '中标单位',
            '中标单位联系人及方式', '采购方式', '采购类别', '采购预算金额(元)',
            '采购控制价（元）', '中标金额（元）', '计划结束采购时间',
            '候选人公示结束时间', '结果公示发布时间', '中标通知书发放日期',
            '采购经办人', '需求部门', '申请人联系电话（需求部门）',
            '采购需求书审批完成日期（OA）', '采购平台', '资格审查方式',
            '评标谈判方式', '定标方法', '公告发布时间'
        ]
        procurement_rows = []
        procurements = Procurement.objects.filter(project=project)
        sorted_procurements = sort_procurement_list(procurements)

        for procurement in sorted_procurements:
            procurement_rows.append({
                '项目编码': project.project_code,
                '招采编号': procurement.procurement_code,
                '采购项目名称': procurement.project_name,
                '采购单位': procurement.procurement_unit or '',
                '中标单位': procurement.winning_bidder or '',
                '中标单位联系人及方式': procurement.winning_contact or '',
                '采购方式': procurement.procurement_method or '',
                '采购类别': procurement.procurement_category or '',
                '采购预算金额(元)': float(procurement.budget_amount) if procurement.budget_amount else '',
                '采购控制价（元）': float(procurement.control_price) if procurement.control_price else '',
                '中标金额（元）': float(procurement.winning_amount) if procurement.winning_amount else '',
                '计划结束采购时间': procurement.planned_completion_date.strftime('%Y-%m-%d') if procurement.planned_completion_date else '',
                '候选人公示结束时间': procurement.candidate_publicity_end_date.strftime('%Y-%m-%d') if procurement.candidate_publicity_end_date else '',
                '结果公示发布时间': procurement.result_publicity_release_date.strftime('%Y-%m-%d') if procurement.result_publicity_release_date else '',
                '中标通知书发放日期': procurement.notice_issue_date.strftime('%Y-%m-%d') if procurement.notice_issue_date else '',
                '采购经办人': procurement.procurement_officer or '',
                '需求部门': procurement.demand_department or '',
                '申请人联系电话（需求部门）': procurement.demand_contact or '',
                '采购需求书审批完成日期（OA）': procurement.requirement_approval_date.strftime('%Y-%m-%d') if procurement.requirement_approval_date else '',
                '采购平台': procurement.procurement_platform or '',
                '资格审查方式': procurement.qualification_review_method or '',
                '评标谈判方式': procurement.bid_evaluation_method or '',
                '定标方法': procurement.bid_awarding_method or '',
                '公告发布时间': procurement.announcement_release_date.strftime('%Y-%m-%d') if procurement.announcement_release_date else '',
            })

        # 如果没有数据，创建空DataFrame但保留表头
        if procurement_rows:
            df_procurement = pd.DataFrame(procurement_rows)
        else:
            df_procurement = pd.DataFrame(columns=procurement_headers)
        df_procurement.to_excel(writer, sheet_name='采购表', index=False)

        # ========== 2. 合同表 ==========
        # 参照contract导入模板定义的字段顺序
        contract_headers = [
            '项目编码', '关联采购编号', '文件定位', '合同来源', '关联主合同编号',
            '合同序号', '合同编号', '合同名称', '甲方', '乙方',
            '含税签约合同价（元）', '合同签订日期'
        ]
        contract_rows = []
        contracts = Contract.objects.filter(project=project).select_related('project', 'procurement', 'parent_contract')
        sorted_contracts = sort_contract_list(contracts)

        for contract in sorted_contracts:
            contract_rows.append({
                '项目编码': project.project_code,
                '关联采购编号': contract.procurement.procurement_code if contract.procurement else '',
                '文件定位': contract.file_positioning,
                '合同来源': contract.contract_source,
                '关联主合同编号': contract.parent_contract.contract_code if contract.parent_contract else '',
                '合同序号': contract.contract_sequence or '',
                '合同编号': contract.contract_code,
                '合同名称': contract.contract_name,
                '甲方': contract.party_a or '',
                '乙方': contract.party_b,
                '含税签约合同价（元）': float(contract.contract_amount) if contract.contract_amount else '',
                '合同签订日期': contract.signing_date.strftime('%Y-%m-%d') if contract.signing_date else '',
            })

        if contract_rows:
            df_contract = pd.DataFrame(contract_rows)
        else:
            df_contract = pd.DataFrame(columns=contract_headers)
        df_contract.to_excel(writer, sheet_name='合同表', index=False)

        # ========== 3. 付款表 ==========
        # 参照payment导入模板定义的字段顺序
        payment_headers = [
            '项目编码', '付款编号', '关联合同编号',
            '实付金额(元)', '付款日期', '结算价（元）', '是否办理结算'
        ]
        payment_rows = []
        for payment in Payment.objects.filter(contract__project=project).select_related('contract').order_by('payment_date'):
            payment_rows.append({
                '项目编码': project.project_code,
                '付款编号': payment.payment_code,
                '关联合同编号': payment.contract.contract_code if payment.contract else '',
                '实付金额(元)': float(payment.payment_amount) if payment.payment_amount else '',
                '付款日期': payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else '',
                '结算价（元）': float(payment.settlement_amount) if payment.settlement_amount else '',
                '是否办理结算': '是' if payment.is_settled else '否',
            })

        if payment_rows:
            df_payment = pd.DataFrame(payment_rows)
        else:
            df_payment = pd.DataFrame(columns=payment_headers)
        df_payment.to_excel(writer, sheet_name='付款表', index=False)

        # ========== 4. 结算表 ==========
        # 需求：包含全部合同（已结算和未结算），包含字段：序号、关联合同名称、关联合同序号、是否已结算、最终结算金额(元)
        settlement_headers = [
            '序号', '关联合同名称', '关联合同序号', '是否已结算', '最终结算金额(元)'
        ]
        settlement_rows = []

        # 获取所有主合同（结算只能关联主合同）
        main_contracts = Contract.objects.filter(
            project=project,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        ).select_related('project').order_by('contract_sequence', 'contract_code')

        for idx, contract in enumerate(main_contracts, start=1):
            # 尝试获取结算记录
            try:
                settlement = Settlement.objects.get(main_contract=contract)
                is_settled = '是'
                final_amount = float(settlement.final_amount) if settlement.final_amount else ''
            except Settlement.DoesNotExist:
                is_settled = '否'
                final_amount = ''

            settlement_rows.append({
                '序号': idx,
                '关联合同名称': contract.contract_name,
                '关联合同序号': contract.contract_sequence or contract.contract_code,
                '是否已结算': is_settled,
                '最终结算金额(元)': final_amount,
            })

        if settlement_rows:
            df_settlement = pd.DataFrame(settlement_rows)
        else:
            df_settlement = pd.DataFrame(columns=settlement_headers)
        df_settlement.to_excel(writer, sheet_name='结算表', index=False)

        # ========== 5. 供应商管理表 ==========
        # 需求：过程履约评价和不定期履约评价字段需要动态生成
        # 基础字段：序号、合同编号、供应商名称、履约综合评价得分、末次评价得分
        supplier_eval_headers = ['序号', '合同编号', '供应商名称', '履约综合评价得分', '末次评价得分']

        # 获取所有评价记录
        evaluations = SupplierEvaluation.objects.filter(
            contract__project=project
        ).select_related('contract').order_by('contract__contract_sequence', 'contract__contract_code')

        # 动态收集所有年度评价和不定期评价的列
        all_years = set()
        max_irregular_count = 0

        for evaluation in evaluations:
            # 收集年度评价的年份
            if evaluation.annual_scores:
                all_years.update(evaluation.annual_scores.keys())
            # 收集不定期评价的最大次数
            if evaluation.irregular_scores:
                irregular_indices = [int(k) for k in evaluation.irregular_scores.keys()]
                if irregular_indices:
                    max_irregular_count = max(max_irregular_count, max(irregular_indices))

        # 年度评价列（按年份排序）
        sorted_years = sorted([int(y) for y in all_years])
        for year in sorted_years:
            supplier_eval_headers.append(f'{year}年度过程履约评价')

        # 不定期评价列
        for i in range(1, max_irregular_count + 1):
            supplier_eval_headers.append(f'第{i}次不定期履约评价')

        supplier_eval_rows = []
        for idx, evaluation in enumerate(evaluations, start=1):
            row = {
                '序号': idx,
                '合同编号': evaluation.contract.contract_code if evaluation.contract else '',
                '供应商名称': evaluation.supplier_name,
                '履约综合评价得分': float(evaluation.comprehensive_score) if evaluation.comprehensive_score else '',
                '末次评价得分': float(evaluation.last_evaluation_score) if evaluation.last_evaluation_score else '',
            }

            # 填充年度评价得分
            for year in sorted_years:
                year_key = str(year)
                score = evaluation.annual_scores.get(year_key) if evaluation.annual_scores else None
                row[f'{year}年度过程履约评价'] = float(score) if score is not None else ''

            # 填充不定期评价得分
            for i in range(1, max_irregular_count + 1):
                index_key = str(i)
                score = evaluation.irregular_scores.get(index_key) if evaluation.irregular_scores else None
                row[f'第{i}次不定期履约评价'] = float(score) if score is not None else ''

            supplier_eval_rows.append(row)

        if supplier_eval_rows:
            df_supplier_eval = pd.DataFrame(supplier_eval_rows)
        else:
            df_supplier_eval = pd.DataFrame(columns=supplier_eval_headers)
        df_supplier_eval.to_excel(writer, sheet_name='供应商管理表', index=False)

        # 美化样式
        for sheet in writer.book.sheetnames:
            beautify_worksheet(writer.sheets[sheet])

    output.seek(0)
    return output




def import_project_excel(file_obj, project_code, user=None):
    """
    从Excel文件导入项目数据，替换指定项目的所有数据
    
    Args:
        file_obj: Excel文件对象（BytesIO或文件路径）
        project_code: 要导入的项目编码
        user: 当前操作用户
    
    Returns:
        dict: 包含导入统计信息的字典
    """
    stats = {
        'project_updated': False,
        'procurements_created': 0,
        'contracts_created': 0,
        'payments_created': 0,
        'procurements_deleted': 0,
        'contracts_deleted': 0,
        'payments_deleted': 0,
        'errors': []
    }
    def _clean_cell(value):
        if pd.notna(value):
            text = str(value).strip()
            if text and text.lower() != 'nan':
                return text
        return ''
    
    try:
        # 读取Excel文件的所有工作表
        excel_data = pd.read_excel(file_obj, sheet_name=None, dtype=str)
        
        # 检查必需的工作表
        required_sheets = ['项目信息', '采购信息', '合同信息', '付款信息']
        for sheet_name in required_sheets:
            if sheet_name not in excel_data:
                raise ValueError(f'Excel文件缺少必需的工作表：{sheet_name}')
        
        # 开始事务
        with transaction.atomic():
            # 1. 验证项目是否存在
            try:
                project = Project.objects.get(project_code=project_code)
            except Project.DoesNotExist:
                raise ValueError(f'项目不存在：{project_code}')
            
            procurement_cache = {}
            # 2. 删除该项目下的所有关联数据
            # 注意：由于外键关系，需要按照依赖顺序删除
            # 付款 -> 合同 -> 采购
            
            # 删除付款记录（通过合同关联）
            deleted_payments = Payment.objects.filter(contract__project=project).delete()[0]
            stats['payments_deleted'] = deleted_payments
            
            # 删除合同记录
            deleted_contracts = Contract.objects.filter(project=project).delete()[0]
            stats['contracts_deleted'] = deleted_contracts
            
            # 删除采购记录
            deleted_procurements = Procurement.objects.filter(project=project).delete()[0]
            stats['procurements_deleted'] = deleted_procurements
            
            # 3. 更新项目信息
            project_df = excel_data['项目信息']
            if not project_df.empty:
                row = project_df.iloc[0]
                project.project_name = str(row.get('项目名称', project.project_name))
                project.description = str(row.get('项目描述', '')) if pd.notna(row.get('项目描述')) else ''
                project.project_manager = str(row.get('项目负责人', '')) if pd.notna(row.get('项目负责人')) else ''
                project.status = str(row.get('项目状态', project.status))
                project.remarks = str(row.get('备注', '')) if pd.notna(row.get('备注')) else ''
                project.save()
                stats['project_updated'] = True
            
            # 4. 导入采购信息
            procurement_df = excel_data['采购信息']
            for _, row in procurement_df.iterrows():
                procurement_code = ''
                try:
                    procurement_code = str(row.get('招采编号', '')).strip()
                    if not procurement_code or procurement_code == 'nan':
                        continue
                    
                    procurement_data = {
                        'procurement_code': procurement_code,
                        'project': project,
                        'project_name': str(row.get('采购项目名称', '')) if pd.notna(row.get('采购项目名称')) else '',
                        'procurement_unit': str(row.get('采购单位', '')) if pd.notna(row.get('采购单位')) else '',
                        'winning_bidder': str(row.get('中标单位', '')) if pd.notna(row.get('中标单位')) else '',
                        'winning_contact': str(row.get('中标单位联系人及方式', '')) if pd.notna(row.get('中标单位联系人及方式')) else '',
                        'procurement_method': str(row.get('采购方式', '')) if pd.notna(row.get('采购方式')) else '',
                        'procurement_category': str(row.get('采购类别', '')) if pd.notna(row.get('采购类别')) else '',
                        'procurement_officer': str(row.get('采购经办人', '')) if pd.notna(row.get('采购经办人')) else '',
                        'demand_department': str(row.get('需求部门', '')) if pd.notna(row.get('需求部门')) else '',
                        'demand_contact': str(row.get('申请人联系电话（需求部门）', '')) if pd.notna(row.get('申请人联系电话（需求部门）')) else '',
                        'procurement_platform': str(row.get('采购平台', '')) if pd.notna(row.get('采购平台')) else '',
                        'qualification_review_method': str(row.get('资格审查方式', '')) if pd.notna(row.get('资格审查方式')) else '',
                        'bid_evaluation_method': str(row.get('评标谈判方式', '')) if pd.notna(row.get('评标谈判方式')) else '',
                        'bid_awarding_method': str(row.get('定标方法', '')) if pd.notna(row.get('定标方法')) else '',
                    }
                    
                    # 处理金额字段
                    for field in ['budget_amount', 'control_price', 'winning_amount']:
                        col_name = {
                            'budget_amount': '采购预算金额(元)',
                            'control_price': '采购控制价（元）',
                            'winning_amount': '中标金额（元）'
                        }[field]
                        value = row.get(col_name)
                        if pd.notna(value) and str(value).strip() and str(value) != '0':
                            try:
                                procurement_data[field] = Decimal(str(value))
                            except:
                                procurement_data[field] = None
                        else:
                            procurement_data[field] = None
                    
                    # 处理日期字段
                    date_fields = {
                        'planned_completion_date': '计划结束采购时间',
                        'candidate_publicity_end_date': '候选人公示结束时间',
                        'result_publicity_release_date': '结果公示发布时间',
                        'notice_issue_date': '中标通知书发放日期',
                        'requirement_approval_date': '采购需求书审批完成日期（OA）',
                        'announcement_release_date': '公告发布时间'
                    }
                    
                    for field, col_name in date_fields.items():
                        value = row.get(col_name)
                        if pd.notna(value) and str(value).strip():
                            try:
                                procurement_data[field] = pd.to_datetime(str(value)).date()
                            except:
                                procurement_data[field] = None
                        else:
                            procurement_data[field] = None
                    
                    if user:
                        procurement_data['created_by'] = user.username
                        procurement_data['updated_by'] = user.username
                    
                    procurement = Procurement.objects.create(**procurement_data)
                    procurement_cache[procurement_code] = procurement
                    stats['procurements_created'] += 1
                    
                except Exception as e:
                    stats['errors'].append(f"采购记录导入失败 [{procurement_code}]: {str(e)}")
            
            def _create_contracts_with_dependencies(contract_rows):
                def _row_hint(info: dict) -> str:
                    row_number = info.get('row_number')
                    return f"第{row_number}行" if row_number else "未知行"
                priority_map = {
                    FilePositioning.MAIN_CONTRACT.value: 0,
                    FilePositioning.FRAMEWORK.value: 1,
                }
                pending = sorted(
                    contract_rows,
                    key=lambda info: (priority_map.get(info['file_positioning'], 2), info['contract_code'])
                )
                created = {}
                while pending:
                    progress = False
                    next_pending = []
                    for info in pending:
                        parent_code = info['parent_contract_code']
                        if parent_code:
                            parent_contract = created.get(parent_code)
                            if not parent_contract:
                                next_pending.append(info)
                                continue
                        else:
                            parent_contract = None
                        procurement = None
                        procurement_code = info['procurement_code']
                        if procurement_code:
                            procurement = procurement_cache.get(procurement_code)
                            if not procurement:
                                stats['errors'].append(
                                    f"合同记录导入失败（{_row_hint(info)}）[{info['contract_code']}]: 关联采购不存在 {procurement_code}"
                                )
                                continue
                        contract_data = info['data'].copy()
                        contract_data['parent_contract'] = parent_contract
                        contract_data['procurement'] = procurement
                        try:
                            contract = Contract.objects.create(**contract_data)
                        except Exception as exc:
                            stats['errors'].append(
                                f"合同记录导入失败（{_row_hint(info)}）[{info['contract_code']}]: {str(exc)}"
                            )
                            continue
                        created[info['contract_code']] = contract
                        stats['contracts_created'] += 1
                        progress = True
                    if not progress:
                        for info in next_pending:
                            parent_hint = info['parent_contract_code']
                            if parent_hint:
                                stats['errors'].append(
                                    f"合同记录导入失败（{_row_hint(info)}）[{info['contract_code']}]: 关联主合同 {parent_hint} 未在文件中提供或顺序错误"
                                )
                            else:
                                stats['errors'].append(
                                    f"合同记录导入失败（{_row_hint(info)}）[{info['contract_code']}]: 未能解析依赖关系"
                                )
                        break
                    pending = next_pending
                return created
            # 5. 导入合同信息
            contract_df = excel_data['合同信息']
            contract_rows = []
            for idx, row in contract_df.iterrows():
                contract_code = ''
                try:
                    contract_code = _clean_cell(row.get('合同编号', ''))
                    if not contract_code:
                        continue

                    file_positioning_value = row.get('文件定位', '')
                    file_positioning = _clean_cell(file_positioning_value)
                    if not file_positioning:
                        file_positioning = FilePositioning.MAIN_CONTRACT.value

                    contract_data = {
                        'contract_code': contract_code,
                        'project': project,
                        'contract_name': str(row.get('合同名称', '')) if pd.notna(row.get('合同名称')) else '',
                        'contract_sequence': _clean_cell(row.get('合同编号', '')) or None,
                        'file_positioning': file_positioning,
                        'contract_source': str(row.get('合同来源', '')) if pd.notna(row.get('合同来源')) else '',
                        'party_b': str(row.get('乙方', '')) if pd.notna(row.get('乙方')) else '',
                    }

                    amount_value = row.get('合同金额(元)')
                    if pd.notna(amount_value) and str(amount_value).strip() and str(amount_value) != '0':
                        try:
                            contract_data['contract_amount'] = Decimal(str(amount_value))
                        except:
                            contract_data['contract_amount'] = None
                    else:
                        contract_data['contract_amount'] = None

                    signing_date = row.get('签订日期')
                    if pd.notna(signing_date) and str(signing_date).strip():
                        try:
                            contract_data['signing_date'] = pd.to_datetime(str(signing_date)).date()
                        except:
                            contract_data['signing_date'] = None
                    else:
                        contract_data['signing_date'] = None

                    if user:
                        contract_data['created_by'] = user.username
                        contract_data['updated_by'] = user.username

                    parent_contract_code = _clean_cell(row.get(CONTRACT_PARENT_COLUMN))
                    procurement_code = _clean_cell(row.get(CONTRACT_PROCUREMENT_COLUMN))

                    contract_rows.append({
                        'row_number': idx + 2,
                        'contract_code': contract_code,
                        'file_positioning': file_positioning,
                        'parent_contract_code': parent_contract_code,
                        'procurement_code': procurement_code,
                        'data': contract_data,
                    })

                except Exception as e:
                    stats['errors'].append(f"合同记录导入失败 [{contract_code}]: {str(e)}")

            contract_cache = _create_contracts_with_dependencies(contract_rows)
            # 6. 导入付款信息
            payment_df = excel_data['付款信息']
            for _, row in payment_df.iterrows():
                payment_code = ''
                try:
                    payment_code = str(row.get('付款编号', '')).strip()
                    contract_code = str(row.get('关联合同编号', '')).strip()
                    
                    if not payment_code or payment_code == 'nan':
                        continue
                    
                    if not contract_code or contract_code == 'nan':
                        stats['errors'].append(f"付款记录 [{payment_code}] 缺少关联合同编号")
                        continue
                    
                    # 查找关联合同
                    contract = contract_cache.get(contract_code)
                    if not contract:
                        stats['errors'].append(f"付款记录 [{payment_code}] 的关联合同不存在: {contract_code}")
                        continue
                        continue
                    
                    payment_data = {
                        'payment_code': payment_code,
                        'contract': contract,
                        'is_settled': str(row.get('是否结算', '')).strip() == '是',
                    }
                    
                    # 处理金额字段
                    for field, col_name in [('payment_amount', '付款金额(元)'), ('settlement_amount', '结算价(元)')]:
                        value = row.get(col_name)
                        if pd.notna(value) and str(value).strip() and str(value) != '0':
                            try:
                                payment_data[field] = Decimal(str(value))
                            except:
                                payment_data[field] = None
                        else:
                            payment_data[field] = None
                    
                    # 处理付款日期
                    payment_date = row.get('付款日期')
                    if pd.notna(payment_date) and str(payment_date).strip():
                        try:
                            payment_data['payment_date'] = pd.to_datetime(str(payment_date)).date()
                        except:
                            payment_data['payment_date'] = None
                    else:
                        payment_data['payment_date'] = None
                    
                    if user:
                        payment_data['created_by'] = user.username
                        payment_data['updated_by'] = user.username
                    
                    Payment.objects.create(**payment_data)
                    stats['payments_created'] += 1
                    
                except Exception as e:
                    stats['errors'].append(f"付款记录导入失败 [{payment_code}]: {str(e)}")
        
        if stats['errors']:
            raise ProjectDataImportError(IMPORT_ROLLBACK_MESSAGE, stats)
        return stats

    except ProjectDataImportError:
        raise
    except Exception as e:
        stats['errors'].append(f"������̷�������: {str(e)}")
        raise ProjectDataImportError(str(e), stats)
