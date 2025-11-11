from io import BytesIO
from datetime import datetime
import pandas as pd

from project.utils.excel_beautifier import beautify_worksheet
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment


def generate_project_excel(project, user):
    """为单个项目生成 Excel 文件，返回 BytesIO。"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        project_data = [{
            '项目编码': project.project_code,
            '项目名称': project.project_name,
            '项目描述': project.description or '',
            '项目负责人': project.project_manager or '',
            '项目状态': project.status,
            '备注': project.remarks or '',
            '创建时间': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else '',
            '更新时间': project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else '',
        }]
        df_projects = pd.DataFrame(project_data)
        df_projects.to_excel(writer, sheet_name='项目信息', index=False)

        procurement_rows = []
        for procurement in Procurement.objects.filter(project=project):
            procurement_rows.append({
                '项目编码': project.project_code,
                '项目名称': project.project_name,
                '招采编号': procurement.procurement_code,
                '采购项目名称': procurement.project_name,
                '采购单位': procurement.procurement_unit or '',
                '中标单位': procurement.winning_bidder or '',
                '中标单位联系人及方式': procurement.winning_contact or '',
                '采购方式': procurement.procurement_method or '',
                '采购类别': procurement.procurement_category or '',
                '采购预算金额(元)': float(procurement.budget_amount) if procurement.budget_amount else 0,
                '采购控制价（元）': float(procurement.control_price) if procurement.control_price else 0,
                '中标金额（元）': float(procurement.winning_amount) if procurement.winning_amount else 0,
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
        pd.DataFrame(procurement_rows).to_excel(writer, sheet_name='采购信息', index=False)

        contract_rows = []
        contracts = Contract.objects.filter(project=project).select_related('project').prefetch_related('payments')
        for contract in contracts:
            total_paid = sum(p.payment_amount or 0 for p in contract.payments.all())
            payment_count = contract.payments.count()
            contract_rows.append({
                '项目编码': project.project_code,
                '项目名称': project.project_name,
                '合同编号': contract.contract_code,
                '合同序号': contract.contract_sequence,
                '合同名称': contract.contract_name,
                '文件定位': contract.file_positioning,
                '合同来源': contract.contract_source,
                '乙方': contract.party_b,
                '合同金额(元)': float(contract.contract_amount) if contract.contract_amount else 0,
                '签订日期': contract.signing_date.strftime('%Y-%m-%d') if contract.signing_date else '',
                '累计付款(元)': float(total_paid),
                '付款笔数': payment_count,
            })
        pd.DataFrame(contract_rows).to_excel(writer, sheet_name='合同信息', index=False)

        payment_rows = []
        for payment in Payment.objects.filter(contract__project=project).select_related('contract'):
            payment_rows.append({
                '项目编码': project.project_code,
                '项目名称': project.project_name,
                '关联合同编号': payment.contract.contract_code if payment.contract else '',
                '付款编号': payment.payment_code,
                '付款金额(元)': float(payment.payment_amount) if payment.payment_amount else 0,
                '付款日期': payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else '',
                '是否结算': '是' if payment.is_settled else '否',
                '结算价(元)': float(payment.settlement_amount) if payment.settlement_amount else 0,
            })
        pd.DataFrame(payment_rows).to_excel(writer, sheet_name='付款信息', index=False)

        # 美化样式（示例：对金额列应用格式）
        for sheet in writer.book.sheetnames:
            beautify_worksheet(writer.sheets[sheet])

    output.seek(0)
    return output

