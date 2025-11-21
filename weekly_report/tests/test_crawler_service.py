"""
爬虫服务单元测试
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from weekly_report.services.crawler_service import CrawlerService


@pytest.mark.asyncio
class TestCrawlerService:
    """爬虫服务测试类"""
    
    async def test_initialize(self):
        """测试浏览器初始化"""
        crawler = CrawlerService()
        
        # 模拟初始化
        with patch('weekly_report.services.crawler_service.async_playwright') as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright)
            mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            
            await crawler.initialize()
            
            assert crawler.browser is not None
            assert crawler.context is not None
            assert crawler.page is not None
    
    def test_parse_amount(self):
        """测试金额解析"""
        crawler = CrawlerService()
        
        # 测试各种金额格式
        test_cases = [
            ("100000元", Decimal("100000")),
            ("10万元", Decimal("100000")),
            ("￥50,000.00", Decimal("50000")),
            ("1000千元", Decimal("1000000")),
        ]
        
        for input_value, expected in test_cases:
            result = crawler._parse_amount(input_value)
            assert result == expected, f"解析 {input_value} 失败，期望 {expected}，得到 {result}"
    
    def test_parse_date(self):
        """测试日期解析"""
        crawler = CrawlerService()
        
        # 测试各种日期格式
        test_cases = [
            ("2025-01-15", "2025-01-15"),
            ("2025年01月15日", "2025-01-15"),
            ("2025/01/15", "2025-01-15"),
        ]
        
        for input_value, expected in test_cases:
            result = crawler._parse_date(input_value)
            assert result == expected, f"解析 {input_value} 失败"
    
    def test_clean_text(self):
        """测试文本清洗"""
        crawler = CrawlerService()
        
        # 测试文本清洗
        test_cases = [
            ("  测试文本  ", "测试文本"),
            ("测试\n文本", "测试 文本"),
            ("测试  多余  空格", "测试 多余 空格"),
        ]
        
        for input_value, expected in test_cases:
            result = crawler._clean_text(input_value)
            assert result == expected, f"清洗 {input_value} 失败"
    
    def test_extract_multiple_winners(self):
        """测试多中标人提取"""
        crawler = CrawlerService()
        
        # 测试多中标人文本
        text = """
        第一中标候选人：深圳市某某建筑公司
        第二中标候选人：广州市某某工程公司
        第三中标候选人：东莞市某某建设公司
        """
        
        winners = crawler.extract_multiple_winners(text)
        
        assert len(winners) > 0, "应该提取到中标人"
        assert len(winners) <= 3, "中标人数量不应超过3个"
    
    @pytest.mark.asyncio
    async def test_crawl_with_retry(self):
        """测试重试机制"""
        crawler = CrawlerService()
        
        # 模拟失败后成功的场景
        with patch.object(crawler, 'navigate_to_detail') as mock_navigate:
            with patch.object(crawler, 'extract_all_fields') as mock_extract:
                # 第一次失败，第二次成功
                mock_navigate.side_effect = [False, True]
                mock_extract.return_value = {'project_name': '测试项目'}
                
                # 初始化浏览器（模拟）
                crawler.browser = Mock()
                crawler.context = Mock()
                crawler.page = Mock()
                
                result = await crawler.crawl_procurement_data('TEST001')
                
                # 应该重试并成功
                assert result is not None
                assert 'project_name' in result


@pytest.mark.asyncio
async def test_crawl_procurement_function():
    """测试便捷函数"""
    from weekly_report.services.crawler_service import crawl_procurement
    
    with patch('weekly_report.services.crawler_service.CrawlerService') as MockCrawler:
        mock_instance = AsyncMock()
        mock_instance.crawl_procurement_data = AsyncMock(return_value={'test': 'data'})
        MockCrawler.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        MockCrawler.return_value.__aexit__ = AsyncMock()
        
        result = await crawl_procurement('TEST001')
        
        assert result is not None
        assert 'test' in result