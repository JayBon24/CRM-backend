"""
获取可用的XpertAI专家列表
用于查找正确的专家ID
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from case_management.xpert_integration import XpertAIClient


async def get_experts():
    """获取并显示所有可用的专家"""
    try:
        # 使用你的API密钥
        client = XpertAIClient(
            api_url=os.getenv("XPERTAI_API_URL", "https://api.mtda.cloud/api/ai/"),
            api_key=os.getenv("XPERTAI_API_KEY", "")
        )
        
        print("=" * 80)
        print("正在获取可用的XpertAI专家列表...")
        print("=" * 80)
        print()
        
        # 获取专家列表
        experts = await client.get_experts(limit=50)
        
        if not experts:
            print("❌ 未找到任何可用的专家")
            return
        
        print(f"✅ 找到 {len(experts)} 个可用的专家:")
        print()
        
        # 打印专家信息
        for i, expert in enumerate(experts, 1):
            print(f"{i}. 专家信息:")
            print(f"   ├─ ID: {expert.get('assistant_id', 'N/A')}")
            print(f"   ├─ 名称: {expert.get('name', 'N/A')}")
            print(f"   ├─ 描述: {expert.get('description', 'N/A')}")
            print(f"   ├─ 模型: {expert.get('model', 'N/A')}")
            print(f"   ├─ Graph ID: {expert.get('graph_id', 'N/A')}")
            print(f"   └─ 创建时间: {expert.get('created_at', 'N/A')}")
            print()
        
        print("=" * 80)
        print("💡 提示: 复制上面的专家ID，更新到 xpert_integration.py 的 search_regulations 方法中")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(get_experts())
