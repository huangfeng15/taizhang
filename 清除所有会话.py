"""
清除所有会话 - 强制所有用户重新登录
适用场景：
1. 启用HTTPS后，清除所有HTTP时期的会话
2. 安全升级后，要求所有用户重新登录
3. 发现安全问题，需要立即让所有会话失效
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.sessions.models import Session

def clear_all_sessions():
    """清除所有会话"""
    try:
        # 获取当前会话数量
        session_count = Session.objects.count()
        
        print(f"当前活跃会话数: {session_count}")
        
        if session_count == 0:
            print("没有需要清除的会话")
            return
        
        # 确认操作
        print("\n⚠️  警告：此操作将清除所有会话，所有用户需要重新登录！")
        confirm = input("是否继续？(输入 yes 确认): ")
        
        if confirm.lower() != 'yes':
            print("操作已取消")
            return
        
        # 删除所有会话
        Session.objects.all().delete()
        
        print(f"\n✅ 成功清除 {session_count} 个会话")
        print("✅ 所有用户需要重新登录")
        print("\n下一步：")
        print("1. 重启Django服务器")
        print("2. 通知所有用户刷新页面并重新登录")
        
    except Exception as e:
        print(f"❌ 清除失败: {e}")

if __name__ == '__main__':
    print("="*50)
    print("清除所有会话 - 强制重新登录")
    print("="*50)
    print()
    clear_all_sessions()