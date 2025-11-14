
                    'type': 'contract'
                })
            
            # 归档里程碑
            if c.archive_date and self.start_date <= c.archive_date <= self.end_date:
                milestones.append({
                    'date': c.archive_date.isoformat(),
                    'event': f'完成归档：{c.contract_name}',
                    'type': 'archive'
                })
        
        # 按日期排序
        milestones.sort(key=lambda x: x['date'])
        return milestones[:20]  # 限制20条
    
    def _get_contract_paid_amount(self, contract_code: str) -> float:
        """获取合同已支付金额"""
        total = Payment.objects.filter(
            contract__contract_code=contract_code
        ).aggregate(total=Sum('payment_amount'))['total'] or 0
        return round(total / 10000, 2)
    
    def _calculate_execution_rate(self, contract_code: str) -> float:
        """计算合同执行率"""
        contract = Contract.objects.filter(contract_code=contract_code).first()
        if not contract or not contract.contract_amount:
            return 0
        
        paid_amount = Payment.objects.filter(
            contract__contract_code=contract_code
        ).aggregate(total=Sum('payment_amount'))['total'] or 0
        
        return round(paid_amount / contract.contract_amount * 100, 1)
    
    def _format_archive_issues(self, archive_data: Dict, archive_problems: Dict) -> Dict[str, Any]:
        """格式化归档问题数据"""
        # 从problems获取超期清单
        procurement_overdue = archive_problems.get('procurement', [])
        contract_overdue = archive_problems.get('contract', [])
        
        # 统计数据
        statistics = {
            'procurement_overdue': len(procurement_overdue),
            'contract_overdue': len(contract_overdue),
            'avg_overdue_days': self._calc_avg_overdue_days(procurement_overdue + contract_overdue)
        }
        
        # 超期清单（限制50条）
        overdue_list = []
        for item in procurement_overdue[:25]:
            overdue_list.append({
                'code': item.get('code', ''),
                'name': item.get('name', ''),
                'type': '采购',
                'business_date': item.get('business_date', ''),
                'archive_deadline': item.get('archive_deadline', ''),
                'overdue_days': item.get('overdue_days', 0),
                'person': item.get('responsible_person', ''),
                'project': item.get('project_code', '')
            })
        
        for item in contract_overdue[:25]:
            overdue_list.append({
                'code': item.get('code', ''),
                'name': item.get('name', ''),
                'type': '合同',
                'business_date': item.get('business_date', ''),
                'archive_deadline': item.get('archive_deadline', ''),
                'overdue_days': item.get('overdue_days', 0),
                'person': item.get('responsible_person', ''),
                'project': item.get('project_code', '')
            })
        
        # 责任人分布
        person_distribution = self._calc_person_distribution(procurement_overdue + contract_overdue)
        
        return {
            'statistics': statistics,
            'overdue_list': overdue_list,
            'person_distribution': person_distribution
        }
    
    def _format_update_issues(self, update_data: Dict, update_problems: Dict) -> Dict[str, Any]:
        """格式化更新问题数据"""
        # 提取延迟记录
        procurement_delayed = update_problems.get('procurement', [])
        contract_delayed = update_problems.get('contract', [])
        payment_delayed = update_problems.get('payment', [])
        settlement_delayed = update_problems.get('settlement', [])
        
        all_delayed = procurement_delayed + contract_delayed + payment_delayed + settlement_delayed
        
        # 统计数据
        statistics = {
            'procurement_delayed': len(procurement_delayed),
            'contract_delayed': len(contract_delayed),
            'payment_delayed': len(payment_delayed),
            'settlement_delayed': len(settlement_delayed),
            'total_delayed': len(all_delayed),
            'avg_delay_days': self._calc_avg_delay_days(all_delayed)
        }
        
        # 延迟清单（限制50条）
        delayed_list = []
        for item in all_delayed[:50]:
            delayed_list.append({
                'code': item.get('code', ''),
                'name': item.get('name', ''),
                'module': item.get('module', ''),
                'business_date': item.get('business_date', ''),
                'update_deadline': item.get('update_deadline', ''),
                'actual_update_date': item.get('actual_update_date', ''),
                'delay_days': item.get('delay_days', 0),
                'person': item.get('responsible_person', '')
            })
        
        return {
            'statistics': statistics,
            'delayed_list': delayed_list
        }
    
    def _format_completeness_issues(self, completeness_data: Dict) -> Dict[str, Any]:
        """格式化齐全性问题数据"""
        summary = completeness_data.get('summary', {})
        
        statistics = {
            'procurement_total': summary.get('procurement_total', 0),
            'procurement_complete': summary.get('procurement_complete', 0),
            'procurement_rate': summary.get('procurement_rate', 0),
            'contract_total': summary.get('contract_total', 0),
            'contract_complete': summary.get('contract_complete', 0),
            'contract_rate': summary.get('contract_rate', 0),
            'overall_rate': summary.get('overall_rate', 0)
        }
        
        return {
            'statistics': statistics
        }
    
    def _build_issues_summary(self, archive_problems: Dict, update_problems: Dict, 
                             completeness_data: Dict) -> Dict[str, Any]:
        """构建问题汇总分析"""
        # 统计各类问题总数
        total_archive = len(archive_problems.get('procurement', [])) + len(archive_problems.get('contract', []))
        total_update = sum(len(v) for v in [
            update_problems.get('procurement', []),
            update_problems.get('contract', []),
            update_problems.get('payment', []),
            update_problems.get('settlement', [])
        ])
        
        summary = completeness_data.get('summary', {})
        total_completeness = (summary.get('procurement_total', 0) - summary.get('procurement_complete', 0) +
                            summary.get('contract_total', 0) - summary.get('contract_complete', 0))
        
        # 问题严重程度分级（简化版）
        high_risk = sum(1 for item in archive_problems.get('procurement', []) + archive_problems.get('contract', [])
                       if item.get('overdue_days', 0) > 30)
        medium_risk = total_archive - high_risk
        
        return {
            'total_issues': total_archive + total_update + total_completeness,
            'severity': {
                'high': high_risk,
                'medium': medium_risk,
                'low': total_update
            },
            'by_type': {
                'archive': total_archive,
                'update': total_update,
                'completeness': total_completeness
            }
        }
    
    def _calc_avg_overdue_days(self, items: List[Dict]) -> float:
        """计算平均超期天数"""
        if not items:
            return 0
        total_days = sum(item.get('overdue_days', 0) for item in items)
        return round(total_days / len(items), 1)
    
    def _calc_avg_delay_days(self, items: List[Dict]) -> float:
        """计算平均延迟天数"""
        if not items:
            return 0
        total_days = sum(item.get('delay_days', 0) for item in items)
        return round(total_days / len(items), 1)
    
    def _calc_person_distribution(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """计算责任人问题分布"""
        person_stats = {}
        
        for item in items:
            person = item.get('responsible_person', '未知')
            if person not in person_stats:
                person_stats[person] = {
                    'person': person,
                    'count': 0,
                    'total_overdue_days': 0
                }
            
            person_stats[person]['count'] += 1
            person_stats[person]['total_overdue_days'] += item.get('overdue_days', 0)
        
        # 计算平均超期天数并排序
        result = []
        for stats in person_stats.values():
            result.append({
                'person': stats['person'],
                'count': stats['count'],
                'avg_overdue_days': round(stats['total_overdue_days'] / stats['count'], 1)
            })
        
        result.sort(key=lambda x: x['count'], reverse=True)
        return result[:10]  # 返回前10名