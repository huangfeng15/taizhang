"""测试分页功能是否正确跳转"""
from playwright.sync_api import sync_playwright
import time
import sys

def test_pagination():
    print("开始测试分页功能...", flush=True)
    with sync_playwright() as p:
        print("启动浏览器...", flush=True)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 测试采购管理分页
        print("测试采购管理分页...")
        page.goto('http://127.0.0.1:8000/procurements/')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 记录当前URL
        current_url = page.url
        print(f"当前URL: {current_url}")
        
        # 检查是否有分页按钮
        if page.locator('.pagination-btn:has-text("下一页")').count() > 0:
            # 点击下一页
            page.locator('.pagination-btn:has-text("下一页")').click()
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            new_url = page.url
            print(f"点击下一页后URL: {new_url}")
            
            # 验证URL是否仍在采购页面
            if '/procurements/' in new_url:
                print("✓ 采购管理分页正常 - URL保持在采购页面")
            else:
                print("✗ 采购管理分页错误 - URL跳转到了其他页面")
        else:
            print("- 采购管理暂无分页（数据量不足）")
        
        # 测试合同管理分页
        print("\n测试合同管理分页...")
        page.goto('http://127.0.0.1:8000/contracts/')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        current_url = page.url
        print(f"当前URL: {current_url}")
        
        if page.locator('.pagination-btn:has-text("下一页")').count() > 0:
            page.locator('.pagination-btn:has-text("下一页")').click()
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            new_url = page.url
            print(f"点击下一页后URL: {new_url}")
            
            if '/contracts/' in new_url:
                print("✓ 合同管理分页正常 - URL保持在合同页面")
            else:
                print("✗ 合同管理分页错误 - URL跳转到了其他页面")
        else:
            print("- 合同管理暂无分页（数据量不足）")
        
        # 测试付款管理分页
        print("\n测试付款管理分页...")
        page.goto('http://127.0.0.1:8000/payments/')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        current_url = page.url
        print(f"当前URL: {current_url}")
        
        if page.locator('.pagination-btn:has-text("下一页")').count() > 0:
            page.locator('.pagination-btn:has-text("下一页")').click()
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            new_url = page.url
            print(f"点击下一页后URL: {new_url}")
            
            if '/payments/' in new_url:
                print("✓ 付款管理分页正常 - URL保持在付款页面")
            else:
                print("✗ 付款管理分页错误 - URL跳转到了其他页面")
        else:
            print("- 付款管理暂无分页（数据量不足）")
        
        print("\n测试完成，浏览器将在5秒后关闭...")
        time.sleep(5)
        browser.close()

if __name__ == '__main__':
    test_pagination()