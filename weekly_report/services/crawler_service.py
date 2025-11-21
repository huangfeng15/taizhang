"""
爬虫服务 - 基于Playwright for Python实现
从阳光采购平台自动提取招投标信息
"""
import asyncio
import logging
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import yaml


logger = logging.getLogger(__name__)


class CrawlerService:
    """爬虫服务类 - 负责从采购平台提取数据"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化爬虫服务
        
        Args:
            config_path: 配置文件路径，默认使用weekly_report/config/crawler_config.yml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'crawler_config.yml'
        
        self.config = self._load_config(config_path)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._intercepted_data: Dict[str, Any] = {}
        
    def _load_config(self, config_path: Path) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    async def initialize(self):
        """初始化浏览器和上下文"""
        try:
            playwright = await async_playwright().start()
            browser_config = self.config.get('browser', {})
            
            # 启动浏览器
            self.browser = await playwright.chromium.launch(
                headless=browser_config.get('headless', False),
                slow_mo=browser_config.get('slow_mo', 100)
            )
            
            # 创建浏览器上下文
            viewport = browser_config.get('viewport', {})
            self.context = await self.browser.new_context(
                viewport={
                    'width': viewport.get('width', 1920),
                    'height': viewport.get('height', 1080)
                }
            )
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 设置默认超时
            timeout = browser_config.get('timeout', 30000)
            self.page.set_default_timeout(timeout)
            
            # 启用API拦截
            if self.config.get('api_intercept', {}).get('enabled', True):
                await self._setup_api_intercept()
            
            logger.info("浏览器初始化成功")
            
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            raise
    
    async def _setup_api_intercept(self):
        """设置API请求拦截"""
        patterns = self.config.get('api_intercept', {}).get('patterns', [])
        
        async def handle_route(route, request):
            """处理拦截的请求"""
            try:
                # 继续请求并获取响应
                response = await route.fetch()
                body = await response.body()
                
                # 存储拦截到的数据
                url = request.url
                self._intercepted_data[url] = {
                    'url': url,
                    'method': request.method,
                    'status': response.status,
                    'body': body.decode('utf-8') if body else None,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.debug(f"拦截到API请求: {url}")
                
                # 继续响应
                await route.fulfill(response=response)
                
            except Exception as e:
                logger.error(f"API拦截处理失败: {e}")
                await route.continue_()
        
        # 注册路由拦截
        for pattern in patterns:
            await self.page.route(pattern, handle_route)
    
    async def navigate_to_detail(self, procurement_code: str) -> bool:
        """
        导航到采购详情页
        
        Args:
            procurement_code: 采购编号
            
        Returns:
            是否成功导航
        """
        try:
            if not self.page:
                raise RuntimeError("浏览器未初始化")
            
            # 构建详情页URL
            primary_site = self.config.get('target_sites', {}).get('primary', {})
            detail_url = primary_site.get('detail_url_pattern', '').format(id=procurement_code)
            
            if not detail_url:
                logger.error("详情页URL配置缺失")
                return False
            
            # 导航到详情页
            logger.info(f"导航到详情页: {detail_url}")
            await self.page.goto(detail_url, wait_until='networkidle')
            
            # 等待页面加载完成
            await self.page.wait_for_load_state('domcontentloaded')
            
            return True
            
        except Exception as e:
            logger.error(f"导航到详情页失败: {e}")
            return False
    
    async def extract_field(self, field_name: str, field_config: Dict) -> Optional[Any]:
        """
        提取单个字段的值
        
        Args:
            field_name: 字段名称
            field_config: 字段配置
            
        Returns:
            提取的字段值
        """
        try:
            if not self.page:
                return None
            
            selector = field_config.get('selector')
            if not selector:
                return None
            
            # 检查是否支持多值
            is_multiple = field_config.get('multiple', False)
            
            if is_multiple:
                # 提取多个值
                elements = await self.page.query_selector_all(selector)
                values = []
                for element in elements:
                    text = await element.text_content()
                    if text:
                        values.append(text.strip())
                return values if values else None
            else:
                # 提取单个值
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    return text.strip() if text else None
                return None
                
        except Exception as e:
            logger.error(f"提取字段 {field_name} 失败: {e}")
            return None
    
    async def extract_all_fields(self) -> Dict[str, Any]:
        """
        提取所有配置的字段
        
        Returns:
            包含所有字段的字典
        """
        extracted_data = {}
        field_configs = self.config.get('field_extraction', {})
        
        for field_name, field_config in field_configs.items():
            value = await self.extract_field(field_name, field_config)
            
            # 应用数据清洗
            parser = field_config.get('parser')
            if value and parser:
                value = self._clean_data(value, parser)
            
            extracted_data[field_name] = value
        
        return extracted_data
    
    def _clean_data(self, value: Any, parser_type: str) -> Any:
        """
        清洗数据
        
        Args:
            value: 原始值
            parser_type: 解析器类型 (amount/date/text)
            
        Returns:
            清洗后的值
        """
        try:
            if parser_type == 'amount':
                return self._parse_amount(value)
            elif parser_type == 'date':
                return self._parse_date(value)
            elif parser_type == 'text':
                return self._clean_text(value)
            else:
                return value
        except Exception as e:
            logger.error(f"数据清洗失败 ({parser_type}): {e}")
            return value
    
    def _parse_amount(self, value: str) -> Optional[Decimal]:
        """
        解析金额
        
        Args:
            value: 金额字符串
            
        Returns:
            Decimal类型的金额
        """
        if not value:
            return None
        
        try:
            # 获取清洗规则
            amount_config = self.config.get('data_cleaning', {}).get('amount', {})
            remove_chars = amount_config.get('remove_chars', [])
            unit_conversion = amount_config.get('unit_conversion', {})
            
            # 移除特殊字符
            cleaned = value
            for char in remove_chars:
                cleaned = cleaned.replace(char, '')
            
            # 检查单位并转换
            multiplier = 1
            for unit, factor in unit_conversion.items():
                if unit in value:
                    multiplier = factor
                    break
            
            # 提取数字
            match = re.search(r'[\d.]+', cleaned)
            if match:
                amount = Decimal(match.group()) * multiplier
                return amount
            
            return None
            
        except Exception as e:
            logger.error(f"金额解析失败: {value}, 错误: {e}")
            return None
    
    def _parse_date(self, value: str) -> Optional[str]:
        """
        解析日期
        
        Args:
            value: 日期字符串
            
        Returns:
            标准格式的日期字符串 (YYYY-MM-DD)
        """
        if not value:
            return None
        
        try:
            date_config = self.config.get('data_cleaning', {}).get('date', {})
            formats = date_config.get('formats', ['%Y-%m-%d'])
            
            # 尝试各种日期格式
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            logger.warning(f"无法解析日期: {value}")
            return None
            
        except Exception as e:
            logger.error(f"日期解析失败: {value}, 错误: {e}")
            return None
    
    def _clean_text(self, value: str) -> str:
        """
        清洗文本
        
        Args:
            value: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not value:
            return value
        
        try:
            text_config = self.config.get('data_cleaning', {}).get('text', {})
            
            cleaned = value
            
            # 去除前后空白
            if text_config.get('strip', True):
                cleaned = cleaned.strip()
            
            # 移除换行符
            if text_config.get('remove_newlines', True):
                cleaned = cleaned.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
            
            # 合并多余空格
            if text_config.get('remove_extra_spaces', True):
                cleaned = re.sub(r'\s+', ' ', cleaned)
            
            return cleaned.strip()
            
        except Exception as e:
            logger.error(f"文本清洗失败: {e}")
            return value
    
    def extract_multiple_winners(self, text: str) -> List[str]:
        """
        从文本中提取多个中标人
        
        Args:
            text: 包含中标人信息的文本
            
        Returns:
            中标人列表
        """
        winners = []
        
        try:
            multiple_config = self.config.get('multiple_winners', {})
            if not multiple_config.get('enabled', True):
                return [text] if text else []
            
            patterns = multiple_config.get('patterns', [])
            max_winners = multiple_config.get('max_winners', 3)
            
            # 尝试匹配多中标人模式
            for pattern in patterns:
                if pattern in text:
                    # 按模式分割文本
                    parts = re.split(f'({pattern})', text)
                    for i, part in enumerate(parts):
                        if pattern in part and i + 1 < len(parts):
                            winner = parts[i + 1].strip()
                            # 提取公司名称（通常在冒号或空格后）
                            match = re.search(r'[:：\s]+([^，,；;。.]+)', winner)
                            if match:
                                winners.append(match.group(1).strip())
                    
                    if winners:
                        break
            
            # 如果没有匹配到模式，返回原文本
            if not winners and text:
                winners = [text]
            
            # 限制数量
            return winners[:max_winners]
            
        except Exception as e:
            logger.error(f"提取多中标人失败: {e}")
            return [text] if text else []
    
    async def crawl_procurement_data(self, procurement_code: str) -> Optional[Dict[str, Any]]:
        """
        爬取采购数据的主方法
        
        Args:
            procurement_code: 采购编号
            
        Returns:
            提取的采购数据字典
        """
        retry_config = self.config.get('retry', {})
        max_attempts = retry_config.get('max_attempts', 3)
        delay = retry_config.get('delay', 2000) / 1000  # 转换为秒
        backoff_factor = retry_config.get('backoff_factor', 2)
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"开始爬取采购数据 (尝试 {attempt + 1}/{max_attempts}): {procurement_code}")
                
                # 导航到详情页
                if not await self.navigate_to_detail(procurement_code):
                    raise Exception("导航到详情页失败")
                
                # 提取所有字段
                data = await self.extract_all_fields()
                
                # 处理多中标人
                if 'winning_bidder' in data and data['winning_bidder']:
                    if isinstance(data['winning_bidder'], list):
                        # 已经是列表，直接使用
                        pass
                    else:
                        # 尝试提取多中标人
                        data['winning_bidder'] = self.extract_multiple_winners(data['winning_bidder'])
                
                # 添加元数据
                data['_metadata'] = {
                    'crawled_at': datetime.now().isoformat(),
                    'procurement_code': procurement_code,
                    'source': 'crawler',
                    'attempt': attempt + 1
                }
                
                logger.info(f"成功爬取采购数据: {procurement_code}")
                return data
                
            except Exception as e:
                logger.error(f"爬取失败 (尝试 {attempt + 1}/{max_attempts}): {e}")
                
                if attempt < max_attempts - 1:
                    # 计算退避延迟
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"达到最大重试次数，爬取失败: {procurement_code}")
                    return None
        
        return None
    
    async def close(self):
        """关闭浏览器和清理资源"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            
            logger.info("浏览器已关闭")
            
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 便捷函数
async def crawl_procurement(procurement_code: str, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    便捷函数：爬取单个采购项目的数据
    
    Args:
        procurement_code: 采购编号
        config_path: 配置文件路径
        
    Returns:
        采购数据字典
    """
    async with CrawlerService(config_path) as crawler:
        return await crawler.crawl_procurement_data(procurement_code)